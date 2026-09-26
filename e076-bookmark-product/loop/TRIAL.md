# Trial protocol — same task across versions, scored (e076)

Goal (from loop/HARNESS_BAR.md gap #6): one fixed task T1 that runs
identically against any version checkout, producing a 0–100 score.
Versions are compared in loop/versions.json; raw runs in loop/trial-v*.json.

## Task T1 — "Core backup loop" (fixed seed, no keys, no network)

Seed tweets (ids fixed, text fixed):
- t1..t4 unique (2 xhr + 2 dom), t5 duplicate of t1 (dom, must count as dupe,
  must NOT overwrite xhr text — XHR wins).
- Labels: create `read-later` + `invoice`; attach both to t1.
- Search: `q=hello` matches t1 text; `label=read-later` narrows to t1.
- Webhook: register `https://example.com/hook`, re-register same URL
  (must stay 1 entry), import 1 more tweet → 1 outbound event logged.
- Approval: propose "Resume paused sync" → pending; empty title → 400;
  approve → approved; approve again → already-decided, still approved.
- Billing: GET /v1/billing/me catalog = free/monthly-7/yearly-99/lifetime-198;
  both webhooks without secrets → plan:test, never a paid plan.
- Referrals: attribute code FRIEND1 → attributed + `bv_ref` cookie;
  self code DEMO42 → self-referral.

## Scoring (100 pts, all-or-nothing per check)

| Group | Pts | Checks |
|---|---|---|
| Import | 25 | accepted==5 (5), dupes==1 (5), XHR-wins text kept (5), total==5 (5), source in {xhr,dom} (5) |
| Labels | 20 | 2 created (5), attach→labels on t1 (5), list contains both (5), label filter returns t1 (5) |
| Search | 15 | q=hello finds t1 (5), empty q returns all (5), unknown q returns 0 (5) |
| Webhooks | 10 | add ok (4), dupe ignored len==1 (3), import fires outbound event (3) |
| Approvals | 10 | propose pending (3), empty→400 (2), approve→approved (3), re-approve already-decided (2) |
| Billing+referrals | 10 | catalog prices (3), fiat test→test (2), crypto test→test (2), referral cookie+self (3) |
| Presentability (static) | 10 | hub+7 landing pages exist (3), sidepanel 5 tabs (2), English-only scan (3), js syntax ok (2) |

## How to run

  python3 loop/trial-check.py                 # scores working tree, prints JSON
  python3 loop/trial-check.py --port 8899     # against a running backend
  python3 loop/trial-check.py --save loop/trial-vX.json

The script starts its own backend copy on an ephemeral port by default
(never touches :8899), runs T1, kills it, then does static file checks.
No browser, no keys, no money. A version is PRESENTABLE only per the
leg-prompt rubric (real Chrome @390px); this scorer reports
`presentable_static` (necessary, not sufficient) and never claims more.

## History

- v0.8: protocol created + first scored run (this leg).
- Future: re-run same script per release; keep seeds frozen. If seeds must
  change, bump task to T2 and keep T1 results for history.
