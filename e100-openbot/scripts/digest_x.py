#!/usr/bin/env python3
"""Daily X research digest for Nova (local, stdlib only; never posts).

Reads Nova's recent likes from e092-echolike/estado/x_items.json (last 48h by
the 'visto' field) and the topic-alert file estado/likes_alertas.json. Scores
items against Nova's standing topics (launchpads/fair launches, AI agents and
AI+crypto, memecoins, coins holding up in drawdowns, dev tools) and writes
coco/digest_x_YYYY-MM-DD.md with the top 5 verified items (real URLs exactly
as found in the source files - never constructed) plus 2-3 reply drafts for
@novaisabuilder chosen from the highest-scored items. Unverifiable entries are
dropped, not guessed. Never posts anything; output is a draft file only.
"""
import json, os, re, sys
from datetime import datetime, timedelta, timezone

E092 = os.path.expanduser("~/code/p4/e092-echolike")
COCO = os.path.expanduser("~/code/p4/e100-openbot/coco")
BOG = timezone(timedelta(hours=-5))
TOPICS = {
    "launchpads": ["launchpad", "fair launch", "fair-launch", "launch", "launchpads"],
    "ai_agents": ["ai agent", "ai agents", "agent", "ai + crypto", "ai x crypto", "ai crypto"],
    "memecoins": ["memecoin", "meme coin", "memecoin launch", "pump.fun", "pumpfun"],
    "drawdown_strength": ["holding", "holder", "drawdown", "resilien", "red day", "down market", "holding up"],
    "dev_tools": ["dev tool", "developer", "sdk", "infrastructure", "open source", "cli", "framework"],
}
REPLY_WORTHY = ("launchpad", "fair launch", "ai agent", "dev tool", "infrastructure")


def jload(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


def score(item):
    """(score, matched topics). Keyword hits only; anything unmatched scores 0."""
    text = (item.get("text") or "").lower()
    topics = [t for t, kws in TOPICS.items() if any(k in text for k in kws)]
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
    scored.sort(key=lambda x: (-x[0], x[2].get("visto") or ""), reverse=False)
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
        lines.append("## Top 5")
        lines.append("")
        for n, (s, topics, it) in enumerate(top5, 1):
            text = " ".join((it.get("text") or "").split())
            reason = f"matches Nova topics: {', '.join(topics)}"
            lines.append(f"{n}. {it.get('handle') or 'unknown'} — {text[:140]}"
                         f"{'…' if len(text) > 140 else ''}")
            lines.append(f"   {it['url']}")
            lines.append(f"   Why: {reason}.")
            lines.append("")
    replies = [x for x in scored if any(k in " ".join(x[1]) or
               any(k in (x[2].get('text') or '').lower() for k in REPLY_WORTHY) for k in REPLY_WORTHY)][:3]
    if replies:
        lines += ["## Suggested replies for @novaisabuilder (drafts — do not post)", ""]
        for s, topics, it in replies:
            pretty = " and ".join(t.replace("_", " ") for t in topics) or "this"
            lines.append(f"- To {it.get('handle')} ({it['url']}):")
            lines.append(f"  \"Saw your post on {pretty}. We run EchoLike, an AI-agent "
                         "workshop that turns X bookmarks into research and working tools — happy to trade notes.\"")
            lines.append("")
    out = os.path.join(COCO, f"digest_x_{now.strftime('%Y-%m-%d')}.md")
    open(out, "w").write("\n".join(lines) + "\n")
    print(f"wrote {out} | scanned {len(items)} | on-topic {len(scored)} | top {len(top5)} | replies {len(replies)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
