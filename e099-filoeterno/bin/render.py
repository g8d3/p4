"""FiloEterno glass wall: builder edition. Stdlib only."""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEEDS = json.load(open(os.path.join(ROOT, "needs.json")))
DATA = os.path.join(ROOT, "data")
TASKS = os.path.join(ROOT, "tasks")


def read(p):
    try:
        return open(p).read().strip()
    except OSError:
        return ""


def task_cards():
    cards = []
    if not os.path.isdir(TASKS):
        return "<p>no tasks yet</p>"
    for t in sorted(os.listdir(TASKS)):
        td = os.path.join(TASKS, t)
        if not os.path.isdir(td):
            continue
        tests = audit = receipt = "—"
        ap = os.path.join(td, "AUDIT.md")
        if os.path.exists(ap):
            import re as _re
            lines = [l for l in open(ap).read().splitlines() if l.startswith("- [")]
            sev = {}
            for l in lines:
                m = _re.match(r"^- \[(\w+)\]", l)
                if m:
                    sev[m.group(1)] = sev.get(m.group(1), 0) + 1
            audit = f"{len(lines)} findings " + ", ".join(f"{k}:{v}" for k, v in sev.items())
        rp = os.path.join(td, "RECEIPT.md")
        if os.path.exists(rp):
            receipt = "deployed locally"
            for l in open(rp).read().splitlines():
                if "tests:" in l:
                    tests = l.split("tests:")[-1].strip()
        cards.append(f"<h3>{t}</h3><ul><li>tests: <b>{tests}</b></li>"
                     f"<li>audit: {audit}</li><li>deploy: {receipt}</li></ul>")
    return "".join(cards) or "<p>no tasks yet</p>"


def roadmap_html():
    rows = []
    for l in read(os.path.join(ROOT, "ROADMAP.md")).splitlines():
        s = l.strip()
        if not s.startswith("- ["):
            continue
        status = s[3:].split("]")[0]
        text = s.split("]", 1)[1].strip()
        pill = ("background:#e8f5e9" if status in ("done",) else
                "background:#fff8e1" if status == "next" else "background:#f4f4f4")
        rows.append(f"<li><span style='{pill};padding:.1rem .5rem;border-radius:1rem'>{status}</span> {text}</li>")
    return f"<ul>{''.join(rows)}</ul>" if rows else "<p>no roadmap</p>"


def toolchain_html():
    import subprocess as _sp
    info = {}
    env = dict(os.environ, PATH=os.path.expanduser("~/.foundry/bin") + ":" +
               os.environ.get("PATH", ""))
    for t in ("forge", "cast", "anvil"):
        try:
            p = _sp.run([t, "--version"], capture_output=True, text=True,
                        timeout=15, env=env)
            info[t] = p.stdout.strip().splitlines()[0] if p.returncode == 0 else "missing"
        except (OSError, subprocess.TimeoutExpired):
            info[t] = "missing"
    row = " · ".join(f"<b>{k}</b> {v}" for k, v in info.items())
    return f"<p>Toolchain (what built and deployed everything above): {row} · solc 0.8.26 (pinned in foundry.toml)</p>"


