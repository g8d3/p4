#!/usr/bin/env python3
"""The audit's delivery engine: a client's log + their three answers -> the breakdown.

    # deliver an audit
    python3 audit_report.py --answers client.json --log <tps-turns.jsonl> --out breakdown.md [--html breakdown.html]

    # regenerate the public sample from our own published numbers
    python3 audit_report.py --sample --html --out ../deliverables-sample.html

    # check the thing you just generated (format + internal arithmetic)
    python3 audit_report.py --self-check <breakdown.md>

Why a script: the deliverable is a page of measured numbers, and a page of numbers typed by
hand is where an audit goes wrong. Everything measurable comes from the log; everything
about volume and price comes from the answers file; the one figure that overlaps the offer
page's calculator is asked from `roi.compute()` so the report and the page cannot drift.

`client.json` (only `loop` is required; the rest falls back to the example values):

    {
      "loop": "checkout-agent",
      "date": "2026-10-17",
      "loops": 10, "turns_per_loop_per_day": 100, "workdays": 250,
      "model": "deepseek-v4.1-flash", "provider": "DeepSeek",
      "price_in": 0.27, "price_cache": 0.07, "price_out": 1.10, "cache_hit": 0.7,
      "in_tok": 40000, "out_tok": 400,
      "machine": "one Linux box, 8 cores, local SSD",
      "process_model": "one process per turn",
      "boot_ms": 372, "boot_measured_by": "us, outside the harness (paper 5.4; 372 ms warm / 940 ms cold, raw runs in procsplit/)",
      "gate_script": "regression_gate.py", "gate_schedule": "nightly, against baseline.json",
      "wasted_budget_pct": 5,
      "cuts": [{"change": "...", "effect": "...", "confidence": "measured"}]
    }
"""
from __future__ import annotations

import argparse
import html as htmllib
import json
import re
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import roi  # noqa: E402  (single source of the money arithmetic)

TEMPLATE = HERE / "deliverable-template.md"

OFFER_URL = "https://focalis.cc/audit/"
REPORT_URL = "https://focalis.cc/tps/"
CONTACT = "hello@focalis.cc"

# Our own published one-word-turn measurement (paper 5.4 / 1.1), used by --sample.
SAMPLE_ANSWERS = {
    "loop": "checkout-agent (example loop)", "date": "2026-10-17",
    "loops": 10, "turns_per_loop_per_day": 100, "workdays": 250,
    "model": "deepseek-v4.1-flash", "provider": "DeepSeek",
    "price_in": 0.27, "price_cache": 0.07, "price_out": 1.10, "cache_hit": 70,
    "in_tok": 40000, "out_tok": 400,
    "machine": "one Linux box, 8 cores, local SSD", "process_model": "one process per turn",
    "boot_ms": 372, "boot_p90_ms": 377, "pre_ms": 1554, "pre_p90_ms": 1748,
    "stream_ms": 3, "stream_p90_ms": 7, "tools_ms": 0, "tools_p90_ms": 0,
    "total_ms": 1974, "total_p90_ms": 2262,
    "unacc_p50_s": 2.7, "unacc_p90_s": 10.8, "worst_s": 300,
    "no_op_turns": 50, "live_turns": 137, "wasted_rate": 3.2,
    "wasted_turns": 16, "wasted_sample": 500,
    "outlier": {"n": "four of ten", "factor": "2-6",
                # the template already says "in a contiguous streak that then recovered", so this
                # value must not repeat it (it did, and the sentence read doubled on the published
                # sample page and in every client report).
                "cause": "we could not name the cause, so it is listed as unexplained "
                         "(paper 6) rather than sold as a finding"},
    "command": "agent-loop --once, one process per turn",
    "extra_notes": "",
}

CSS = """
:root { color-scheme: light dark; --fg:#14161a; --bg:#fff; --muted:#5b6270; --line:#e3e6ec; --accent:#1c5fd4; --card:#f7f8fa; }
@media (prefers-color-scheme: dark) { :root { --fg:#e8eaed; --bg:#101215; --muted:#9aa2b1; --line:#282c33; --accent:#79aaff; --card:#171a1f; } }
* { box-sizing: border-box; }
body { margin:0 auto; max-width:52rem; padding:1.6rem 1.2rem 3rem; background:var(--bg); color:var(--fg);
  font:16px/1.65 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
h1 { font-size:1.7rem; line-height:1.25; margin:.4rem 0 .6rem; }
h2 { margin-top:2.2rem; border-top:1px solid var(--line); padding-top:1rem; font-size:1.2rem; }
h3 { margin-top:1.6rem; font-size:1.05rem; }
table { border-collapse:collapse; width:100%; margin:1rem 0; font-size:.92rem; display:block; overflow-x:auto; }
th, td { border-bottom:1px solid var(--line); padding:.45rem .6rem; text-align:left; }
th { color:var(--muted); font-weight:500; }
code { font-family:ui-monospace, SFMono-Regular, Menlo, monospace; font-size:.9em;
  background:color-mix(in srgb, currentColor 8%, transparent); padding:.1rem .25rem; border-radius:.25rem; }
blockquote { border-left:3px solid var(--line); margin:1.2rem 0; padding:.2rem 0 .2rem 1rem; color:var(--muted); }
hr { border:0; border-top:1px solid var(--line); margin:2rem 0; }
strong { font-weight:600; }
.banner { background:var(--card); border:1px solid var(--line); border-radius:.5rem; padding:.8rem 1rem; font-size:.9rem; margin-bottom:1.4rem; }
footer { margin-top:3rem; font-size:.85rem; color:var(--muted); }
.tag { font-size:.85em; color:var(--muted); }
"""


# ---------------------------------------------------------------- log -> measurements
def usable(row: dict) -> bool:
    return (isinstance(row, dict) and isinstance(row.get("ts"), str)
            and isinstance(row.get("model"), str)
            and all(isinstance(row.get(k), (int, float)) and not isinstance(row.get(k), bool)
                    for k in ("turnMsTotal", "llmDurationMs", "toolMsTotal", "output"))
            and row.get("outcome") in ("completed", "aborted", "error"))


def pct(values: list[float], p: float) -> float:
    s = sorted(values)
    return s[round(p * (len(s) - 1))] if s else float("nan")


def measure(rows: list[dict]) -> dict:
    """Segments, tail and waste from the client's own turns."""
    seg: dict[str, list[float]] = {"pre": [], "pre_only": [], "stream": [], "tools": [], "rest": [], "wall": []}
    clamped = no_pre = wasted = 0
    wasted_in = wasted_out = 0.0
    for r in rows:
        has_pre = isinstance(r.get("preResponseMs"), (int, float))
        pre = r["preResponseMs"] if has_pre else 0
        if not has_pre:
            no_pre += 1
        rest = r["turnMsTotal"] - r["llmDurationMs"] - r["toolMsTotal"] - pre
        if rest < 0:
            clamped += 1
            rest = 0
        seg["pre"].append(pre)
        if has_pre:
            seg["pre_only"].append(pre)
        seg["stream"].append(r["llmDurationMs"])
        seg["tools"].append(r["toolMsTotal"])
        seg["rest"].append(rest)
        seg["wall"].append(r["turnMsTotal"])
        if r["outcome"] != "completed" or r["output"] == 0:
            wasted += 1
            wasted_in += r.get("input", 0) or 0
            wasted_out += r.get("output", 0) or 0
    n = len(rows)
    return dict(
        n=n, seg=seg, clamped=clamped, no_pre=no_pre, wasted=wasted,
        wasted_in=wasted_in, wasted_out=wasted_out,
        wasted_pct=wasted / n * 100 if n else 0.0,
        wall_total_ms=sum(seg["wall"]), window=(rows[0]["ts"][:10], rows[-1]["ts"][:10]),
        models=sorted({r["model"] for r in rows}),
        sum={k: sum(v) for k, v in seg.items()},
    )


