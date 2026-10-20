#!/usr/bin/env python3
"""FiloEterno v0: self-improving BTC paper-signal loop. Stdlib only.

The machine plays; humans hold the cage. Cage (locked in this file, the loop
can NEVER edit it): paper only, position size 0, daily call cap, new rules
must beat the current rule on past data before adoption, every change needs a
<=140-char plain-words note or it is rejected.

Model access: OPENCODE_GO_* env (Responses API, session header). Key comes
from env only, never from files.

Commands:
  loop.py fetch              check market data connection (no model call)
  loop.py score              score current prompt on last N completed days
  loop.py propose            ask model for a better prompt, test, adopt if wins
  loop.py today              record today's signal with current prompt
  loop.py render             rebuild static glass-wall page (no server)
"""
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time as _time
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import op as _op

_WEEKLY = None

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
NEEDS = json.load(open(os.path.join(ROOT, "needs.json")))
DATA = os.path.join(ROOT, "data")
os.makedirs(DATA, exist_ok=True)
os.makedirs(os.path.join(ROOT, "prompts"), exist_ok=True)

STATE_F = NEEDS["state_file"]
PROMPTS = os.path.join(ROOT, "prompts")
V1 = ("You are a careful Bitcoin analyst. Look at the last {N} daily closes below. "
      "Answer with JSON only: {\"bias\": \"long|short|flat\", \"confidence\": 0-1, "
      "\"note\": \"why, plain words\"}. "
      "Rule: if the last 5 closes rise 3+ times, bias long; if they fall 3+ times, "
      "bias short; else flat. Closes:\n{closes}")


def cfg():
    base = os.environ.get(NEEDS["base_url_env"], "").rstrip("/") + "/"
    key = ""
    for n in NEEDS["key_envs"]:
        if os.environ.get(n):
            key = os.environ[n]
            break
    model = NEEDS.get("model") or os.environ.get(NEEDS["model_env"], "")
    if not key or not model:
        sys.exit("missing model access: need key env + model env set")
    return base, key, model


def now():
    return dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %z")


def call_model(text, max_tokens=4096):
    """One gateway call. Counts caps, records tokens/$/tok/s."""
    global _WEEKLY
    if _WEEKLY is None:
        _WEEKLY = _op.weekly_pct()
    if _WEEKLY >= NEEDS.get("weekly_cap_pct", 80):
        sys.exit(f"weekly cap hit ({_WEEKLY}%); loop stops itself")
    st = load_state()
    today = dt.date.today().isoformat()
    used = st.get("calls", {}).get(today, 0)
    if used >= NEEDS["max_calls_per_day"]:
        sys.exit(f"daily call cap hit ({used}); loop stops itself")
    base, key, model = cfg()
    body = json.dumps({"model": model, "max_output_tokens": max_tokens,
                       "input": text}).encode()
    req = urllib.request.Request(
        base + "responses", data=body,
        headers={"Authorization": f"Bearer {key}",
                 NEEDS["session_header"]: NEEDS["session_id"],
                 "User-Agent": NEEDS["user_agent"],
                 "Content-Type": "application/json"})
    t0 = _time.time()
    with urllib.request.urlopen(req, timeout=120) as r:
        resp = json.load(r)
    secs = _time.time() - t0
    _op.record_call(model, resp.get("usage"), secs)
    skel = {'status': resp.get('status'), 'items': [
        (i.get('type'), i.get('status')) for i in resp.get('output', [])]}
    open(os.path.join(DATA, 'last_resp_skeleton.txt'), 'w').write(json.dumps(skel))
    st.setdefault("calls", {})[today] = used + 1
    save_state(st)
    return extract_text(resp)


def extract_text(resp):
    for item in resp.get("output", []):
        if item.get("type") == "message":
            parts = [c.get("text", "") for c in item.get("content", [])
                     if c.get("type") == "output_text"]
            if parts:
                return "\n".join(parts)
    return ""


def fill(template, window, asset="BTC", tf="day"):
    closes = ", ".join(f"{c:.0f}" for _, c in window)
    return (template.replace("{N}", str(NEEDS["window_days"]))
             .replace("{closes}", closes)
             .replace("{asset}", asset).replace("{tf}", tf))


