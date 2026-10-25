#!/usr/bin/env python3
"""Daily X research digest for Nova (local, stdlib only; never posts).

Reads Nova's recent likes from e092-echolike/estado/x_items.json (last 48h by
the 'visto' field) and the topic-alert file estado/likes_alertas.json. Scores
items against Nova's standing topics (launchpads/fair launches, AI agents and
AI+crypto, memecoins, coins holding up in drawdowns, dev tools) using
word-boundary regexes, and writes coco/digest_x_YYYY-MM-DD.md with:
  - Candidate posts: top 5, full text, real URLs exactly as found in the
    source files (never constructed), plus a PUMP holder note when relevant.
  - A placeholder reply section that Mango Z fills in by hand per candidate.
Unverifiable entries are dropped, not guessed. Never posts anything.
"""
import json, os, re, sys
from datetime import datetime, timedelta, timezone

E092 = os.path.expanduser("~/code/p4/e092-echolike")
COCO = os.path.expanduser("~/code/p4/e100-openbot/coco")
BOG = timezone(timedelta(hours=-5))
# Word-boundary regexes: bare "launch"/"cli"/"agent"/"holding" matched too much.
TOPICS = {
    "launchpads": [r"\blaunchpads?\b", r"\bfair[ -]launch", r"\btoken launch"],
    "ai_agents": [r"\bai agents?\b", r"\bai agent\b", r"\bagentic\b", r"\bai\s*\+\s*crypto\b", r"\bai ?x ?crypto\b", r"\bcrypto ?x ?ai\b"],
    "memecoins": [r"\bmemecoins?\b", r"\bmeme coins?\b", r"\bpump\.fun\b", r"\bpumpfun\b", r"\bmemecoin launch"],
    "drawdown_strength": [r"\bholding up\b", r"\bdrawdowns?\b", r"\bresilien\w*", r"\bred days?\b", r"\bdown market\b", r"\bwhile the market (falls|dumps|drops)\b"],
    "dev_tools": [r"\bdev tools?\b", r"\bsdks?\b", r"\binfrastructure\b", r"\bopen source\b", r"\bframeworks?\b", r"\breverse engineering\b"],
}
RX = {t: [re.compile(p, re.I) for p in pats] for t, pats in TOPICS.items()}
PUMP_RX = re.compile(r"\bpump\.fun\b|\bpumpfun\b|\b\$?pump\b", re.I)


