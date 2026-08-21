# e035 — Trading Video Alerts

**Goal**: when a live Hyperliquid market approaches a support/resistance
level, auto-produce a vertical (9:16) chart-explainer short that explains the
setup in plain language — the missing link between the trading experiments
(e021/e022/e025) and the video stack (e023/e024/e029/e034).

## Inherits

- [../e000-fundamentals/AGENTS.md](../e000-fundamentals/AGENTS.md) — principles,
  command rules, GPU encoding (h264_vaapi), quiet hours
- [../e021-hyperliquid-playground/AGENTS.md](../e021-hyperliquid-playground/AGENTS.md) —
  Hyperliquid API conventions (candleSnapshot pitfalls)
- [../e022-nautilus-sr-grid/AGENTS.md](../e022-nautilus-sr-grid/AGENTS.md) —
  S/R detection method (fractal pivots + clustering)

## Pipeline

```
ag-01-setup                 ag-02-video
Hyperliquid REST  ──►  setup.json  ──►  HyperFrames 9:16  ──►  renders/alert.mp4
1h candles BTC/ETH/SOL     (the contract)   composition          (h264_vaapi)
fractal pivots + ATR                        driven by JSON
proximity detector
```

| Agent | Consumes | Produces |
|---|---|---|
| **ag-01-setup** | Hyperliquid public REST (`candleSnapshot`, `allMids`) | `output/setup.json` (or `output/no_setup.json`) |
| **ag-02-video** | `../ag-01-setup/output/setup.json` | `alert-short/` HyperFrames project, `alert-short/renders/alert.mp4` |

## Setup definition (v1, honest and simple)

A coin fires when its last 1h close is within `proximity_pct` (default 0.35%)
of a confirmed S/R level. Levels = fractal pivots (window 5) from the last
~14 days of 1h candles, clustered within 0.3%, keeping clusters touched ≥ 2
times. The strongest (nearest) setup across coins wins; ties broken by level
touch count. If nothing fires → `no_setup.json` (a valid result, not an
error). This is a *level-proximity* alert, NOT a trade signal — the video says
so explicitly.

## setup.json contract

```json
{
  "generated_at": "ISO-8601",
  "coin": "BTC",
  "price": 123456.7,
  "change_24h_pct": -1.2,
  "tf": "1h",
  "setup": "support_test" | "resistance_test",
  "level": 123000.0,
  "distance_pct": 0.21,
  "touches": 3,
  "levels_all": [ ... ],
  "candles": [{ "t": ms, "o": , "h": , "l": , "c": , "v":  }, ...]   // last 72
  "atr_pct": 0.8
}
```

## How to run

```bash
bin/run_pipeline.sh                # full pipeline: detect -> build -> check -> render -> vaapi encode
bin/run_pipeline.sh --force        # drill: nearest real level even if > 0.35% away (labeled DRILL in the video)
```

Individual steps:

```bash
python3 ag-01-setup/bin/detect_setup.py             # writes ag-01-setup/output/setup.json
python3 ag-02-video/bin/build_composition.py        # setup.json -> ag-02-video/alert-short/index.html
cd ag-02-video/alert-short && npm run check         # validate composition
npx hyperframes render -o renders/alert-raw.mp4     # render
e023-build-in-public/bin/encode_vaapi.sh renders/alert-raw.mp4 renders/alert.mp4
```

## Status

- ag-01: implemented, verified on live data (BTC/ETH/SOL 1h). `--force` drill mode added —
  on 2026-08-20 no coin was within 0.35% of a confirmed level (nearest were 12-18% away
  after a sharp drop), so honest runs currently end in `no_setup.json`.
- ag-02: generator + composition done. First render: 34s 1080x1920 silent MP4,
  `check` 0 errors / 0 warnings, h264_vaapi verified. Drill video for SOL support $88.05.
- Open: scheduled runs (cron/tmux loop) + phone push via notify.sh when a REAL setup fires;
  narration/captions pass; more coins beyond BTC/ETH/SOL.
