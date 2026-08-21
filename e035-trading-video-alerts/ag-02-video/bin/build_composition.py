#!/usr/bin/env python3
"""Generate the alert-short HyperFrames composition from ag-01's setup.json.

Reads  ../ag-01-setup/output/setup.json
Writes ../alert-short/index.html   (standalone composition, 1080x1920, 34s, silent)

Deterministic by construction: static DOM + one paused GSAP timeline,
no clocks, no randomness, no network at render time.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SETUP_JSON = HERE.parent.parent / "ag-01-setup" / "output" / "setup.json"
OUT_HTML = HERE.parent / "alert-short" / "index.html"

W, H = 1080, 1920
DUR = 34.0
CHART = {"x": 60, "w": 960, "y": 470, "h": 850}
MAX_LEVELS = 4


def fmt_px(p):
    if p >= 1000:
        return f"{p:,.0f}"
    if p >= 10:
        return f"{p:,.2f}"
    return f"{p:.3f}"


def build_candles(candles, lo, hi):
    n = len(candles)
    slot = CHART["w"] / n
    bw = max(4.0, slot * 0.62)

    def y(p):
        return CHART["y"] + (hi - p) / (hi - lo) * CHART["h"]

    rows = []
    for i, c in enumerate(candles):
        cx = CHART["x"] + i * slot + (slot - bw) / 2
        yh, yl = y(c["h"]), y(c["l"])
        yo, yc = y(c["o"]), y(c["c"])
        top, bot = min(yo, yc), max(yo, yc)
        cls = "up" if c["c"] >= c["o"] else "down"
        rows.append(
            f'<div class="candle {cls}" style="left:{cx:.1f}px;top:{yh:.1f}px;'
            f'width:{bw:.1f}px;height:{max(2.0, yl - yh):.1f}px;">'
            f'<div class="wick" style="left:{(bw - 2) / 2:.1f}px;height:{max(2.0, yl - yh):.1f}px;"></div>'
            f'<div class="body" style="top:{top - yh:.1f}px;height:{max(2.0, bot - top):.1f}px;"></div>'
            f"</div>"
        )
    return "\n        ".join(rows)


def build_levels(levels, price, target):
    rows = []
    for lv in levels:
        px = lv["px"]
        frac = (px - CHART["y"]) / CHART["h"]
        ypos = CHART["y"] + (1 - frac) * CHART["h"]  # placeholder replaced below
        rows.append((px, lv))
    return rows


def main():
    d = json.loads(SETUP_JSON.read_text())
    coin = d["coin"]
    price = float(d["price"])
    chg = float(d["change_24h_pct"])
    level = float(d["level"])
    dist = float(d["distance_pct"])
    touches = int(d.get("touches", 0))
    atr = float(d.get("atr_pct", 0))
    forced = bool(d.get("forced"))
    is_support = d["setup"] == "support_test"

    candles = d["candles"]
    levels_all = d.get("levels_all", [])
    tgt = {"px": level}
    near = sorted(levels_all, key=lambda l: abs(l["px"] - price))[:MAX_LEVELS]
    if not any(abs(l["px"] - level) < 1e-9 for l in near):
        near = ([tgt] + near)[:MAX_LEVELS]
    if not any(abs(l["px"] - level) < 1e-9 for l in near):
        near.append(tgt)

    lows = [c["l"] for c in candles] + [l["px"] for l in near]
    highs = [c["h"] for c in candles] + [l["px"] for l in near]
    span = max(highs) - min(lows)
    lo, hi = min(lows) - span * 0.04, max(highs) + span * 0.04

    def y(p):
        return CHART["y"] + (hi - p) / (hi - lo) * CHART["h"]

    slot = CHART["w"] / len(candles)
    bw = max(4.0, slot * 0.62)
    candle_divs = []
    for i, c in enumerate(candles):
        cx = i * slot + (slot - bw) / 2
        yh, yl = y(c["h"]) - CHART["y"], y(c["l"]) - CHART["y"]
        yo, yc = y(c["o"]) - CHART["y"], y(c["c"]) - CHART["y"]
        top, bot = min(yo, yc), max(yo, yc)
        cls = "up" if c["c"] >= c["o"] else "down"
        candle_divs.append(
            f'<div class="candle {cls}" style="left:{cx:.1f}px;top:{yh:.1f}px;'
            f'width:{bw:.1f}px;height:{max(2.0, yl - yh):.1f}px;">'
            f'<div class="wick" style="left:{(bw - 2) / 2:.1f}px;width:2px;height:100%;"></div>'
            f'<div class="body" style="top:{top - yh:.1f}px;height:{max(2.0, bot - top):.1f}px;"></div>'
            f"</div>"
        )
    candles_html = "\n        ".join(candle_divs)

    level_rows = []
    for i, l in enumerate(near):
        is_tgt = abs(l["px"] - level) < 1e-9
        ly2 = y(l["px"]) - CHART["y"]
        cls = "level target" if is_tgt else "level"
        col = "cyan" if (is_tgt and is_support) or (not is_tgt and l["px"] < price) else "amber"
        level_rows.append(
            f'<div id="lv-{i}" class="{cls} {col}" style="top:{ly2:.1f}px;"></div>'
        )
    levels_html = "\n        ".join(level_rows)

    # resolve label collisions: keep >= 40px vertical separation
    order = sorted(range(len(near)), key=lambda i: y(near[i]["px"]))
    last_y = -1e9
    for i in order:
        ly_i = y(near[i]["px"]) - 34
        if ly_i - last_y < 40:
            ly_i = last_y + 40
        near[i]["_ly"] = ly_i
        last_y = ly_i

    price_labels = []
    for i, l in enumerate(near):
        is_tgt = abs(l["px"] - level) < 1e-9
        col = "cyan" if (is_tgt and is_support) or (not is_tgt and l["px"] < price) else "amber"
        price_labels.append(
            f'<div id="lvx-{i}" class="lv-label {col}{" tgt-lb" if is_tgt else ""}" '
            f'style="top:{l["_ly"]:.1f}px;">{fmt_px(l["px"])}</div>'
        )
    labels_html = "\n        ".join(price_labels)

    py = y(price)
    ly = y(level)
    brk_top, brk_h = (py, ly - py) if is_support else (ly, py - ly)
    dir_word = "ABOVE" if is_support else "BELOW"
    arrow = "&#9650;" if chg >= 0 else "&#9660;"
    chg_cls = "chip-up" if chg >= 0 else "chip-dn"
    setup_name = "SUPPORT TEST" if is_support else "RESISTANCE TEST"
    accent = "#22d3ee" if is_support else "#f59e0b"
    scen_a = ("BUYERS DEFEND", "Level holds as floor; bounces stay buyable." if is_support
              else "Level holds as ceiling; rejections extend.")
    scen_b = ("LEVEL FLIPS", f"A close beyond {fmt_px(level)} flips it to "
              f"{'resistance' if is_support else 'support'}.")
    drill = " &middot; DRILL (no live trigger)" if forced else ""

    html = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <title>{coin} {setup_name}</title>
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: {W}px; height: {H}px; overflow: hidden; background: #05070b; }}
      body {{ font-family: Inter, system-ui, sans-serif; color: #e6edf3; }}
      .mono {{ font-family: "JetBrains Mono", ui-monospace, Menlo, monospace; }}
      #root {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; }}
      .clip {{ position: absolute; }}

      /* background */
      #bg-fill {{ position: absolute; inset: 0;
        background: radial-gradient(900px 600px at 50% 18%, #101823 0%, #0a0e14 55%, #05070b 100%); }}
      #bg-grid {{ position: absolute; inset: 0; opacity: .5;
        background-image: linear-gradient(rgba(148,163,184,.05) 1px, transparent 1px),
          linear-gradient(90deg, rgba(148,163,184,.05) 1px, transparent 1px);
        background-size: 90px 90px; }}

      /* header */
      #header {{ left: 0; top: 96px; width: {W}px; padding: 0 64px; }}
      #coin-row {{ display: flex; align-items: center; gap: 20px; }}
      #coin-badge {{ font-size: 44px; font-weight: 800; letter-spacing: 2px; }}
      #tf-chip {{ font-size: 26px; font-weight: 700; color: #8b98a5;
        border: 2px solid rgba(139,152,165,.35); border-radius: 12px; padding: 4px 16px; }}
      #src-chip {{ margin-left: auto; font-size: 24px; color: #8b98a5; font-weight: 600; }}
      #price-row {{ display: flex; align-items: baseline; gap: 28px; margin-top: 18px; }}
      #price {{ font-size: 128px; font-weight: 800; letter-spacing: -2px; }}
      #chg {{ font-size: 40px; font-weight: 800; border-radius: 14px; padding: 6px 20px; }}
      .chip-up {{ color: #4ade80; background: rgba(34,197,94,.12); }}
      .chip-dn {{ color: #f87171; background: rgba(239,68,68,.12); }}
      #setup-pill {{ display: inline-block; margin-top: 26px; font-size: 34px; font-weight: 800;
        letter-spacing: 3px; color: #05070b; background: {accent};
        border-radius: 14px; padding: 12px 28px; }}

      /* chart */
      #chart-wrap {{ left: 0; top: 0; width: {W}px; height: {H}px; }}
      #chart-panel {{ position: absolute; left: {CHART['x'] - 20}px; top: {CHART['y'] - 56}px;
        width: {CHART['w'] + 40}px; height: {CHART['h'] + 110}px;
        background: rgba(255,255,255,.02); border: 1px solid rgba(255,255,255,.07);
        border-radius: 24px; }}
      #chart {{ position: absolute; left: {CHART['x']}px; top: {CHART['y']}px;
        width: {CHART['w']}px; height: {CHART['h']}px; }}
      .candle {{ position: absolute; }}
      .candle .wick {{ position: absolute; top: 0; background: inherit; }}
      .candle .body {{ position: absolute; left: 0; width: 100%; border-radius: 2px; }}
      .candle.up {{ background: #26a69a; }} .candle.up .body {{ background: #26a69a; }}
      .candle.down {{ background: #ef5350; }} .candle.down .body {{ background: #ef5350; }}
      .level {{ position: absolute; left: 0; width: 100%; height: 3px; border-radius: 2px; }}
      .level.cyan {{ background: #22d3ee; box-shadow: 0 0 18px rgba(34,211,238,.55); }}
      .level.amber {{ background: #f59e0b; box-shadow: 0 0 14px rgba(245,158,11,.4); }}
      .lv-label {{ position: absolute; right: 8px; font-size: 27px; font-weight: 800; }}
      .lv-label.cyan {{ color: #22d3ee; }} .lv-label.amber {{ color: #f59e0b; }}
      #price-dot {{ position: absolute; width: 22px; height: 22px; border-radius: 50%;
        background: #fff; box-shadow: 0 0 16px rgba(255,255,255,.8); }}
      #bracket {{ position: absolute; width: 0; border-left: 4px dashed {accent}; opacity: .9; }}
      #dist-chip {{ position: absolute; font-size: 30px; font-weight: 800; color: #05070b;
        background: {accent}; border-radius: 12px; padding: 8px 18px; white-space: nowrap; }}

      /* callout */
      #callout {{ left: 64px; top: 1430px; width: {W - 128}px; }}
      #callout-card {{ background: rgba(255,255,255,.04); border: 1px solid rgba(255,255,255,.09);
        border-left: 8px solid {accent}; border-radius: 20px; padding: 30px 36px; }}
      #callout-h {{ font-size: 40px; font-weight: 800; line-height: 1.25; }}
      #callout-sub {{ margin-top: 12px; font-size: 28px; color: #8b98a5; line-height: 1.35; }}

      /* scenarios */
      #scenarios {{ left: 64px; top: 1660px; width: {W - 128}px; display: flex; gap: 24px; }}
      .scen {{ flex: 1; border-radius: 18px; padding: 24px 26px;
        background: rgba(255,255,255,.03); border: 1px solid rgba(255,255,255,.08); }}
      .scen h3 {{ font-size: 27px; font-weight: 800; letter-spacing: 1px; }}
      .scen p {{ margin-top: 8px; font-size: 23px; color: #9aa7b4; line-height: 1.3; }}
      #scen-a h3 {{ color: #4ade80; }} #scen-b h3 {{ color: #f87171; }}

      /* outro */
      #outro-veil {{ position: absolute; inset: 0; background: rgba(5,7,11,.88); }}
      #outro-inner {{ position: absolute; left: 0; top: 0; width: {W}px; height: {H}px;
        display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 34px; }}
      #outro-big {{ font-size: 84px; font-weight: 800; letter-spacing: 2px; text-align: center; }}
      #outro-sub {{ font-size: 42px; font-weight: 700; color: {accent}; }}
      #outro-fine {{ font-size: 26px; color: #8b98a5; text-align: center; line-height: 1.5; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0"
         data-width="{W}" data-height="{H}" data-duration="{DUR:g}">

      <div id="bg" class="clip" data-start="0" data-duration="{DUR:g}" data-track-index="0">
        <div id="bg-fill"></div>
        <div id="bg-grid"></div>
      </div>

      <div id="stage">
        <div id="header" class="clip" data-start="0" data-duration="{DUR:g}" data-track-index="1">
          <div id="coin-row">
            <span id="coin-badge">{coin}<span style="color:#8b98a5">-USDT</span></span>
            <span id="tf-chip" class="mono">{d['tf'].upper()}</span>
            <span id="src-chip">Hyperliquid</span>
          </div>
          <div id="price-row">
            <span id="price" class="mono">${fmt_px(price)}</span>
            <span id="chg" class="mono {chg_cls}">{arrow} {chg:+.2f}% 24h</span>
          </div>
          <span id="setup-pill">{setup_name}</span>
        </div>

        <div id="chart-wrap" class="clip" data-start="3.5" data-duration="{DUR - 3.5:g}" data-track-index="2">
          <div id="chart-panel"></div>
          <div id="chart">
        {candles_html}
        {levels_html}
            <div id="price-dot" style="left:{CHART['w'] - 14}px;top:{py - CHART['y'] - 11:.1f}px;"></div>
            <div id="bracket" style="left:{CHART['w'] - 6}px;top:{brk_top - CHART['y']:.1f}px;height:{max(2.0, brk_h):.1f}px;"></div>
            <div id="dist-chip" style="right:70px;top:{(py + ly) / 2 - CHART['y'] - 24:.1f}px;">{dist:.2f}% {dir_word}</div>
          </div>
        {labels_html}
        </div>

        <div id="callout" class="clip" data-start="13.5" data-duration="{DUR - 13.5:g}" data-track-index="3">
          <div id="callout-card">
            <div id="callout-h">{coin} is testing {setup_name.lower().replace('test', 'at')} ${fmt_px(level)}</div>
            <div id="callout-sub">Last {len(candles)}&times;{d['tf']} candles &middot; level touched {touches}&times;
              &middot; ATR {atr:.2f}%/bar &middot; fractal pivots, 14&nbsp;days</div>
          </div>
        </div>

        <div id="scenarios" class="clip" data-start="24" data-duration="{DUR - 24:g}" data-track-index="4">
          <div id="scen-a" class="scen"><h3>{scen_a[0]}</h3><p>{scen_a[1]}</p></div>
          <div id="scen-b" class="scen"><h3>{scen_b[0]}</h3><p>{scen_b[1]}</p></div>
        </div>
      </div>

      <div id="outro" class="clip" data-start="29.5" data-duration="{DUR - 29.5:g}" data-track-index="5">
        <div id="outro-veil"></div>
        <div id="outro-inner">
          <div id="outro-big">WATCH<br>THE LEVEL</div>
          <div id="outro-sub" class="mono">{coin} {('support' if is_support else 'resistance')} ${fmt_px(level)}</div>
          <div id="outro-fine">Hyperliquid &middot; {d['tf']} candles &middot; generated {d['generated_at'][:10]}{drill}<br>
            Level-proximity alert, not a trade signal &middot; not financial advice</div>
        </div>
      </div>
    </div>

    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
      const E = "power3.out";

      // header
      tl.from("#coin-badge", {{ y: -40, autoAlpha: 0, duration: 0.5, ease: E }}, 0.15);
      tl.from(["#tf-chip", "#src-chip"], {{ y: -30, autoAlpha: 0, duration: 0.45, ease: E, stagger: 0.08 }}, 0.3);
      tl.from("#price", {{ y: 36, autoAlpha: 0, duration: 0.55, ease: E }}, 0.55);
      tl.from("#chg", {{ scale: 0.6, autoAlpha: 0, duration: 0.45, ease: "back.out(2)" }}, 0.95);
      tl.from("#setup-pill", {{ y: 30, autoAlpha: 0, duration: 0.5, ease: E }}, 1.25);

      // chart build
      tl.from("#chart-panel", {{ autoAlpha: 0, duration: 0.4, ease: E }}, 3.7);
      tl.from(".candle", {{
        scaleY: 0, transformOrigin: "50% 100%", duration: 0.28, ease: "power2.out",
        stagger: {{ each: 0.055 }},
      }}, 4.1);
      tl.from(".level", {{ scaleX: 0, transformOrigin: "0% 50%", duration: 0.5, ease: E, stagger: 0.12 }}, 8.7);
      tl.from(".lv-label", {{ autoAlpha: 0, x: 24, duration: 0.4, ease: E, stagger: 0.1 }}, 9.3);
      tl.from("#price-dot", {{ scale: 0, autoAlpha: 0, duration: 0.4, ease: "back.out(2)" }}, 10.2);

      // focus
      tl.to(".level:not(.target)", {{ opacity: 0.18, duration: 0.5, ease: E }}, 13.8);
      tl.to(".lv-label:not(.tgt-lb)", {{ opacity: 0.18, duration: 0.5, ease: E }}, 13.8);
      tl.from("#callout-card", {{ y: 48, autoAlpha: 0, duration: 0.55, ease: E }}, 14.2);
      tl.from("#bracket", {{ scaleY: 0, transformOrigin: "50% 0%", duration: 0.6, ease: E }}, 15.4);
      tl.from("#dist-chip", {{ scale: 0.6, autoAlpha: 0, duration: 0.45, ease: "back.out(2)" }}, 16.1);
      tl.to(".level.target", {{ opacity: 0.55, duration: 0.45, yoyo: true, repeat: 3, ease: "sine.inOut" }}, 17.2);

      // scenarios
      tl.from("#scen-a", {{ x: -70, autoAlpha: 0, duration: 0.5, ease: E }}, 24.3);
      tl.from("#scen-b", {{ x: 70, autoAlpha: 0, duration: 0.5, ease: E }}, 24.9);

      // outro
      tl.to("#stage", {{ autoAlpha: 0, duration: 0.7, ease: E }}, 29.6);
      tl.from("#outro-veil", {{ autoAlpha: 0, duration: 0.6, ease: E }}, 29.6);
      tl.from("#outro-big", {{ y: 50, autoAlpha: 0, duration: 0.6, ease: E }}, 30.0);
      tl.from("#outro-sub", {{ y: 36, autoAlpha: 0, duration: 0.5, ease: E }}, 30.4);
      tl.from("#outro-fine", {{ autoAlpha: 0, duration: 0.5, ease: E }}, 30.8);

      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""
    OUT_HTML.write_text(html)
    print(f"wrote {OUT_HTML} ({len(html)} bytes) "
          f"coin={coin} setup={d['setup']} level={level} candles={len(candles)}")


if __name__ == "__main__":
    sys.exit(main())
