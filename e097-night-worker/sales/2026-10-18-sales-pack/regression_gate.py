#!/usr/bin/env python3
"""The regression gate the audit leaves behind — the part that keeps the cut from creeping back.

    # one-time: record the baseline from the (already audited) window
    python3 regression_gate.py --log <tps-turns.jsonl> --write-baseline baseline.json

    # nightly / in CI: fail loudly when it regresses
    python3 regression_gate.py --log <tps-turns.jsonl> --baseline baseline.json

Fails (exit 1) on either of the two things the deliverable promises:

  * steady-state wall per turn (p50) above `baseline x 1.2`
  * wasted-turn rate above 5% (failed, aborted or zero-output turns — counted over every row,
    since waste has no warm-up, only latency does)

It also *reports* the provider roundtrip (p50 `preResponseMs`) against the baseline without
failing on it: that slice is mostly the provider's, and failing a client's CI for their
provider's latency would be dishonest. Everything else is the same arithmetic the report, the
panel and the preview use: `rest = wall − stream − tools − pre-response`, and a turn is wasted
when it failed, aborted or produced no output.

Standard library only (Python 3.9+), no network, no dependencies — it has to keep running on a
machine we no longer touch.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

WALL_FACTOR = 1.2
WASTED_RATE_LIMIT = 5.0


def usable(row: dict) -> bool:
    return (isinstance(row, dict) and isinstance(row.get("ts"), str)
            and all(isinstance(row.get(k), (int, float)) and not isinstance(row.get(k), bool)
                    for k in ("turnMsTotal", "llmDurationMs", "toolMsTotal", "output"))
            and row.get("outcome") in ("completed", "aborted", "error"))


def load(path: Path) -> list[dict]:
    rows = []
    for i, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as e:
            raise SystemExit(f"{path}:{i}: not JSON ({e.msg})")
        if usable(row):
            rows.append(row)
    return rows


def pct(values: list[float], p: float) -> float:
    s = sorted(values)
    return s[round(p * (len(s) - 1))] if s else float("nan")


def summarize(rows: list[dict], skip_first: int) -> dict:
    steady = rows[skip_first:] if len(rows) > skip_first else rows
    wall = [r["turnMsTotal"] for r in steady]
    pre = [r["preResponseMs"] for r in steady if isinstance(r.get("preResponseMs"), (int, float))]
    rest = [max(0, r["turnMsTotal"] - r["llmDurationMs"] - r["toolMsTotal"]
                - (r["preResponseMs"] if isinstance(r.get("preResponseMs"), (int, float)) else 0))
            for r in steady]
    # Waste is counted over EVERY row: a turn that failed before producing anything is waste
    # wherever it happened. Only the latency stats skip the cold start, because only latency
    # has a warm-up. (Skipping the first rows for waste would hide exactly the "it failed at
    # startup" case a gate exists to catch.)
    wasted = sum(1 for r in rows if r["outcome"] != "completed" or r["output"] == 0)
    return {
        "rows_total": len(rows), "rows_steady": len(steady), "skip_first": skip_first,
        "window": f"{rows[0]['ts'][:19]}Z → {rows[-1]['ts'][:19]}Z" if rows else "—",
        "wall_p50_ms": round(statistics.median(wall)) if wall else None,
        "wall_p90_ms": round(pct(wall, 0.9)) if wall else None,
        "wall_mean_ms": round(sum(wall) / len(wall)) if wall else None,
        "pre_p50_ms": round(statistics.median(pre)) if pre else None,
        "rest_p50_ms": round(statistics.median(rest)) if rest else None,
        "wasted_rate_pct": round(wasted / len(rows) * 100, 1) if rows else None,
    }


def fmt(ms: int | None) -> str:
    if ms is None:
        return "–"
    return f"{ms} ms" if ms < 1000 else f"{ms / 1000:.2f} s"


def main() -> None:
    ap = argparse.ArgumentParser(description="fail when the per-turn tax creeps back")
    ap.add_argument("--log", type=Path, required=True, help="tps-turns.jsonl (the client's)")
    ap.add_argument("--baseline", type=Path, default=Path("baseline.json"))
    ap.add_argument("--write-baseline", nargs="?", const=True,
                    help="record the current window as the baseline (review this once, by hand)")
    ap.add_argument("--skip-first", type=int, default=3,
                    help="turns to ignore as cold start (default 3)")
    ap.add_argument("--wall-factor", type=float, default=WALL_FACTOR)
    ap.add_argument("--wasted-limit", type=float, default=WASTED_RATE_LIMIT)
    args = ap.parse_args()

    rows = load(args.log)
    if not rows:
        raise SystemExit(f"{args.log}: no usable turn rows (needs turnMsTotal, llmDurationMs, "
                         f"toolMsTotal, output, outcome — the fields the monitor writes)")
    now = summarize(rows, args.skip_first)

    if args.write_baseline:
        dest = Path(args.baseline) if isinstance(args.write_baseline, str) else args.baseline
        payload = dict(now, created=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                       source=args.log.name, wall_factor=args.wall_factor,
                       wasted_rate_limit=args.wasted_limit)
        dest.write_text(json.dumps(payload, indent=1) + "\n")
        print(f"baseline written: {dest}")
        print(json.dumps(payload, indent=1))
        print("\nThis is a snapshot of a window you have already audited. Re-running the gate "
              "against it is what makes the cut stick; re-writing it silently is how a "
              "regression gets buried.")
        return

    # The gate is the part of the audit that runs unattended on the client's machine, so a
    # missing baseline is a message, not a traceback.
    if not args.baseline.exists():
        print(f"no baseline at {args.baseline}.\n"
              "The baseline is recorded once, deliberately, on the window you audited and the\n"
              "client accepted:\n"
              f"    python3 regression_gate.py --log {args.log.name} --baseline "
              f"{args.baseline.name} --write-baseline\n"
              "Re-baselining is never implicit: a gate that resets itself cannot catch a regression.")
        sys.exit(1)
    try:
        base = json.loads(args.baseline.read_text())
    except ValueError as e:
        print(f"baseline {args.baseline} is not valid JSON ({e}). Re-record it with --write-baseline.")
        sys.exit(1)
    print(f"window   {args.log.name}: {now['window']}  ({now['rows_steady']} steady turns of "
          f"{now['rows_total']}, latency stats skipping the first {now['skip_first']})")
    print(f"baseline {args.baseline.name}: {base.get('created', '?')} "
          f"({base.get('source', '?')}, {base.get('rows_steady', '?')} turns)\n")
    print(f"{'':22}{'baseline':>14}{'now':>14}{'limit':>14}")
    print(f"{'wall p50 per turn':22}{fmt(base['wall_p50_ms']):>14}{fmt(now['wall_p50_ms']):>14}"
          f"{'x' + str(args.wall_factor):>14}")
    print(f"{'wall p90 per turn':22}{fmt(base['wall_p90_ms']):>14}{fmt(now['wall_p90_ms']):>14}{'':>14}")
    print(f"{'wasted-turn rate (all)':22}{str(base['wasted_rate_pct']) + '%':>14}"
          f"{str(now['wasted_rate_pct']) + '%':>14}{'< ' + str(args.wasted_limit) + '%':>14}")
    print(f"{'provider roundtrip p50':22}{fmt(base.get('pre_p50_ms')):>14}{fmt(now['pre_p50_ms']):>14}"
          f"{'(reported only)':>14}")
    print(f"{'unexplained p50':22}{fmt(base.get('rest_p50_ms')):>14}{fmt(now['rest_p50_ms']):>14}{'':>14}\n")

    failures = []
    wall_limit = (base["wall_p50_ms"] or 0) * args.wall_factor
    if now["wall_p50_ms"] and base["wall_p50_ms"] and now["wall_p50_ms"] > wall_limit:
        failures.append(f"steady-state wall p50 rose to {fmt(now['wall_p50_ms'])} "
                        f"(baseline {fmt(base['wall_p50_ms'])} x {args.wall_factor} = "
                        f"{fmt(int(wall_limit))})")
    if now["wasted_rate_pct"] is not None and now["wasted_rate_pct"] > args.wasted_limit:
        failures.append(f"wasted-turn rate {now['wasted_rate_pct']}% is above {args.wasted_limit}%")

    for f in failures:
        print(f"FAIL {f}")
    if failures:
        print("\nThe tax crept back or turns are burning budget for nothing. Diagnose with the "
              "audit's own tooling (the preview reads this same file), then re-baseline "
              "deliberately:  python3 regression_gate.py --log "
              f"{args.log.name} --write-baseline {args.baseline.name}")
        raise SystemExit(1)
    print("PASS wall p50 within the baseline and the wasted-turn rate inside the limit.")
    if base.get("pre_p50_ms") and now["pre_p50_ms"]:
        delta = (now["pre_p50_ms"] - base["pre_p50_ms"]) / base["pre_p50_ms"] * 100
        if abs(delta) >= 20:
            print(f"note: the provider roundtrip moved {delta:+.0f}% (reported, not failed — "
                  f"that slice is mostly the provider's, not yours).")


if __name__ == "__main__":
    main()