def pick(m: dict, key: str, p: float, unit: str, fallback: float) -> float:
    """A segment statistic, or the sample constant when the log has no such column."""
    values = m["seg"][key]
    if values and (key != "pre_only" or len(values) == m["n"]) or (key == "pre_only" and values):
        return statistics.median(values) if p == 0.5 else pct(values, p)
    return fallback


def hours_per_year(ms: float, turns_year: int) -> float:
    return turns_year * ms / 1000 / 3600


def build_values(answers: dict, m: dict | None) -> tuple[dict, list[str], dict]:
    """Fill the template's placeholders. Returns (values, notes about what was assumed)."""
    a = dict(SAMPLE_ANSWERS)
    a.update({k: v for k, v in answers.items() if v is not None})
    if a.get("outlier"):
        a["outlier"] = {**SAMPLE_ANSWERS["outlier"], **a["outlier"]}
    notes: list[str] = []
    # The money line is the number a client reads first. Inheriting a missing rate from
    # SAMPLE_ANSWERS silently would print OUR example rate as if it were theirs, so it is
    # detected here, said in the notes block of the document (not only on stdout), and
    # labelled on the line itself.
    money_fields = ("price_in", "price_cache", "price_out", "in_tok", "out_tok", "cache_hit")
    missing_money = [k for k in money_fields if answers.get(k) is None]
    identity_fields = ("model", "provider", "process_model")
    missing_identity = [k for k in identity_fields if answers.get(k) is None]
    if missing_identity:
        notes.append("your answers did not name "
                     + ", ".join(f"`{k}`" for k in missing_identity)
                     + " — the report describes OUR example loop wherever it should describe "
                       "yours. The timings are still measured from your log; the model, the route "
                       "and the process model are not.")
    if missing_money:
        notes.append("your answers did not give "
                     + ", ".join(f"`{k}`" for k in missing_money)
                     + " — the token line below is computed with **our** example rates and is "
                       "**not your bill**. Send those six numbers and we re-run it in minutes.")
    # (meta is returned so the delivery folder can reuse the same computed numbers instead of
    # recomputing them differently — the rule that keeps the payback figure honest.)

    loops = a["loops"]
    tpd = loops * a["turns_per_loop_per_day"]
    turns_year = int(tpd * a["workdays"])

    if m:  # client log present: measure, and say where the boot number came from
        boot = a.get("boot_ms")
        if boot is None:
            boot = SAMPLE_ANSWERS["boot_ms"]
            notes.append("no boot measurement in the answers: the report uses our published "
                         f"{SAMPLE_ANSWERS['boot_ms']} ms (warm cache; 940 ms cold) and labels it "
                         "as ours, not as the client's")
        boot_p90 = a.get("boot_p90_ms", round(boot * 1.06))
        pre = pick(m, "pre_only", 0.5, "ms", a.get("pre_ms", float("nan")))
        pre_p90 = pick(m, "pre_only", 0.9, "ms", a.get("pre_p90_ms", float("nan")))
        stream = pick(m, "stream", 0.5, "ms", float("nan"))
        stream_p90 = pick(m, "stream", 0.9, "ms", float("nan"))
        tools = pick(m, "tools", 0.5, "ms", float("nan"))
        tools_p90 = pick(m, "tools", 0.9, "ms", float("nan"))
        total = pick(m, "wall", 0.5, "ms", float("nan"))
        total_p90 = pick(m, "wall", 0.9, "ms", float("nan"))
        unacc_p50 = statistics.median(m["seg"]["rest"]) / 1000
        unacc_p90 = pct(m["seg"]["rest"], 0.9) / 1000
        worst = max(m["seg"]["rest"]) / 1000
        wasted_rate = m["wasted_pct"]
        wasted_turns, wasted_sample = m["wasted"], m["n"]
        no_op, live = 0, m["n"]
        segment_note = (
            f"{m['no_pre']} of {m['n']} rows carry no pre-response column: for those the provider "
            f"roundtrip is inside the residual, so the split above is a lower bound."
            if m["no_pre"] else
            "Every row carries the pre-response column, so the provider roundtrip is separated "
            "from the residual.") + (
            f" {m['clamped']} row(s) had segments exceeding the turn wall (independent timers); "
            f"their residual is clamped to 0." if m["clamped"] else "")
        segment_note += (f" Boot is the one figure on this page that is not from your log: "
                         f"{a.get('boot_measured_by', 'measured outside the harness')}.")
    else:  # --sample: the published one-word-turn numbers
        boot, boot_p90 = a["boot_ms"], a["boot_p90_ms"]
        pre, pre_p90 = a["pre_ms"], a["pre_p90_ms"]
        stream, stream_p90 = a["stream_ms"], a["stream_p90_ms"]
        tools, tools_p90 = a["tools_ms"], a["tools_p90_ms"]
        total, total_p90 = a["total_ms"], a["total_p90_ms"]
        unacc_p50, unacc_p90, worst = a["unacc_p50_s"], a["unacc_p90_s"], a["worst_s"]
        wasted_rate, wasted_turns, wasted_sample = a["wasted_rate"], a["wasted_turns"], a["wasted_sample"]
        no_op, live = a["no_op_turns"], a["live_turns"]
        segment_note = (
            f"The rows do not sum exactly to the total: the total is process wall "
            f"({total} ms) while each row is that segment's median, leaving "
            f"{total - (boot + pre + stream + tools)} ms [measured] of process exit, teardown "
            f"and bookkeeping, which no single event delimits.")

    boot_source = a.get("boot_measured_by",
                        "us, measured from outside the harness (paper 5.4; 372 ms with the "
                        "startup cache warm, 940 ms cold)")
    money = roi.compute(argparse.Namespace(
        agents=loops, turns=a["turns_per_loop_per_day"], days=a["workdays"],
        in_tok=a["in_tok"], out_tok=a["out_tok"], cache_hit=a["cache_hit"] / 100 if a["cache_hit"] > 1 else a["cache_hit"],
        price_in=a["price_in"], price_cache=a["price_cache"], price_out=a["price_out"],
        floor_s=total / 1000, boot_s=boot / 1000, warm=False, miss_rate=0.3, miss_penalty_s=5.0,
        wasted=wasted_rate / 100, cut_input=0.35, cut_wall=0.20, hourly=0.0, tier=1400))

    def ms(v: float, tag: str = "[measured]") -> str:
        """Whole milliseconds, as the segment table's own header says (boot/pre/stream/tools).
        The total row is the one that reads in seconds, and the template does that itself."""
        return f"{v:.0f} ms {tag}"

    def hrs(v: float) -> str:
        return f"{v:.1f}" if v < 10 else f"{v:.0f}"

    cuts = make_cuts(a, boot, turns_year, boot_source)
    if m and (m["wasted_in"] or m["wasted_out"]):
        at_rates = (m["wasted_in"] * a["price_in"] + m["wasted_out"] * a["price_out"]) / 1e6
        waste_note = (f"{wasted_turns} of {wasted_sample} turns in your log. At your list rates those "
                      f"rows bought ${at_rates:,.2f} of input+output for nothing — *if your provider "
                      f"billed them at all*, which is your invoice to check, not ours. The wall time "
                      f"they burned is already in the totals above.")
        if len(m["models"]) > 1:
            waste_note += (f" The log mixes {len(m['models'])} models, so this uses your one rate for "
                           f"all of them; per-model rates would change it.")
    elif m:
        waste_note = (f"{wasted_turns} of {wasted_sample} turns in your log. Those rows report zero "
                      f"input and zero output tokens — they failed before the provider billed "
                      f"anything visible to us — so the honest number is the rate, not a cost. Your "
                      f"exposure is the rate x your volume.")
    else:
        waste_note = (f"{wasted_turns} of {wasted_sample} turns in our own sample; we quote no "
                      f"dollar figure for them — every one of those errors ran on a model with no "
                      f"public list price, so the honest number is the rate, not a cost. Your "
                      f"exposure is the rate x your volume.")

    values = {
        "«loop name»": a["loop"], "«date»": a["date"],
        "«n»": f"{live + no_op}", "«no-op series»": f"{no_op} no-op turns",
        "«live turns»": f"{live} live turns" + (" from your log" if m else " from our own fleet"),
        "«command»": a["command"],
        "«model»": a["model"] + (" (NOT YOURS — not given)" if "model" in missing_identity else ""),
        "«provider»": a["provider"] + (" (NOT YOURS — not given)" if "provider" in missing_identity else ""),
        "«machine»": a["machine"],
        "«one process per turn / warm process»": f"{a['process_model']}"
            + (" (so boot is paid every turn)" if "one process" in a["process_model"] else ""),
        "«boot-ms»": ms(boot), "«boot-p90»": ms(boot_p90),
        "«pre-ms»": ms(pre), "«pre-p90»": ms(pre_p90),
        "«stream-ms»": ms(stream), "«stream-p90»": ms(stream_p90),
        "«tools-ms»": ms(tools), "«tools-p90»": ms(tools_p90),
        "«total-s»": f"{total / 1000:.2f} s [measured]", "«total-p90»": f"{total_p90 / 1000:.1f} s [measured]",
        "«segment-note»": segment_note,
        "«turns-day»": f"{tpd:,} ({loops} loops x {a['turns_per_loop_per_day']} turns/day) "
                       + ("[example]" if m is None else "[from your answers]"),
        "«h-day»": f"{tpd * total / 1000 / 3600:.2f}",
        "«h-year»": hrs(hours_per_year(total, turns_year)),
        "«h-boot-year»": hrs(hours_per_year(boot, turns_year)),
        "«h-pre-year»": hrs(hours_per_year(pre, turns_year)),
        "«token-usd»": f"${money['year_tokens']:,.0f}", "«cache-hit»": f"{a['cache_hit'] * 100 if a['cache_hit'] <= 1 else a['cache_hit']:.0f}",
        "«wasted-rate»": f"{wasted_rate:.1f}",
        "«wasted-source»": "measured on your log" if m else "measured on our fleet",
        "«waste-note»": waste_note,
        "«unacc-p50»": f"{unacc_p50:.1f} s [measured]", "«unacc-p90»": f"{unacc_p90:.1f} s [measured]",
        "«worst»": f"{worst:.0f} s [measured]",
        "«outlier-n»": a["outlier"]["n"], "«threshold»": "the median", "«k»": a["outlier"]["factor"],
        "«outlier-cause»": a["outlier"]["cause"],
        "«keep the process warm»": cuts[0]["change"], "«boot-cut»": cuts[0]["change"],
        "«boot-cut-effect»": cuts[0]["effect"],
        "«context-cut»": cuts[1]["change"], "«context-cut-effect»": cuts[1]["effect"],
        "«third-cut»": cuts[2]["change"], "«third-cut-effect»": cuts[2]["effect"],
        "«third-cut-confidence»": cuts[2]["confidence"],
        "«gate-path»": a.get("gate_script", "regression_gate.py"),
        "«gate-how»": a.get("gate_schedule", "nightly, against the baseline in baseline.json"),
        "«baseline-x»": "baseline x 1.2", "«wasted-budget»": f"{a.get('wasted_budget_pct', 5)}",
        "«n-per-cell»": f"{live} turns in this run" if m else "5 reps for the decomposed one-word turn",
        "«jitter-s»": "1",
        "«logs-path»": a.get("logs_path", "the per-run logs we hand over (this page is not one of them)"),
        "«price»": f"{a['provider']} list (${a['price_in']:.2f} in / ${a['price_out']:.2f} out per MTok)",
        "«price-source»": ("[OUR EXAMPLE RATES — not yours]" if missing_money
                           else ("[from your answers]" if m else "[example]")),
        "«cache-hit-source»": "[from your answers]" if (m and "cache_hit" not in missing_money) else "[assumption]",
        "«notes»": ("**Read this first — what is assumed:**\n\n"
                    + "\n".join(f"- {n}" for n in notes) + "\n") if notes else "",
    }
    return values, notes, {"money": money, "cuts": cuts, "turns_year": turns_year, "boot_ms": boot}