def kraken_daily(pair="XBTUSD", interval=1440):
    url = (f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval={interval}")
    req = urllib.request.Request(url, headers={"User-Agent": NEEDS["user_agent"]})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    rows = next(iter(data["result"].values()))
    closes = [(dt.datetime.fromtimestamp(c[0], dt.timezone.utc).date().isoformat(),
               float(c[4])) for c in rows]
    return closes[:-1]  # drop today's incomplete candle


def parse_signal(text):
    m = re.search(r"\{[^{}]*\"bias\"[^{}]*\}", text, re.S)
    if not m:
        return {"bias": "flat", "confidence": 0.0, "note": "unparseable reply"}
    try:
        s = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {"bias": "flat", "confidence": 0.0, "note": "bad json"}
    b = str(s.get("bias", "flat")).lower()
    return {"bias": b if b in ("long", "short", "flat") else "flat",
            "confidence": float(s.get("confidence", 0) or 0),
            "note": str(s.get("note", ""))[:140]}


def score_day(bias, ret):
    if bias == "flat":
        return 0.5 if abs(ret) < 0.003 else 0.0
    return 1.0 if (ret > 0 and bias == "long") or (ret < 0 and bias == "short") else 0.0


def market():
    """[(asset, closes)] for every configured asset/interval."""
    out = []
    for pair in NEEDS.get("assets", ["XBTUSD"]):
        out.append((pair.replace("XBT", "BTC").replace("USD", ""),
                      kraken_daily(pair, NEEDS.get("interval", 1440))))
    return out


def tf_label():
    return {60: "hour", 1440: "day"}.get(NEEDS.get("interval", 1440),
             f"{NEEDS.get('interval')}min")


def score_version(prompt, mk, n):
    """Score prompt on last n completed periods across all assets.
    Each test: 30 prior closes in, next-period return out."""
    res = []
    for asset, closes in mk:
        if len(closes) < NEEDS["window_days"] + n + 1:
            sys.exit(f"not enough history for {asset}")
        start = len(closes) - n - 1
        for i in range(start, start + n):
            window = closes[i - NEEDS["window_days"]:i]
            ret = (closes[i + 1][1] - closes[i][1]) / closes[i][1]
            sig = parse_signal(call_model(fill(prompt, window, asset, tf_label())))
            s = score_day(sig["bias"], ret)
            res.append({"asset": asset, "day": closes[i][0], "bias": sig["bias"],
                        "ret_pct": round(ret * 100, 2), "score": s,
                        "note": sig["note"]})
    return sum(r["score"] for r in res) / len(res), res


def load_state():
    if os.path.exists(STATE_F):
        return json.load(open(STATE_F))
    return {"current": "v1", "versions": {}, "calls": {}}


def save_state(st):
    json.dump(st, open(STATE_F, "w"), indent=2)


def ensure_v1():
    p = os.path.join(PROMPTS, "v1.txt")
    if not os.path.exists(p):
        open(p, "w").write(V1)


def cmd_fetch():
    for asset, closes in market():
        print(f"market ok: {asset} {len(closes)} closes ({tf_label()}), last {closes[-1]}")


def cmd_score():
    ensure_v1()
    st = load_state()
    cur = st["current"]
    prompt = open(os.path.join(PROMPTS, f"{cur}.txt")).read()
    mean, det = score_version(prompt, market(), NEEDS["score_periods"])
    fresh = load_state()  # scoring calls already saved their counts; don't clobber
    fresh["versions"].setdefault(cur, {})["score"] = round(mean, 3)
    fresh["versions"][cur]["n"] = len(det)
    save_state(fresh)
    _op.record_call(cfg()[2], None, 0, score=round(mean, 3))
    print(f"{cur}: score {mean:.3f} over {len(det)} asset-periods")
    for d in det:
        print(f"  {d['asset']} {d['day']} bias={d['bias']} next={d['ret_pct']}% s={d['score']}")


def plain_ok(note):
    return isinstance(note, str) and 0 < len(note) <= 140


def extract_json(text):
    """First balanced {...} object in text (prompt text may hold {N})."""
    i = text.find("{")
    if i < 0:
        return None
    depth, instr, esc = 0, False, False
    for j in range(i, len(text)):
        c = text[j]
        if instr:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                instr = False
        elif c == '"':
            instr = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[i:j + 1])
                except json.JSONDecodeError:
                    return None
    return None


