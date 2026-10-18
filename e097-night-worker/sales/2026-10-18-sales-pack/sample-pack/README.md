# The published Tier 2 examples — and the exact command that makes them

These are the four filled examples served at
<https://focalis.cc/audit/sample/{cuts,budget,cache-report,size-curve}.html>. They are generated
from a **window we publish** — not from the live turn log, which rotates:

| input | where it is published |
|---|---|
| the turn window (500 turns) | <https://focalis.cc/tps/fleet/fleet-turns-2026-10-18.jsonl> |
| the message-sample window (500 samples) | <https://focalis.cc/tps/fleet/fleet-history-2026-10-18.jsonl> |
| the answers | <https://focalis.cc/tps/fleet/example-answers.json> |

```sh
python3 audit_report.py --answers example-answers.json \
        --log   fleet-turns-2026-10-18.jsonl \
        --history fleet-history-2026-10-18.jsonl \
        --outdir sample-pack --html
```

Every figure on every page is labelled `[measured] / [example] / [assumption]` by the engine
itself, and the label `loop` in `example-answers.json` names these two files, so the page says
where its numbers come from.

`tests/sample-repro.py` is the evidence: it downloads those three files, re-runs the engine into a
temp directory and compares the four produced pages with the ones being served (byte for byte,
after undoing the two things the host adds to a served page: its analytics script and its
email-protection link rewriting). If a page drifts from the published inputs, that test fails.

**Why this changed on 2026-10-18.** The examples used to be generated from the *live* log, so the
window behind their figures rotated away and nobody could check them — the same failure R80 found
on the money pages. They are now a function of three published files.

**And the reason `export-history` exists:** publishing the turn window for this was how the
private `sessionName` field (the text of the prompt that opened a session — the turn log started
carrying it that day) nearly went into a public repository. `fleet/publish_fleet.py` now drops
`sessionName` from **both** logs, and `tests/sample-repro.py` fails if either published window
contains it.

`turns.csv` and `regression_gate.py` are the two files the client keeps; they are here so the pack
has a copy of the whole delivery.