# ---------------------------------------------------------------- route finding (2026-10-18)
# What the same base model costs on other routes, read off the published matrix
# (`routes/MATRIX.md`: each provider's own `/models` price metadata, snapshot ROUTES_DATE).
# A table in the file, not a live read: the engine makes no network calls, and a price
# quoted in a paid report must be the snapshot stated below, not whatever the API says
# that morning. Re-run `routes/matrix.py` before quoting any row: prices rotate.
# (anchor, route, $/M in, $/M out, $/M cache-read, first-token p50 ms on our keys or None).
ROUTES: list[tuple[str, str, float, float, float, int | None]] = [
    ("claude-haiku-5-5", "openrouter", 0.1, 0.5, 0.01, 1148),
    ("claude-haiku-5-5", "venice", 0.1, 0.5, 0.01, 778),
    ("claude-opus-5", "openrouter", 5.0, 25.0, 0.5, 2188),
    ("claude-opus-5", "venice", 5.0, 25.0, 0.5, 1248),
    ("claude-sonnet-5-5", "openrouter", 2.0, 10.0, 0.1, 1166),
    ("claude-sonnet-5-5", "venice", 2.0, 10.0, 0.1, 1191),
    ("deepseek-v3.2", "chutes", 1.0, 1.0, 0.1, 1386),
    ("deepseek-v3.2", "openrouter", 0.28, 0.42, 0.028, 2174),
    ("deepseek-v4-flash-0731", "chutes", 0.44, 1.32, 0.044, 1610),
    ("deepseek-v4-flash-0731", "openrouter", 0.0151, 0.45, 0.0151, 674),
    ("deepseek-v4-pro", "openrouter", 0.2088, 0.4176, 0.0174, 1158),
    ("deepseek-v4.1-flash", "chutes", 0.44, 1.32, 0.044, 1011),
    ("deepseek-v4.1-flash", "openrouter", 0.0648, 0.144, 0.0016, 680),
    ("gemini-3-8-flash", "openrouter", 0.825, 4.125, 0.0825, 2056),
    ("gemini-3-8-flash", "venice", 0.9375, 4.6875, 0.0938, 2263),
    ("gemini-3-flash-preview", "openrouter", 0.5, 3.0, 0.05, 838),
    ("gemini-3-flash-preview", "venice", 0.7, 3.75, 0.07, 1988),
    ("glm-5.1", "chutes", 0.98, 3.08, 0.098, 14819),
    ("glm-5.1", "openrouter", 0.966, 3.036, 0.1794, 1932),
    ("glm-5.2", "chutes", 1.25, 3.95, 0.125, None),
    ("glm-5.2", "openrouter", 0.62, 2.42, 0.14, 732),
    ("gpt-oss-120b", "groq", 0.15, 0.6, 0.075, 424),
    ("gpt-oss-120b", "openrouter", 0.15, 0.6, 0.075, 709),
    ("gpt-oss-20b", "groq", 0.075, 0.3, 0.0375, 604),
    ("gpt-oss-20b", "openrouter", 0.018, 0.09, 0.009, 1994),
    ("grok-4-7", "openrouter", 2.0, 6.0, 0.5, 2492),
    ("grok-4-7", "venice", 2.27, 6.8, 0.57, 2714),
    ("kimi-k2.6", "chutes", 0.45, 1.95, 0.045, 1488),
    ("kimi-k2.6", "openrouter", 0.65, 3.41, 0.15, 776),
    ("kimi-k3", "chutes", 1.85, 9.5, 0.185, 2136),
    ("kimi-k3", "openrouter", 0.304, 11.936, 0.21, 990),
    ("qwen3.6-27b", "chutes", 0.25, 2.0, 0.025, 1036),
    ("qwen3.6-27b", "openrouter", 0.25, 2.0, 0.025, 826),
    ("qwen3.8-27b", "chutes", 0.039, 1.25, 0.0039, 1748),
    ("qwen3.8-27b", "groq", 0.8, 4.0, 0.4, 290),
    ("qwen3.8-27b", "openrouter", 0.24, 2.2, 0.05, 731),
]
ROUTES_DATE = "2026-10-18"