def jload(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


def score(item):
    """(ntopics, nhits, matched topics). Regex word-boundary hits only; else 0."""
    text = (item.get("text") or "").lower()
    topics, hits = [], 0
    for t, rxs in RX.items():
        n = sum(len(r.findall(text)) for r in rxs)
        if n:
            topics.append(t)
            hits += n
    return len(topics), hits, topics


def main():
    now = datetime.now(BOG)
    cutoff = (now - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M")
    src = jload(os.path.join(E092, "estado", "x_items.json")) or {}
    items = [i for i in src.get("items", []) if (i.get("visto") or "") >= cutoff]
    alerts = (jload(os.path.join(E092, "estado", "likes_alertas.json")) or {}).get("alertas", [])
    for a in alerts:
        if (a.get("visto") or "") >= cutoff:
            items.append(a)

    seen, scored = set(), []
    for it in items:
        url = it.get("url") or ""
        if not url.startswith("https://x.com/") or url in seen:
            continue
        nt, nh, topics = score(it)
        if nt <= 0:
            continue
        seen.add(url)
        scored.append((nt, nh, topics, it))
    # One sort: most topics, then most keyword hits, then newest.
    scored.sort(key=lambda x: (x[0], x[1], x[3].get("visto") or ""), reverse=True)
    top5 = scored[:5]

    lines = [f"# X research digest — {now.strftime('%Y-%m-%d')} (Bogotá)",
             "",
             f"Sources: estado/x_items.json + estado/likes_alertas.json, last 48h "
             f"({len(items)} items scanned, {len(scored)} on-topic). Draft only — never posted.",
             ""]
    if not top5:
        lines += ["## No fresh on-topic data in the last 48h.", ""]
    else:
        lines.append("## Candidate posts")
        lines.append("")
        for n, (nt, nh, topics, it) in enumerate(top5, 1):
            text = " ".join((it.get("text") or "").split())
            lines.append(f"### {n}. {it.get('handle') or 'unknown'} — topics: {', '.join(topics)}")
            lines.append(f"{it['url']}")
            lines.append("")
            lines.append(f"Full text: {text}")
            if PUMP_RX.search(text):
                lines.append("PUMP holder note: directly about Pump.fun / $PUMP.")
            lines.append("")

    out = os.path.join(COCO, f"digest_x_{now.strftime('%Y-%m-%d')}.md")
    # Never clobber hand-written drafts: keep an existing drafts section that
    # already has "- To ..." entries, regenerate only the candidates above it.
    tail = None
    if os.path.exists(out):
        prev = open(out, encoding="utf-8").read()
        if "## Reply drafts" in prev:
            old_sec = prev.split("## Reply drafts", 1)[1]
            if re.search(r"^- To \S+ \(https://x\.com/\S+\)", old_sec, re.M):
                tail = "## Reply drafts" + old_sec.rstrip() + "\n"
    if tail is None:
        tail = ("## Reply drafts (hand-written — do not post)\n\n"
                "(Write drafts here by hand against the candidates above — one per post,\n"
                "under 200 chars, one specific observation or question from the post's\n"
                "actual content. No product pitch, no quoting URLs/arrows/lists, no cashtags,\n"
                "no repeated questions. Skip the post if nothing real to say.)\n")
    open(out, "w").write("\n".join(lines) + "\n" + tail)
    print(f"wrote {out} | scanned {len(items)} | on-topic {len(scored)} | top {len(top5)}")
    return check_drafts(out)


def parse_drafts(path):
    """[(handle, url, body)] from a digest file; body = indented lines."""
    sec = open(path, encoding="utf-8").read().split("## Reply drafts")
    if len(sec) < 2:
        return []
    out, cur = [], None
    for line in sec[1].splitlines():
        m = re.match(r"^- To (\S+) \((https://x\.com/\S+?)\)", line.strip())
        if m:
            cur = [m.group(1), m.group(2).rstrip(":"), []]
            out.append(cur)
        elif cur is not None and line.startswith("  ") and line.strip():
            cur[2].append(line.strip())
    return [(h, u, " ".join(b)) for h, u, b in out if b]


def fact_tokens(body):
    """Checkable claims in a draft: cashtags and numbers with units."""
    toks = set(re.findall(r"\$[A-Za-z]{2,}", body))
    toks.update(re.findall(r"\d[\d.,]*\s*(?:M|B|K|k|%)", body))
    return toks


def check_drafts(path):
    """Fail the run when a hand-written draft exceeds 200 chars, contains a
    link/arrow/cashtag, repeats a question, or cites a fact not present in
    its own cited post (checked against the post's text in this file)."""
    posts = {}
    cur_url, buf = None, []
    for line in open(path, encoding="utf-8"):
        if line.startswith("https://x.com/"):
            if cur_url and buf:
                posts[cur_url] = " ".join(buf)
            cur_url, buf = line.strip(), []
        elif line.startswith("Full text: ") and cur_url:
            buf.append(line[len("Full text: "):].strip())
    if cur_url and buf:
        posts[cur_url] = " ".join(buf)
    drafts = parse_drafts(path)
    questions = []
    for handle, url, d in drafts:
        if len(d) > 200:
            print(f"FAIL draft over 200 chars ({len(d)}): {d[:60]}…")
            return 1
        if re.search(r"http|→|\$[A-Z]{2,}", d):
            print(f"FAIL draft has link/arrow/cashtag: {d[:60]}…")
            return 1
        post = posts.get(url, "")
        for tok in fact_tokens(d):
            if tok.lower() not in post.lower():
                print(f"FAIL draft cites fact not in its post ({tok}): {d[:60]}…")
                return 1
        questions += re.findall(r"[^?]+\?", d)
    dup = {q for q in questions if questions.count(q) > 1}
    if dup:
        print(f"FAIL repeated question: {next(iter(dup))}")
        return 1
    print(f"drafts OK: {len(drafts)} checked, facts match cited posts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