def cmd_propose():
    ensure_v1()
    st = load_state()
    cur = st["current"]
    hist = {v: {"score": i.get("score"), "n": i.get("n")}
            for v, i in st["versions"].items()}
    lessons = ""
    if os.path.exists(NEEDS["lessons_file"]):
        lessons = open(NEEDS["lessons_file"]).read()[-1500:]
    mission = (
        "You improve a Bitcoin daily-signal prompt. Current prompt:\n" + open(
            os.path.join(PROMPTS, f"{cur}.txt")).read() +
        f"\n\nPast version scores: {json.dumps(hist)}\nPast lessons:\n{lessons}\n\n"
        "Write a better prompt. Reply with JSON only: "
        "{\"prompt\": \"full new prompt, keep {N} and {closes} placeholders\", "
        "\"note\": \"what you changed and why\"}. "
        "RULES for note: max 140 characters, only common words, no jargon. "
        "Example good note: 'also look at 10-day average so choppy days give flat'.")
    raw = call_model(mission, max_tokens=8192)
    open(os.path.join(DATA, "last_propose_raw.txt"), "w").write(raw)
    prop = extract_json(raw)
    if not prop or "prompt" not in prop:
        sys.exit("proposer gave no usable JSON; nothing changed")
    new_prompt, note = prop["prompt"], prop.get("note", "")
    if "{N}" not in new_prompt or "{closes}" not in new_prompt:
        sys.exit("proposal dropped placeholders; rejected")
    if not plain_ok(note):
        sys.exit(f"note not plain (must be 1-140 chars); rejected: {note[:80]}")
    nv = f"v{len([f for f in os.listdir(PROMPTS) if f.endswith('.txt')]) + 1}"
    open(os.path.join(PROMPTS, f"{nv}.txt"), "w").write(new_prompt)
    mean, det = score_version(new_prompt, market(), NEEDS["score_periods"])
    old = st["versions"].get(cur, {}).get("score", 0)
    verdict = "ADOPTED" if mean > old + 0.05 else "REJECTED"
    st["versions"][nv] = {"score": round(mean, 3), "n": len(det),
                          "note": note, "parent": cur}
    if verdict == "ADOPTED":
        st["current"] = nv
    fresh = load_state()  # keep call counts saved during scoring
    fresh["versions"].update(st["versions"])
    fresh["current"] = st["current"]
    save_state(fresh)
    with open(NEEDS["lessons_file"], "a") as f:
        f.write(f"\n## {now()} {nv} {verdict} "
                f"(score {mean:.3f} vs {cur} {old})\n- change: {note}\n")
    print(f"{nv}: score {mean:.3f} vs {cur} {old} -> {verdict}")


def cmd_today():
    ensure_v1()
    st = load_state()
    cur = st["current"]
    prompt = open(os.path.join(PROMPTS, f"{cur}.txt")).read()
    for asset, closes in market():
        window = closes[-NEEDS["window_days"]:]
        sig_raw = call_model(fill(prompt, window, asset, tf_label()), max_tokens=8192)
        open(os.path.join(DATA, 'last_today_raw.txt'), 'w').write(sig_raw)
        sig = parse_signal(sig_raw)
        rec = {"date": closes[-1][0], "asset": asset, "tf": tf_label(),
               "version": cur, "signal": sig, "last_close": closes[-1][1],
               "paper_only": True, "position_pct": 0}
        with open(os.path.join(DATA, "signals.jsonl"), "a") as f:
            f.write(json.dumps(rec) + "\n")
        print(json.dumps(rec))


def cmd_probe():
    """Red-first mutation probe: break fee math in a COPY, tests must go red.
    No model calls. Verdict appended to LESSONS.md."""
    import shutil
    import tempfile
    td = os.path.join(ROOT, "tasks", "01-tipjar-coin")
    tmp = tempfile.mkdtemp(prefix="probe01-")
    try:
        for sub in ("src", "test", "foundry.toml"):
            s, d = os.path.join(td, sub), os.path.join(tmp, sub)
            if os.path.isdir(s):
                shutil.copytree(s, d)
            else:
                shutil.copy(s, d)
        sp = os.path.join(tmp, "src", "TipJarCoin.sol")
        src = open(sp).read()
        assert "amount / 100" in src, "fee pattern moved — probe needs update"
        open(sp, "w").write(src.replace("amount / 100", "amount / 50"))
        env = dict(os.environ, PATH=os.path.expanduser("~/.foundry/bin") + ":" +
                   os.environ.get("PATH", ""))
        p = subprocess.run(["forge", "test"], cwd=tmp, capture_output=True,
                           text=True, timeout=300, env=env)
        red = p.returncode != 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    verdict = "PROBE-OK (gate caught the mutation)" if red else \
        "GATE-BROKEN (tests stayed green on broken math)"
    with open(NEEDS["lessons_file"], "a") as f:
        f.write(f"\n## {now()} mutation probe: {verdict}\n")
    print(verdict)
    if not red:
        sys.exit("gate broken — no building until fixed")


CMDS = {"fetch": cmd_fetch, "score": cmd_score, "propose": cmd_propose,
        "today": cmd_today, "probe": cmd_probe}


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in CMDS and sys.argv[1] != "render":
        sys.exit("usage: loop.py fetch|score|propose|today|probe|render")
    if sys.argv[1] == "render":
        sys.path.insert(0, os.path.join(ROOT, "bin"))
        import render
        render.main()
    else:
        CMDS[sys.argv[1]]()
        if sys.argv[1] in ("score", "propose", "today", "probe"):
            sys.path.insert(0, os.path.join(ROOT, "bin"))
            import render
            render.main()