def norm_model(name: str) -> str:
    """Drop the vendor prefix and the deployment suffixes so the same model compares.

    A dot and a hyphen are the same separator here on purpose: providers spell one model
    `claude-sonnet-5.5` and another `claude-sonnet-5-5`, and a client types whichever their
    config uses. Normalising both sides the same way is what makes the route comparison
    work for the closed models at all.
    """
    n = str(name).split("/")[-1].lower()
    n = re.sub(r"-(tee|turbo|fast|preview|free|contributor)$", "", n)
    n = n.replace("_", "-")
    return re.sub(r"[^a-z0-9]+", "-", n).strip("-")


def route_finding(a: dict, turns_year: int) -> str:
    """What the same model costs on the routes we measured, priced at the client's volume.

    `pricing.md` promises that "when every route charges the same list price we say that
    instead, and the finding is the latency". So this never goes silent while it has
    something true to say. Four shapes:

      * no model in the answers -> "" (there is nothing to price)
      * the model is not in the measured matrix -> say so; no comparison exists
      * the only route we measured is the client's own -> say so
      * other routes exist -> price them; if none is cheaper, report the latency instead

    Every price is labelled as measured on *our* keys, never as the client's bill.
    """
    want = norm_model(a.get("model", ""))
    if not want:
        return ""
    theirs = str(a.get("provider", "")).lower()
    measured = [r for r in ROUTES if norm_model(r[0]) == want]
    head = ["", "## The route: what the same model costs elsewhere", ""]
    base_models = len({r[0] for r in ROUTES})

    if not measured:
        return "\n".join(head + [
            f"`{a.get('model')}` is not one of the {base_models} base models we measured across "
            f"routes ({len(ROUTES)} priceable route/model pairs; each price read from that provider's own "
            f"metadata on {ROUTES_DATE}), so we make no route comparison for it. What the audit "
            "still measures on your own loop is the first-token latency of the route you actually "
            "use — that is where a route change shows up even when the list price is identical.",
            ""])

    candidates = [r for r in measured if not (theirs and theirs in r[1].lower())]
    if not candidates:
        return "\n".join(head + [
            f"The only route we measured for `{a.get('model')}` is the one you are on"
            + (f" (`{a.get('provider')}`)" if a.get("provider") else "")
            + ", so there is nothing to compare it against. The audit measures that route's "
            "first-token latency on your loop, and this table is re-measured rather than assumed.",
            ""])
    candidates.sort(key=lambda r: r[2])

    hit = a.get("cache_hit", 0) or 0
    hit = hit / 100 if hit > 1 else hit
    in_tok = a.get("in_tok", 0) or 0

    def input_year(price_in: float, price_cache: float | None) -> float:
        cache_price = price_in if price_cache is None else price_cache
        return in_tok * turns_year * ((1 - hit) * price_in + hit * cache_price) / 1e6

    def table(rows: list[tuple]) -> list[str]:
        out = ["| route | $/M in | $/M cache-read | first token p50 (ours) |", "|---|---|---|---|"]
        for _anchor, provider, pin, _pout, pcache, ttft in rows[:5]:
            cache_cell = ('$' + format(pcache, 'g')) if pcache else '–'
            out.append(f"| {provider} | ${pin:g} | {cache_cell} | "
                       f"{str(ttft) + ' ms' if ttft else '–'} |")
        return out

    their_cache = a.get("price_cache", None)
    their_cost = input_year(float(a.get("price_in", 0) or 0),
                            None if their_cache is None else float(their_cache))
    best = candidates[0]
    best_cost = input_year(best[2], best[4])

    if their_cost <= 0 or best_cost >= their_cost:
        # No price advantage to show: the promise is that we say that and report the latency.
        timed = [r for r in measured if r[5]]
        latency = ""
        if len(timed) >= 2:
            slow = max(timed, key=lambda r: r[5])
            fast = min(timed, key=lambda r: r[5])
            if slow[5] > fast[5]:
                latency = (f" On first-token latency the spread we measured is "
                           f"**{slow[5]} ms on `{slow[1]}` vs {fast[5]} ms on `{fast[1]}`** "
                           f"({slow[5] / fast[5]:.1f}x) — a switch buys time here, not money.")
        if their_cost <= 0:
            why = ("your answers do not give a price for your route, so we cannot compute a "
                   "difference against it")
        else:
            why = (f"none of the routes we can price is cheaper than the "
                   f"${a.get('price_in')}/M input your answers give for your route")
        return "\n".join(head + [
            f"We measured `{a.get('model')}` on the routes we can reach, reading each provider's "
            f"own published price ({ROUTES_DATE}):", "", *table(measured),
            "", f"At your volume ({turns_year:,} turns/year, {in_tok:,} input tokens per turn, "
            f"{hit * 100:.0f}% cached) {why}. **The finding is the latency, not a price cut.**"
            + latency, "",
            "**Labels:** the prices are the providers' own metadata and the latency is our "
            "measurement, both on our keys and not on yours. Re-run `routes/matrix.py` before "
            "quoting any row: prices rotate.", ""])

    saving = their_cost - best_cost
    # When the client does not give a cache-read rate we price their cached input at their input
    # rate (the conservative fallback). If the route we compare against charges much less for
    # cached input, that assumption is most of the difference — so it is said, not hidden.
    cache_note = ""
    if their_cache is None and best[4] and best[4] != best[2]:
        cache_note = (f" **Assumption behind that difference:** your answers did not give a "
                      f"cache-read rate, so your cached input is priced at your input rate "
                      f"(${a.get('price_in')}/M) while `{best[1]}` charges ${best[4]:g}/M for cached "
                      f"input — that is most of the gap. Send us your cached rate and we recompute it.")
    return "\n".join(head + [
        f"Your answers price `{a.get('model')}` at ${a.get('price_in')}/M input"
        + (f" on {a.get('provider')}" if a.get("provider") else "")
        + f". We measured the same base model on the routes we can reach, reading each "
        f"provider's own published price ({ROUTES_DATE}):", "", *table(candidates),
        "", f"At your volume ({turns_year:,} turns/year, {in_tok:,} input tokens per turn,"
        f" {hit * 100:.0f}% cached) the input line is **${their_cost:,.0f}/year** on your route and",
        f"**${best_cost:,.0f}/year** on `{best[1]}` — a difference of **${saving:,.0f}/year**,"
        " before any output-token difference." + cache_note, "",
        "**Labels, so this is not mistaken for your own bill:** the prices are the providers' own",
        "metadata and the latency is our measurement, both on our keys and not on yours. Verify on",
        "your account before switching, and re-run the gate after any switch — a different",
        "deployment can behave differently even at the same model name. Re-run `routes/matrix.py`",
        "before quoting any row: prices rotate.", ""])


