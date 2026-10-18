# The published Tier 2 examples — and the exact command that makes them

These are the four filled examples served at
<https://focalis.cc/audit/sample/{cuts,budget,cache-report,size-curve}.html>, generated
from **our own fleet** (the 500 most recent turn rows and the 500 most recent message
samples at generation time) with the example answers in `../audit-offer.md`'s intake shape:

```sh
python3 audit_report.py --answers answers.json \
        --log  /home/vuos/code/p4/.pi-web/tps-turns.jsonl \
        --history /home/vuos/code/p4/.pi-web/tps-history.jsonl \
        --outdir sample-pack --html
```

`answers.json` is the file `/tmp/night/r26/example-answers.json` (loop label, date,
`boot_ms: 929`, process model). Every figure on every page is labelled
`[measured] / [example] / [assumption]` by the engine itself.

**Why they were regenerated on 2026-10-18:** the route finding (the section `pricing.md`
sells — "the cut list says so with the numbers") had been added to the engine *after* the
examples were generated, so the published cut list was missing it: a deliverable we sell
that no prospect could see. The four pages were regenerated together, from one window, so
they agree with each other; `tests/deliverable-browser.py` now fails if the route section
disappears from the cut list again or if the four pages stop naming the same window.

`turns.csv` and `regression_gate.py` are the two files the client keeps; they are here so
the pack has a copy of the whole delivery.
