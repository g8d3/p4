# Audit delivery — our own fleet (500 message samples, 2026-10-18)

Window analysed: `2026-10-18`. Every number in these files comes from your log, from
your answers, or is labelled where we measured it ourselves.

| file | what it is |
|---|---|
| `breakdown.md` | one page per loop: segments, costs, tail, cuts summary, gate, method |
| `breakdown.html` | the same page as a file you can send |
| `cuts.md` | ranked fixes with effort, risk and a label per line, plus what we do not recommend |
| `budget.md` | the turn-budget formula with your numbers, and the gate that keeps it |
| `cuts.html` | cuts as a page |
| `budget.html` | budget as a page |
| `turns.csv` | your raw turns in the paper's column names; re-run the scripts on this |
| `cache-report.md` | cache hit rate, cached tokens per turn, wall at fixed context size |
| `size-curve.md` | overhead against carried context, as ranges, no coefficient |
| `cache-report.html` | cache report as a page |
| `size-curve.html` | size curve as a page |
| `regression_gate.py` | the gate you keep; run it nightly or in CI against baseline.json |

## Reproduce it

```
python3 audit_report.py --answers answers.json --log <your turns.jsonl> \
        --history <your history.jsonl> --outdir <this folder>
python3 regression_gate.py --log <your turns.jsonl> --write-baseline baseline.json
python3 regression_gate.py --log <your turns.jsonl> --baseline baseline.json
```

The two scripts are stdlib-only Python 3 and make no network calls.
