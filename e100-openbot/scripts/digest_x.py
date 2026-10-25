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
    "dev_tools": [r"\bdev tools?\b", r"\bdevelopers?\b", r"\bsdks?\b", r"\binfrastructure\b", r"\bopen source\b", r"\bframeworks?\b", r"\bclis?\b", r"\breverse engineering\b"],
}
PUMP_RX = re.compile(r"\bpump\.fun\b|\bpumpfun\b|\b\$?pump\b", re.I)


def jload(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


def score(item):
    """(score, matched topics). Regex word-boundary hits only; else 0."""
    text = (item.get("text") or "").lower()
    topics = [t for t, kws in TOPICS.items() if any(re.search(k, text) for k in kws)]
    return len(topics), topics


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
        s, topics = score(it)
        if s <= 0:
            continue
        seen.add(url)
        scored.append((s, topics, it))
    # Tie-break newest first, then a stable sort by score (both passes matter).
    scored.sort(key=lambda x: x[2].get("visto") or "", reverse=True)
    scored.sort(key=lambda x: -x[0])
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
        for n, (s, topics, it) in enumerate(top5, 1):
            text = " ".join((it.get("text") or "").split())
            lines.append(f"### {n}. {it.get('handle') or 'unknown'} — topics: {', '.join(topics)}")
            lines.append(f"{it['url']}")
            lines.append("")
            lines.append(f"Full text: {text}")
            if PUMP_RX.search(text):
                lines.append("PUMP holder note: directly about Pump.fun / $PUMP.")
            lines.append("")

    lines += ["## Reply drafts (Mango Z)", "",
              "(To be written by hand against the candidates above — one per post,",
              "under 240 chars, about the post's actual point. No EchoLike pitch",
              "unless it fits naturally.)", ""]
    out = os.path.join(COCO, f"digest_x_{now.strftime('%Y-%m-%d')}.md")
    open(out, "w").write("\n".join(lines) + "\n")
    print(f"wrote {out} | scanned {len(items)} | on-topic {len(scored)} | top {len(top5)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
