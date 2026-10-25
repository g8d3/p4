# NEXT — EchoLike business priorities
Updated: Sun 2026-10-25 15:25 Bogotá (UTC-5)

## Top priority
Get the echolike.app sales page ready to sell on a phone. Six gaps:
1. No price (Nova decides).
2. No clear call to action.
3. Weak proof, full of jargon.
4. No reason to pick us.
5. No steps or FAQ.
6. Bottom nav pulls buyers away from the offer.
"Ready" = passes this checklist with phone screenshots, not just "it loads".

## In progress (assigned 3:25 PM, local only, no push)
- Mango: gaps 4 (why us) and 6 (bottom nav) in e092-echolike/sitio_unico.py.
- Mango Z: gap 5 (steps + FAQ) in the same file.
- Both report via bin/to_coco.sh when done.

## Done today
- echolike.app moved to GitHub Pages (g8d3/echolike-site) via Cloudflare DNS; email works.
- Firefox add-on install button is live.
- Mango Z daily 7 AM report is live.
- Agent trials: Mango 9.5/10, Mango Z 9.5/10.

## Blocked
- Outreach DMs to 7 people failed: X only allows chats from followers.
- Public announcement post needs Nova's OK on the text.
- /directory/ and /funding-rates/ are a frozen snapshot until a job publishes them to echolike-site.

## Paused
- Trading and Hummingbot (Nova unsure about trading), Churn paper test (undecided), liquidity page.

## Rules
- No sending, posting or pushing without Nova.
- Never invent times or approvals.

## How to reach Coco
You and Mango Z can message Coco on your own (no sending/posting outside):
`bin/to_coco.sh "<from>" "<message>"` queues one JSON line to `coco/inbox_to_coco.jsonl`.
Use it for questions, blockers, and finished results — one line per message, keep it short.
Coco reads with `bin/coco_unread.py` (`--peek` to preview without moving the marker).

## Suggested order
1. Sales page. 2. Add-on distribution. 3. Agents refresh directory + funding pages. 4. Trading stays paused.