def make_cuts(a: dict, boot_ms: float, turns_year: int, boot_source: str) -> list[dict]:
    """The ranked cut list. Defaults are the three we stand behind; `cuts` in the answers file
    replaces them with the client's own profile."""
    cuts = a.get("cuts") or [
        {"change": "keep the process warm", "effect":
            f"-{boot_ms / 1000:.2f} s/turn = -{hours_per_year(boot_ms, turns_year):.0f} h/year at this volume "
            f"[measured boot: {boot_source}]", "confidence": "measured", "effort": "low",
         "risk": "none to correctness; watch long-lived process state"},
        {"change": "cut carried context from 108 KB to 30 KB [example]",
         "effect": "-0.9 s/turn is illustrative [example]: we retracted a size coefficient "
                   "(paper 8), so what you buy is the before/after series on your own loop",
         "confidence": "measured on your loop", "effort": "medium",
         "risk": "compaction can lose task state; the gate catches the wall, not the quality"},
        {"change": "cap tool-result size before it enters the transcript",
         "effect": "not yet measured on this loop: we would run the series first",
         "confidence": "hypothesis", "effort": "low", "risk": "truncated tool output changes behaviour"},
    ]
    while len(cuts) < 3:
        cuts.append({"change": "«profile»", "effect": "«not measured yet»",
                     "confidence": "hypothesis", "effort": "?", "risk": "?"})
    return cuts


def cuts_markdown(cuts: list[dict], answers: dict, route_text: str = "") -> str:
    lines = [f"# Cuts — {answers.get('loop', 'the loop')}", "",
             "Ranked by measured effect on *this* loop. Every line carries its own label:",
             "`measured` (from the run), `measured on your loop` (before/after series), or",
             "`hypothesis` (we would run the series first).", "",
             "| # | change | expected effect | confidence | effort | risk |", "|---|---|---|---|---|---|"]
    for i, c in enumerate(cuts, 1):
        lines.append(f"| {i} | {c['change']} | {c['effect']} | {c['confidence']} | "
                     f"{c.get('effort', '?')} | {c.get('risk', '?')} |")
    lines += ["", "## Explicitly not recommended, with reasons", "",
              "- **Cache discipline** — did not reproduce in our own data (paper §6). Measured and",
              "  reported in `cache-report.md`; not sold as a lever.",
              "- **Startup-scan scoping** — startup does not scale with the session store (paper §7).",
              "- **A size coefficient** — mis-stated by 10x and would not rebuild (paper §8).",
              "", "If your profile shows no lever worth pulling, the implementation half is refunded;",
              "we would rather say that than ship a preset playbook.", ""]
    if route_text:
        lines += route_text.split("\n")
    return "\n".join(lines)


def budget_markdown(values: dict, answers: dict, money: dict, turns_year: int) -> str:
    a = {"loops": answers.get("loops", 10), "tpd": answers.get("turns_per_loop_per_day", 100),
         "days": answers.get("workdays", 250)}
    turns_day = a["loops"] * a["tpd"]
    lines = [f"# Turn budget — {answers.get('loop', 'the loop')}", "",
             "The formula and the numbers behind it, so the budget can live in your code instead of",
             "in a spreadsheet.", "",
             "```", "cost_per_turn  = (in_tok x price_in + cache_tok x price_cache + out_tok x price_out) / 1e6",
             "wall_per_turn  = boot + pre_response + stream + tools + unexplained",
             "monthly_cost   = cost_per_turn x turns_per_day x 30", "```", "",
             "| term | value | source |", "|---|---|---|",
             f"| turns/day | {turns_day:,} | your answers |",
             f"| turns/year | {turns_year:,} | your answers x workdays |",
             f"| wall per turn (p50) | {values['«total-s»']} | measured from your log |",
             f"| boot per turn | {values['«boot-ms»']} | {answers.get('boot_measured_by', 'measured outside the harness')} |",
             f"| provider roundtrip (p50) | {values['«pre-ms»']} | measured from your log |",
             f"| tokens per turn | {answers.get('in_tok', '?')} in / {answers.get('out_tok', '?')} out | your answers |",
             f"| token line | {values['«token-usd»']}/year | `roi.py`, same function as the offer calculator |",
             f"| wasted turns | {values['«wasted-rate»']}% | {values['«wasted-source»']} |", "",
             "**The gate that keeps it:** `regression_gate.py` + `baseline.json` (delivered with",
             "Tier 2+). `python3 regression_gate.py --log tps-turns.jsonl --baseline baseline.json`",
             "exits non-zero when wall p50 passes `baseline x 1.2` or the wasted-turn rate passes 5%.",
             "Wire it into the job that runs the loop, and the budget stops being a one-off.", ""]
    return "\n".join(lines)


def size_curve_markdown(samples: list[dict], bucket_kb: int = 8) -> str:
    """Overhead vs context size, as ranges — no coefficient (paper §8)."""
    ok = [s for s in samples if s.get("status") == "ok" and s.get("streamed") is not False]
    buckets: dict[int, list[float]] = {}
    for s in ok:
        ctx = (s.get("input", 0) or 0) + (s.get("cacheRead", 0) or 0)
        buckets.setdefault(int(round(ctx / (bucket_kb * 1024))), []).append(s.get("durationMs", 0))
    lines = ["# Size curve — overhead against carried context", "",
             f"From {len(ok)} ratable message samples, bucketed to the nearest {bucket_kb} KB.",
             "**Ranges, not a slope.** We tried to fit a size coefficient of our own and it did not",
             "reproduce (paper §8), so this page reports what your sizes do and stops there.", "",
             "| context size | rows | wall p50 | wall p90 |", "|---|---|---|---|"]
    for key in sorted(buckets):
        v = sorted(buckets[key])
        lines.append(f"| ~{int(key * bucket_kb)} KB | {len(v)} | {statistics.median(v) / 1000:.2f} s | "
                     f"{pct(v, 0.9) / 1000:.2f} s |")
    lines += ["", "Caveats that apply to every row above: context size is confounded with cache state,",
              "model and task type; a bucket with a handful of rows is an anecdote, not a rate; and",
              "your own before/after series is the only honest way to price a compaction change.", ""]
    return "\n".join(lines)


