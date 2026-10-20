# FiloEterno roadmap — what gets built, in what order, and when it runs.

- [done] 01-tipjar-coin: ERC-20 + 1% fee treasury + holder votes. 5/5 tests, self-audit, local deploy. Runs: finished.
- [done] 02-lottery-coin (deployed locally, audited, probe-gated) — fee-fed weekly on-chain lottery for holders. Built automatically by the guard cycle (contract, tests, audit, probe, local deploy).
- [next] 03-gated-tool-coin: holding X unlocks a real tool. Builds itself on the continuous loop.
- [queued] Gate automation: red-first probe runs inside every build automatically (today it is a separate command). Runs: built as part of 02.
- [always] Guard cycle every 2h: build the [next] roadmap task if unstarted, then probe + credits check + page rebuild. Model spend inside daily/weekly caps.