def status_panel():
    """When things run + which flags are still open."""
    import re as _re
    lessons = read(NEEDS["lessons_file"]).splitlines()
    flags, resolved_blob, resolves = [], [], set()
    cur = None
    for l in lessons:
        if l.startswith("## "):
            cur = l
            if "HUMAN FLAG" in l:
                flags.append([l, ""])
        elif cur and flags and cur == flags[-1][0] and l.startswith("- confusing:"):
            flags[-1][1] = l[len("- confusing:"):].strip()
        if l.startswith('- resolves:'):
            resolves.add(l[len('- resolves:'):].strip().strip('"'))
        if cur and "RESOLVED" in cur:
            resolved_blob.append(l)
    blob = "\n".join(resolved_blob)
    open_flags, done_flags = [], []
    for stamp, text in flags:
        hit = (text in resolves or (text[:25] in blob if text else False))
        (done_flags if hit else open_flags).append((stamp, text))
    last_start = last_result = None
    clog = read(os.path.join(DATA, "cycle.log")).splitlines()
    for l in clog:
        if "cycle start" in l:
            last_start = l.split("cycle start")[0].strip("= ")
        if "PROBE-OK" in l or "GATE-BROKEN" in l or "ADOPTED" in l or "REJECTED" in l:
            last_result = l.strip()
    nxt = ""
    hb = {}
    try:
        hb = json.load(open(os.path.join(DATA, "heartbeat.json")))
    except (OSError, ValueError):
        pass
    if hb:
        try:
            import datetime as _dt
            t = _dt.datetime.strptime(hb["ts"], "%Y-%m-%d %H:%M %z")
            age = int((_dt.datetime.now(_dt.timezone.utc) - t).total_seconds() // 60)
            nxt = (f"Loop is <b>continuous</b> — heartbeat {hb['ts']} "
                   f"({age} min ago), doing: {hb.get('doing', '?')}. "
                   f"Last guarded run {last_start or '?'} — {last_result or 'done'}.")
        except (ValueError, TypeError):
            nxt = f"Last run {last_start}."
    else:
        nxt = "Daemon heartbeat missing — check service."
    olist = "".join(f"<li>{t} <small>({s})</small></li>" for s, t in open_flags)
    return (f"<div class=\"cage\"><b>Loop status.</b> {nxt or 'No runs yet.'}<br>"
            f"Your flags: {len(done_flags)} answered, {len(open_flags)} waiting." +
            (f"<br>Waiting now:<ul>{olist}</ul>" if olist else "<br>Nothing waiting.") +
            "</div>")


def main():
    try:
        sys.path.insert(0, os.path.join(ROOT, "bin"))
        import op as _op
        _op.snapshot()  # fresh credits + empirical table; silent if offline
    except Exception:
        pass
    st = json.load(open(NEEDS["state_file"])) if os.path.exists(NEEDS["state_file"]) else {}
    lessons = read(NEEDS["lessons_file"])
    op = {}
    try:
        op = json.load(open(os.path.join(DATA, "operator.json")))
    except OSError:
        pass
    c = op.get("credits_pct", {})
    emp = "".join(
        f"<tr><td>{m}</td><td>{e['calls']}</td><td>{e['avg_tps']}</td>"
        f"<td>${e['avg_usd_call']}</td><td>{e['avg_score']}</td></tr>"
        for m, e in sorted(op.get("empirical", {}).items()))
    opbox = (f"<p>Credits used: rolling {c.get('rolling')}% / weekly {c.get('weekly')}% / "
             f"monthly {c.get('monthly')}% (cap {NEEDS.get('weekly_cap_pct')}% weekly). "
             f"Brain: <b>{op.get('configured_model', '?')}</b> · "
             f"live models on provider: {len(op.get('live_models', []))}.</p>"
             f"<table><tr><th>model</th><th>calls</th><th>tok/s (avg over all its calls)</th>"
             f"<th>$/call</th><th>avg score</th></tr>{emp or '<tr><td colspan=5>no calls yet</td></tr>'}</table>"
             f"<p><small>tok/s = all tokens that model ever produced ÷ all seconds it ever took.</small></p>"
             if op else "<p>operator data missing — run bin/op.py</p>")
    bench_html = ""
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FiloEterno — builder glass wall</title>
<style>body{{font-family:system-ui,sans-serif;max-width:62rem;margin:2rem auto;padding:0 1rem;line-height:1.6}}
pre{{background:#f4f4f4;padding:1rem;overflow:auto;white-space:pre-wrap;max-width:100%}}
table{{display:block;max-width:100%;overflow-x:auto;border-collapse:collapse}}
td,th{{border:1px solid #ccc;padding:.4rem .8rem;white-space:nowrap}}
.cage{{background:#fff8e1;border:1px solid #e0c36a;padding:1rem;border-radius:.5rem}}</style>
</head><body>
<h1>FiloEterno — apps that build themselves</h1>
{status_panel()}
<h2>What gets built next, and when it runs</h2>
<p>Only the guard runs on a clock. New builds start when you approve them —
flagging, chatting, or the button below when it lands.</p>
{roadmap_html()}
<p>Direction: <b>utility-meme dapps</b> — meme brings eyes, a glued-on micro-service
brings revenue beyond hype. The loop writes contracts, tests them, audits itself,
deploys locally. Paper and local-only until a human approves anything real.</p>
<div class="cage"><b>The cage (locked in code, the loop cannot touch):</b>
local deploys only · no mainnet without human approval · every test file must fail
on purpose once before it counts as a gate (red-first rule) · new brains must beat
the old one on past data · every change needs a 140-char plain-words note.</div>
<h2>Build tasks</h2>
{toolchain_html()}
{task_cards()}
<h2>Retired: trading-signal bench</h2>
<p>Early experiment (paper BTC signals, brains v1–v6, best 0.25). Retired when the
direction became building. Code and data kept in the repo for reference;
nothing here spends or trades. The lesson it taught — flat markets beat
always-flat brains — is baked into how strictly new work is scored.</p>
<h2>Operator view (what the loop sees about itself)</h2>
{opbox}
<h2>Lesson book (plain words — the asset)</h2>
<pre>{lessons or 'empty'}</pre>
<h2>Do you understand this page?</h2>
<p>Paste any confusing line — it becomes a penalty the loop must beat AND explain better.</p>
<form onsubmit="return flag(event)">
<input id="flagtext" size="60" placeholder="paste the confusing line">
<button>Flag as confusing</button> <span id="flagstatus"></span></form>
<h2>Run from here (served page only)</h2>
<p><b>The probe, in plain words:</b> we make a throwaway copy of the contract,
deliberately break the money math (turn the 1% fee into 2%), and run the tests.
If the tests go red, the gate works — they actually watch the money. If they stay
green, the gate is blind and everything stops until a human fixes it.
Free because no AI is involved: it is just running tests, like a fire drill.</p>
<p>Full build rounds (new contracts, audits) run in chat with a human present.</p>
<button onclick="return run('probe')">Run red-first probe</button>
<span id="status"></span>
"""
    script = ("<script>"
        "async function run(cmd){const s=document.getElementById('status');"
        "s.textContent='working on '+cmd+'…';"
        "const r=await fetch('/api/'+cmd,{method:'POST'});const j=await r.json();"
        "s.textContent=r.ok?('done: '+j.tail.slice(-200)+' — reloading…'):'FAILED: '+(j.tail||'').slice(-200);"
        "if(r.ok)setTimeout(()=>location.reload(),2500);return false}"
        "async function flag(e){e.preventDefault();"
        "const t=document.getElementById('flagtext').value;"
        "const s=document.getElementById('flagstatus');s.textContent='sending…';"
        "const r=await fetch('/api/confused',{method:'POST',"
        "headers:{'Content-Type':'application/json'},"
        "body:JSON.stringify({text:t})});"
        "s.textContent=r.ok?'recorded — the loop must now beat that lesson AND explain it better':'failed';"
        "if(r.ok)setTimeout(()=>location.reload(),800);return false}</script>"
        "</body></html>")
    page = html + script
    for tag in ("div", "table", "ul", "form", "button"):
        assert page.count(f"<{tag}") == page.count(f"</{tag}>"), f"unbalanced <{tag}>"
    os.makedirs(NEEDS["site_dir"], exist_ok=True)
    open(os.path.join(NEEDS["site_dir"], "index.html"), "w").write(page)
    print("wrote glass wall")