def turns_csv(rows: list[dict], answers: dict) -> str:
    """The raw data, in the paper's own column names (acceptance says it must reproduce)."""
    head = "harness,run,wall_s,llm_ms,total_ms,unacc_ms,in_tok,cache_tok,out_tok,notes"
    out = [head]
    harness = str(answers.get("command", answers.get("loop", "loop"))).replace(",", " ")
    for r in rows:
        pre = r["preResponseMs"] if isinstance(r.get("preResponseMs"), (int, float)) else 0
        unacc = max(0, r["turnMsTotal"] - r["llmDurationMs"] - r["toolMsTotal"] - pre)
        out.append(",".join([harness, str(r.get("turnIndex", "")), f"{r['turnMsTotal'] / 1000:.2f}",
                             str(r["llmDurationMs"]), str(r["turnMsTotal"]), str(unacc),
                             str(r.get("input", "")), "", str(r.get("output", "")),
                             f"{r.get('outcome', '')} pre={pre}"]))
    return "\n".join(out) + "\n"


def index_markdown(files: list[tuple[str, str]], answers: dict, log_name: str) -> str:
    lines = [f"# Audit delivery — {answers.get('loop', 'the loop')}", "",
             f"Window analysed: `{log_name}`. Every number in these files comes from your log, from",
             "your answers, or is labelled where we measured it ourselves.", "",
             "| file | what it is |", "|---|---|"]
    for name, what in files:
        lines.append(f"| `{name}` | {what} |")
    lines += ["", "## Reproduce it", "",
              "```", "python3 audit_report.py --answers answers.json --log <your turns.jsonl> \\",
              "        --history <your history.jsonl> --outdir <this folder>",
              "python3 regression_gate.py --log <your turns.jsonl> --write-baseline baseline.json",
              "python3 regression_gate.py --log <your turns.jsonl> --baseline baseline.json",
              "```", "",
              "The two scripts are stdlib-only Python 3 and make no network calls.", ""]
    return "\n".join(lines)


def write_delivery(outdir: Path, values: dict, answers: dict, markdown_text: str, rows: list[dict],
                   samples: list[dict] | None, money: dict, turns_year: int,
                   cuts: list[dict], html: bool, sample: bool = False) -> list[tuple[str, str]]:
    """The whole delivery folder: the six deliverables the offer lists, plus an index."""
    outdir.mkdir(parents=True, exist_ok=True)
    files: list[tuple[str, str]] = []
    banner = sample_banner() if sample else client_banner(values)
    (outdir / "breakdown.md").write_text(markdown_text)
    files.append(("breakdown.md", "one page per loop: segments, costs, tail, cuts summary, gate, method"))
    if html:
        (outdir / "breakdown.html").write_text(to_html(markdown_text, banner))
        files.append(("breakdown.html", "the same page as a file you can send"))
    merged = dict(SAMPLE_ANSWERS)
    merged.update(answers)
    cuts_text = cuts_markdown(cuts, answers, route_finding(merged, turns_year))
    (outdir / "cuts.md").write_text(cuts_text)
    files.append(("cuts.md", "ranked fixes with effort, risk and a label per line, plus what we do not recommend"))
    budget_text = budget_markdown(values, answers, money, turns_year)
    (outdir / "budget.md").write_text(budget_text)
    files.append(("budget.md", "the turn-budget formula with your numbers, and the gate that keeps it"))
    if html:
        for name, md_text in (("cuts", cuts_text), ("budget", budget_text)):
            (outdir / f"{name}.html").write_text(to_html(md_text, banner))
            files.append((f"{name}.html", f"{name} as a page"))
    (outdir / "turns.csv").write_text(turns_csv(rows, answers))
    files.append(("turns.csv", "your raw turns in the paper's column names; re-run the scripts on this"))
    if samples is not None:
        cache_md, curve_md = cache_report_markdown(cache_stats(samples), answers), size_curve_markdown(samples)
        (outdir / "cache-report.md").write_text(cache_md)
        (outdir / "size-curve.md").write_text(curve_md)
        files.append(("cache-report.md", "cache hit rate, cached tokens per turn, wall at fixed context size"))
        files.append(("size-curve.md", "overhead against carried context, as ranges, no coefficient"))
        if html:
            for name, md_text in (("cache-report", cache_md), ("size-curve", curve_md)):
                (outdir / f"{name}.html").write_text(
                    to_html(md_text, cache_banner(answers) if (name == "cache-report" and not sample) else banner))
                files.append((f"{name}.html", f"{name.replace('-', ' ')} as a page"))
    gate = Path(__file__).parent / "regression_gate.py"
    if gate.exists():
        (outdir / "regression_gate.py").write_text(gate.read_text())
        files.append(("regression_gate.py", "the gate you keep; run it nightly or in CI against baseline.json"))
    (outdir / "INDEX.md").write_text(index_markdown(files, answers, rows[0]["ts"][:10] if rows else "?"))
    return files


# ---------------------------------------------------------------- cache report (Tier 2)
def cache_stats(samples: list[dict], bucket_kb: int = 8) -> dict:
    """Cache behaviour from the monitor's message samples: hit rate, cached tokens per turn, and
    wall at fixed context size. Report-only — our own data showed no separating effect (paper 6),
    so the verdict below says what *their* rows show, including "nothing separates"."""
    ok = [s for s in samples if s.get("status") == "ok" and s.get("streamed") is not False]
    excluded = len(samples) - len(ok)
    if not ok:
        # `window` is part of the contract: the markdown renders it in its first line. Omitting
        # it here made the "no usable samples" path (which the markdown implements) unreachable —
        # the report crashed with a KeyError instead of telling the client to send the history file.
        return {"n": 0, "excluded": excluded, "hit_rate": None, "hit_rate_all": None,
                "cached_per_turn": None, "cached_per_turn_mean": None, "buckets": [],
                "verdict": "no usable samples", "window": None}
    total_in = sum(s.get("input", 0) for s in ok)
    total_cache = sum(s.get("cacheRead", 0) for s in ok)
    hit_rate = total_cache / (total_in + total_cache) if (total_in + total_cache) else None
    all_in = sum(s.get("input", 0) or 0 for s in samples)
    all_cache = sum(s.get("cacheRead", 0) or 0 for s in samples)
    hit_rate_all = all_cache / (all_in + all_cache) if (all_in + all_cache) else None
    per_turn = [s.get("cacheRead", 0) for s in ok]
    buckets: dict[int, dict[str, list[float]]] = {}
    for s in ok:
        ctx = (s.get("input", 0) or 0) + (s.get("cacheRead", 0) or 0)
        key = int(round(ctx / (bucket_kb * 1024)))
        cls = "hit" if ctx and (s.get("cacheRead", 0) / ctx) > 0.5 else "miss"
        buckets.setdefault(key, {"hit": [], "miss": []})[cls].append(s.get("durationMs", 0))
    paired = []
    for key in sorted(buckets):
        h, m = buckets[key]["hit"], buckets[key]["miss"]
        if len(h) >= 2 and len(m) >= 2:
            mh, mm = statistics.median(h), statistics.median(m)
            paired.append({"ctx_kb": int(key * bucket_kb), "rows_hit": len(h), "rows_miss": len(m),
                           "wall_hit_ms": round(mh), "wall_miss_ms": round(mm),
                           "delta_pct": round((mh - mm) / mm * 100, 1) if mm else None})
    # Only buckets with >= 3 rows per class count as evidence; thinner ones are printed as
    # context but must not decide the verdict (two rows is not a separation test).
    evidence = [p for p in paired if min(p["rows_hit"], p["rows_miss"]) >= 3 and p["delta_pct"] is not None]
    faster = [p for p in evidence if p["delta_pct"] <= -10]
    slower = [p for p in evidence if p["delta_pct"] >= 10]
    if not paired:
        verdict = ("not enough rows at the same context size to compare cache states; the overall "
                   "figures below mix sizes and are not a separation test")
    elif not evidence:
        verdict = ("no context size has 3+ rows in both classes, so this window cannot separate "
                   "cache states at fixed size. Reported, not prescribed.")
    elif faster and not slower:
        verdict = (f"cache state separated wall at {len(faster)} of {len(evidence)} comparable sizes "
                   f"(cached rows faster, table below). Reported, not prescribed: we still do not sell "
                   f"cache discipline, and one bucket is not a mechanism.")
    elif slower and not faster:
        verdict = (f"the cached rows were **slower** at {len(slower)} of {len(evidence)} comparable "
                   f"sizes — the confounded direction: long cached contexts are the expensive sessions, "
                   f"so this is not evidence that caching hurts. Reported, no mechanism drawn.")
    elif faster or slower:
        verdict = (f"cache state does **not** separate consistently in your window: cached rows were "
                   f"faster at {len(faster)} and slower at {len(slower)} comparable sizes (paper 6 found "
                   f"the same absence in ours). Reported, not prescribed.")
    else:
        verdict = (f"no context size separates the two classes by 10% or more in this window, so cache "
                   f"state does not separate fast from slow turns here — the same absence we found in "
                   f"our own 500-turn sample (paper 6). Reported, not prescribed.")
    return {"n": len(ok), "excluded": excluded, "hit_rate": hit_rate, "hit_rate_all": hit_rate_all, "cached_per_turn": statistics.median(per_turn),
            "cached_per_turn_mean": statistics.mean(per_turn), "buckets": paired, "verdict": verdict,
            "window": (ok[0]["ts"][:10], ok[-1]["ts"][:10])}


