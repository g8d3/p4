#!/usr/bin/env python3
"""Compute weekly RSI-14 + RSI<30 history + forward returns -> site/data.json."""
import json, os, time, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
needs = json.load(open(os.path.join(ROOT, "needs.json")))
P = needs["rsi_period"]

def closes(raw):
    r = raw["chart"]["result"][0]
    ts = r["timestamp"]
    q = r["indicators"]["quote"][0]
    out = []
    for i, t in enumerate(ts):
        c = q["close"][i]
        if c is None:
            continue
        out.append((t, c))
    return out, r.get("meta", {})

def rsi(series, period=14):
    # Wilder's RSI on closes
    if len(series) < period + 1:
        return [None] * len(series)
    gains, losses = [], []
    for i in range(1, len(series)):
        d = series[i][1] - series[i-1][1]
        gains.append(max(d, 0)); losses.append(max(-d, 0))
    avg_g = sum(gains[:period]) / period
    avg_l = sum(losses[:period]) / period
    out = [None] * period
    out.append(100 - 100/(1 + (avg_g/avg_l if avg_l else 100)))
    for i in range(period, len(gains)):
        avg_g = (avg_g*(period-1) + gains[i]) / period
        avg_l = (avg_l*(period-1) + losses[i]) / period
        rs = avg_g/avg_l if avg_l else 100
        out.append(100 - 100/(1+rs))
    return out  # aligned to series

tickers = {}
for t in needs["tickers"]:
    try:
        wraw = json.load(open(os.path.join(ROOT, "data", "raw", f"{t}_1wk.json")))
        draw = json.load(open(os.path.join(ROOT, "data", "raw", f"{t}_1d.json")))
    except FileNotFoundError as e:
        tickers[t] = {"error": f"missing raw: {e}"}
        continue
    try:
        w, wmeta = closes(wraw)
        d, dmeta = closes(draw)
        wcloses = w
        r = rsi(wcloses, P)
        last_rsi = round(r[-1], 1) if r[-1] is not None else None
        price = round(wcloses[-1][1], 2)
        price_ts = wcloses[-1][0]
        # daily red-day flag
        red = None; day_chg = None
        if len(d) >= 2:
            day_chg = round(100*(d[-1][1]-d[-2][1])/d[-2][1], 2)
            red = d[-1][1] < d[-2][1]
        # 52w high/low from daily
        hi = round(max(c for _, c in d), 2); lo = round(min(c for _, c in d), 2)
        pos52 = round(100*(price-lo)/(hi-lo), 1) if hi != lo else None
        # RSI<30 events + forward returns (26w ~= 6mo, 52w ~= 12mo)
        events = []
        wc = [c for _, c in wcloses]
        for i in range(len(wcloses)):
            if r[i] is not None and r[i] < needs["rsi_trigger"]:
                # only first week of a cluster (prev week >= 30)
                if i > 0 and r[i-1] is not None and r[i-1] < needs["rsi_trigger"]:
                    continue
                dt = datetime.datetime.fromtimestamp(wcloses[i][0], datetime.timezone.utc).strftime("%Y-%m-%d")
                fwd6 = round(100*(wc[i+26]-wc[i])/wc[i], 1) if i+26 < len(wc) else None
                fwd12 = round(100*(wc[i+52]-wc[i])/wc[i], 1) if i+52 < len(wc) else None
                events.append({"date": dt, "rsi": round(r[i],1), "price": round(wc[i],2),
                               "fwd6m_pct": fwd6, "fwd12m_pct": fwd12})
        events = events[-8:]
        # verdict
        if last_rsi is None:
            verdict = "NO DATA"
        elif last_rsi < needs["rsi_trigger"]:
            verdict = "TRIGGER — RSI<30"
        elif last_rsi < needs["rsi_watch"]:
            verdict = "WATCH — approaching"
        else:
            verdict = "WAIT"
        tickers[t] = {
            "price": price, "price_date": datetime.datetime.fromtimestamp(price_ts, datetime.timezone.utc).strftime("%Y-%m-%d"),
            "weekly_rsi": last_rsi, "verdict": verdict,
            "red_day": red, "day_chg_pct": day_chg,
            "hi_52w": hi, "lo_52w": lo, "pos_52w_pct": pos52,
            "weeks": len(wcloses), "rsi30_events": events,
        }
    except Exception as e:
        tickers[t] = {"error": str(e)}

payload = {
    "generated_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    "source": needs["source"],
    "rsi_period": P, "rsi_trigger": needs["rsi_trigger"],
    "note": "Forward returns are the underlying ETF/stock, NOT LEAPS option P&L. LEAPS amplify moves (delta ~0.6-0.8 + leverage) but also decay and can expire worthless. Proxy only.",
    "tickers": tickers,
}
os.makedirs(os.path.join(ROOT, "site"), exist_ok=True)
json.dump(payload, open(os.path.join(ROOT, "site", "data.json"), "w"), indent=2)
print(json.dumps({k: {kk: v[kk] for kk in ("price","weekly_rsi","verdict") if kk in v} for k,v in tickers.items()}, indent=2))
