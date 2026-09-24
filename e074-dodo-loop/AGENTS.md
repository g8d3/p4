# e074 — Dodo Loop (observable builder, Dodo-ready site)

Goal: ship one live site that passes Dodo Payments Product Information
review. Human owns Persona + Bank. Agent owns everything else.

## Split (hard rule)

- Agent: site, legal pages, product packet, checks, desk. Never touches
  ID, selfie, bank credentials, Dodo dashboard submit.
- Human: pastes Product Form, completes Persona KYC, enters IBAN.
  One time, ~15 min, after agent says READY.

## Cycle

```
bin/loop.sh  ->  dodo_check.py  ->  data/ledger.jsonl  ->  render_desk.py -> desk.html
```

One iteration = one check + one ledger row + one desk render.
Idempotent. No cron yet — human runs `bash bin/loop.sh` to advance.
Loop is a PROGRAM, this chat is supervision only.

## Files

| File | Purpose |
|---|---|
| `site/` | Live-reviewable site (index, pricing, terms, privacy, refunds, contact) |
| `data/product-packet.json` | Exact strings to paste into Dodo Product Information Form |
| `bin/dodo_check.py` | Dodo readiness gate (footer links, pricing, match site vs packet) |
| `bin/render_desk.py` | Rebuilds `desk.html` from ledger + latest check |
| `bin/loop.sh` | One iteration driver |
| `data/ledger.jsonl` | Append-only truth (one row per iteration) |
| `desk.html` | Observer desk — watch this, never the chat log |
| `log/loop.log` | Raw run log |

## Observer contract

The asker watches `desk.html` only. Every reviewable fact lives there:
pulse, spend proxy, actions, artifacts, Dodo checklist, human gates,
decisions. If it is not on the desk, it did not happen.

## Product (v0)

SnapConvert — tiny PDF-to-text tool. SaaS, instant delivery,
fully automated, low-risk category. Chosen for Dodo acceptance,
not for vision. Monetization hunting starts after first approval.