def cache_report_html(c: dict, answers: dict) -> str:
    md_text = cache_report_markdown(c, answers)
    return to_html(md_text, cache_banner(answers))


def cache_banner(answers: dict) -> str:
    return f"""
<div class="banner">
  <strong>SAMPLE — a cache report on our own data, not a client result.</strong> Tier 2 ships
  this page for <em>your</em> loops: hit rate, cached tokens per turn, and wall at fixed context
  size. It is report-only — where the rows show no separating effect (ours do not, paper §6) the
  page says so instead of prescribing cache discipline.
  <br>Offer: <a href="{OFFER_URL}">{OFFER_URL}</a> ·
  paper: <a href="{REPORT_URL}">{REPORT_URL}</a> · contact: <a href="mailto:{CONTACT}">{CONTACT}</a>
</div>
"""


def client_cache_banner(answers: dict) -> str:
    return f"""
<div class="banner">
  <strong>Client deliverable — cache report (Tier 2).</strong> Measured from the message samples
  you supplied. Report-only: where your rows show no separating effect, this page says so rather
  than prescribing cache discipline. Thresholds used are stated in the method section.
  <br>Offer: <a href="{OFFER_URL}">{OFFER_URL}</a> · contact: <a href="mailto:{CONTACT}">{CONTACT}</a>
</div>
"""


