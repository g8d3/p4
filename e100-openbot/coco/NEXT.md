# NEXT — EchoLike business priorities
Updated: Sun 2026-10-25 15:45 Bogotá (UTC-5)

## Owners
- Mango: product + dev (extension, sales page, site).
- Mango Z: market, monetization, social (pricing research, competitors, post drafts; Nova approves every post).
- Coco: coordination; decisions for Nova come to Coco as max 3 numbered options + a recommendation.

## Top priority
Get the echolike.app sales page ready to sell on a phone. Six gaps:
1. [Owner: Mango Z → Nova] No price (Nova decides).
2. [Owner: Mango] No clear call to action.
3. [Owner: Mango] Weak proof, full of jargon.
4. [Owner: Mango] No reason to pick us.
5. [Owner: Mango Z, in progress] No steps or FAQ.
6. [Owner: Mango] Bottom nav pulls buyers away from the offer.
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
- [Owner: Mango Z] Outreach DMs to 7 people failed: X only allows chats from followers.
- [Owner: Mango Z] Public announcement post needs Nova's OK on the text.
- [Owner: Mango] /directory/ and /funding-rates/ are a frozen snapshot until a job publishes them to echolike-site.

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
1. Sales page (Mango). 2. Add-on distribution (Mango). 3. Refresh directory + funding pages (Mango); pricing research (Mango Z). 4. Trading stays paused.