def cache_report_markdown(c: dict, answers: dict) -> str:
    where = (f", window {c['window'][0]} → {c['window'][1]}" if c.get("window") else "")
    lines = [f"# Cache report — {answers.get('loop', 'the loop')}", "",
             f"Measured from the monitor's message samples ({c['n']} OK rows, {c['excluded']} excluded "
             f"as failed/replayed){where}.", ""]
    if not c["n"]:
        return "\n".join(lines + ["No usable samples in the history file — send `tps-history.jsonl` "
                                 "from the same workspace as the turn log.", ""])
    lines += [
        f"- **Cache-hit rate**: {c['hit_rate'] * 100:.0f}% [measured] over the {c['n']} rows we can rate"
        + (f" ({c['hit_rate_all'] * 100:.0f}% over every row in the file, including the excluded ones)"
           if c.get("hit_rate_all") is not None else ""),
        f"- **Cached tokens per turn**: p50 {c['cached_per_turn']:,.0f}, mean {c['cached_per_turn_mean']:,.0f} [measured]",
        f"- **Verdict**: {c['verdict']}", ""]
    if c["buckets"]:
        lines += ["## Wall at fixed context size", "",
                  "| context size | rows cached | wall cached | rows uncached | wall uncached | delta |",
                  "|---|---|---|---|---|---|"]
        for b in c["buckets"]:
            lines.append(f"| ~{b['ctx_kb']} KB | {b['rows_hit']} | {b['wall_hit_ms'] / 1000:.2f} s | "
                         f"{b['rows_miss']} | {b['wall_miss_ms'] / 1000:.2f} s | {b['delta_pct']:+.0f}% |")
        lines.append("")
    lines += ["## Method and limits", "",
              "- Rows with `status: failed` or `streamed: false` are excluded: their durations are not",
              "  generation time, and including them is how a cache table turns into a fake finding.",
              "- Context size is bucketed to the nearest 8 KB and cache state is >50% of the context",
              "  cached; both thresholds are stated parameters, not measurements, so you can re-run them",
              "  differently. Every figure above comes from the sample file.",
              "- We do **not** sell cache discipline. This page reports your rows; where they show no",
              "  separating effect it says so, exactly as our own 500-turn sample did (paper §6).", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------- render
def render_markdown(values: dict, raw: str | None = None) -> str:
    text = raw if raw is not None else TEMPLATE.read_text()
    marker = "\n---\n"
    if marker in text and raw is None:
        text = text.split(marker, 1)[1]
    for key in sorted(values, key=len, reverse=True):
        text = text.replace(key, values[key])
    left = sorted(set(re.findall(r"«[^»]*»", text)))
    if left:
        raise SystemExit("placeholders with no value: " + ", ".join(left))
    return text


def to_html(markdown_text: str, banner: str, title: str = "Per-loop tax breakdown",
            description: str = "Where the wall-clock of one agent loop goes, measured per turn.") -> str:
    try:
        import markdown as md
    except ImportError:  # pragma: no cover
        raise SystemExit("pip install markdown to emit HTML (the markdown output needs nothing)")
    body = md.markdown(markdown_text, extensions=["tables", "fenced_code", "sane_lists"])
    for tag in ("measured", "example", "assumption"):
        body = body.replace(f"[{tag}]", f'<span class="tag">[{tag}]</span>')
    out = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<style>{CSS}</style></head>
<body>
{banner}
{body}
<footer>Generated by the audit's delivery script; the offer this belongs to is
<a href="{OFFER_URL}">{OFFER_URL}</a>. The page ships no tracking and no external requests;
the hosted copy gets Cloudflare's cookieless page-view beacon.</footer>
</body></html>
"""
    for tag in ("code", "strong", "em", "a"):
        if out.count(f"<{tag}") != out.count(f"</{tag}>"):
            raise SystemExit(f"unbalanced <{tag}>: a fill value leaked markdown syntax")
    return out


def sample_banner() -> str:
    return f"""
<div class="banner">
  <strong>SAMPLE — not a client result.</strong> This is the blank template filled with one
  example loop so you can see the shape of what you get. Every figure is tagged
  <em>[measured]</em> (ours, same numbers as the paper), <em>[example]</em> (an
  illustrative volume) or <em>[assumption]</em> (a parameter you replace). Our client
  deliverables carry the client's own numbers and none of these.
  <br>Offer and prices: <a href="{OFFER_URL}">{OFFER_URL}</a> ·
  paper: <a href="{REPORT_URL}">{REPORT_URL}</a> · contact: <a href="mailto:{CONTACT}">{CONTACT}</a>
  <br>Tier 2 also ships these, filled from our own data:
  <a href="https://focalis.cc/audit/sample/cache-report.html">cache report</a> ·
  <a href="https://focalis.cc/audit/sample/size-curve.html">size curve</a> ·
  <a href="https://focalis.cc/audit/sample/cuts.html">cuts</a> ·
  <a href="https://focalis.cc/audit/sample/budget.html">turn budget</a>.
</div>
"""


def client_banner(values: dict) -> str:
    return f"""
<div class="banner">
  <strong>Client deliverable.</strong> Measured from the turn log you supplied
  ({htmllib.escape(str(values['«loop name»']))}), labelled <em>[measured]</em> where it comes
  from your log or our published measurements, <em>[example]</em> where it is an
  illustrative parameter and <em>[assumption]</em> where it is a number you replace. The
  boot figure is marked with who measured it. Raw logs stay yours.
</div>
"""


# ---------------------------------------------------------------- self-check
def self_check(path: Path) -> int:
    """Format and arithmetic checks on a generated report."""
    bad = 0
    text = path.read_text()
    body = re.sub(r"<[^>]+>", " ", text) if path.suffix == ".html" else text
    checks = [
        ("no unfilled placeholder", "«" not in body and "»" not in body),
        ("says what is measured", "[measured]" in body),
        ("carries the boot caveat", "boot" in body.lower()),
        ("mentions the retracted mechanisms", "not recommended" in body),
        ("has the regression gate", "regression" in body.lower()),
    ]
    seg = {k: float(v.replace(",", "")) for k, v in re.findall(r"\| ([a-z\- ]+) \| ([\d.]+) s \[measured\]", body)}
    total = seg.get("**total wall per turn**")
    if total:
        parts = sum(seg.get(k, 0) for k in ("boot (process start → first event)",
                                            "pre-response (turn start → assistant message start)",
                                            "stream (first token → end)", "tools"))
        checks.append((f"segments do not exceed the total ({parts:.2f} <= {total:.2f})", parts <= total + 0.01))
    for name, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'} {name}")
        bad += 0 if ok else 1
    print(f"\n{len(checks) - bad}/{len(checks)} checks passed on {path.name}")
    return 1 if bad else 0


def main() -> None:
    ap = argparse.ArgumentParser(description="generate, or check, an audit breakdown")
    ap.add_argument("--answers", type=Path, help="client.json (the three answers + prices)")
    ap.add_argument("--log", type=Path, help="the client's tps-turns.jsonl")
    ap.add_argument("--sample", action="store_true", help="use our published example loop")
    ap.add_argument("--banner", choices=("sample", "client"),
                    help="which banner to print (default: sample with --sample, client otherwise)")
    ap.add_argument("--out", type=Path, help="write the markdown here")
    ap.add_argument("--outdir", type=Path,
                    help="write the whole delivery folder (breakdown, cuts, budget, csv, cache, size curve, gate, index)")
    ap.add_argument("--html", nargs="?", const=True, help="also write HTML (optionally to this path)")
    ap.add_argument("--history", type=Path, help="the monitor's tps-history.jsonl (Tier 2 cache report)")
    ap.add_argument("--cache-out", type=Path, help="where to write cache-report.md (default: next to --out)")
    ap.add_argument("--cache-html", nargs="?", const=True,
                    help="also write the cache report as HTML (for the public example page)")
    ap.add_argument("--self-check", type=Path, help="check an existing generated file")
    args = ap.parse_args()

    if args.self_check:
        raise SystemExit(self_check(args.self_check))

    if args.outdir:                      # a delivery is a folder: create it before writing into it
        args.outdir.mkdir(parents=True, exist_ok=True)
        if not args.out:
            args.out = args.outdir / "breakdown.md"
    answers = json.loads(args.answers.read_text()) if args.answers else {}
    if args.sample:
        # not `{}`: build_values() merges the client's answers over SAMPLE_ANSWERS and now
        # reports any money field the client did not give. An empty dict would make the sample
        # page accuse itself of missing rates.
        answers = dict(SAMPLE_ANSWERS)
    m = None
    if args.log:
        raw = [json.loads(l) for l in args.log.read_text().splitlines() if l.strip()]
        rows = [r for r in raw if usable(r)]
        if not rows:
            raise SystemExit(
                f"{args.log}: no usable turn rows ({len(raw)} lines). A row needs: ts, model, "
                "turnMsTotal, llmDurationMs, toolMsTotal, output (numbers) and outcome "
                "(completed | aborted | error). If the log is from another harness, map its "
                "columns in the free preview (https://focalis.cc/audit/preview/) or send it to "
                "us: writing that adapter is part of the audit.")
        m = measure(rows)
        print(f"read {m['n']} usable turns from {args.log.name} "
              f"({m['window'][0]} → {m['window'][1]}, models: {', '.join(m['models'])})")
    values, notes, meta = build_values(answers, m)
    text = render_markdown(values)
    out = args.out or Path("breakdown.md")
    out.write_text(text)
    print(f"wrote {out} ({len(text) / 1024:.1f} KB), every placeholder filled")
    if args.html:
        dest = Path(args.html) if isinstance(args.html, str) else out.with_suffix(".html")
        as_sample = args.banner == "sample" or (args.banner is None and args.sample)
        dest.write_text(to_html(text, sample_banner() if as_sample else client_banner(values)))
        print(f"wrote {dest} ({dest.stat().st_size / 1024:.0f} KB)")
    if args.outdir:
        samples = ([json.loads(l) for l in args.history.read_text().splitlines() if l.strip()]
                   if args.history else None)
        rows_for_csv = [json.loads(l) for l in args.log.read_text().splitlines() if l.strip()] if args.log else []
        rows_for_csv = [r for r in rows_for_csv if usable(r)]
        files = write_delivery(args.outdir, values, answers, text, rows_for_csv, samples,
                               meta["money"], meta["turns_year"], meta["cuts"], html=bool(args.html),
                               sample=(args.banner == "sample" or (args.banner is None and args.sample)))
        print(f"delivery folder {args.outdir}: {len(files)} file(s)")
        for name, what in files:
            print(f"  {name:22} {what[:70]}")
    if args.history:
        samples = [json.loads(l) for l in args.history.read_text().splitlines() if l.strip()]
        c = cache_stats(samples)
        dest = args.cache_out or out.with_name("cache-report.md")
        dest.write_text(cache_report_markdown(c, answers))
        if args.cache_html:
            hdest = (Path(args.cache_html) if isinstance(args.cache_html, str)
                     else dest.with_suffix(".html"))
            as_sample = args.banner == "sample" or (args.banner is None and args.sample)
            hdest.write_text(to_html(cache_report_markdown(c, answers),
                                     cache_banner(answers) if as_sample else client_cache_banner(answers)))
            print(f"wrote {hdest} ({hdest.stat().st_size / 1024:.0f} KB)")
        rate = "n/a" if c["hit_rate"] is None else f"{c['hit_rate'] * 100:.0f}%"
        print(f"wrote {dest} ({dest.stat().st_size / 1024:.1f} KB) — cache-hit rate {rate}")
        print(f"  verdict: {c['verdict']}")
    for n in notes:
        print("note:", n)


if __name__ == "__main__":
    main()
