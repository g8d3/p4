#!/usr/bin/env python3
"""Event-driven relative-strength listener (paper only, never trades).

Replaces the 07:15 daily timer. Nothing runs on a clock of its own:
  FAST  Binance public websocket (SOL/USDT, BTC/USDT 1m klines). Each closed candle
        is an event. A new 5-minute bucket on the stream takes one DexScreener sample
        (volume + liquidity) per watched coin -> data/rs_series.csv (time series).
  SLOW  First stream event of a new Bogota day refreshes fundamentals
        (rs_fundamentals.refresh: DefiLlama + CoinGecko, cached).
  LAUNCH Every 5m bucket reads GeckoTerminal solana new_pools (pump-fun, pumpswap,
        launchlab...) into a capped watch set; graduates are flagged separately.
Rules:
  MARKET  SOL or BTC down >= RS_DROP_PCT from its 60-min high -> runs rstrength_scan.py
          and flags watched coins whose 1h price rose while SOL fell.
  COIN    liquidity change over 5m/30m/1h >= +RS_LIQ_PCT (LIQ_ADD) or <= -RS_LIQ_PCT
          (LIQ_DRAIN); 5m volume >= RS_VOL_X x prior-hour avg: + liq rising = STRONG,
          + liq draining = RUG_RISK.
  GRADUATED launchpad coin >= RS_GRAD_AGE_H old with liq >= RS_GRAD_LIQ and 1h volume
          >= RS_GRAD_VOL on its last 3 samples (low-trust bucket).
Each flag row holds volume/liquidity deltas, fundamentals score/trend, coin_type,
external_share, and a rank. Real projects with improving fundamentals outrank memes.
launchpad_meme flags go to data/rs_lowtrust_flags.csv. Cooldown per (coin, rule):
RS_COOLDOWN_MIN. Important flags call e100-openbot/bin/to_coco.sh (RS_DRY_RUN=1 prints).
Test: --simulate.
"""
import csv, json, os, re, subprocess, sys, time
from collections import deque
from datetime import datetime, timezone, timedelta

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))
import rstrength_scan as scan
import rs_fundamentals as fund

DATA = os.path.join(BASE, "data")
SERIES = os.path.join(DATA, "rs_series.csv")
FLAGS = os.path.join(DATA, "rs_event_flags.csv")
LOWT = os.path.join(DATA, "rs_lowtrust_flags.csv")
STATE = os.path.join(DATA, "rs_listener_state.json")
MINTS = os.path.join(DATA, "rs_mints.json")
LAUNCH = os.path.join(DATA, "rs_launch_watch.json")
TO_COCO = os.path.expanduser("~/code/p4/e100-openbot/bin/to_coco.sh")
BOG = timezone(timedelta(hours=-5))
E = os.environ.get
DROP_PCT = float(E("RS_DROP_PCT", 3)); LIQ_PCT = float(E("RS_LIQ_PCT", 20))
VOL_X = float(E("RS_VOL_X", 3)); COOLDOWN_MIN = float(E("RS_COOLDOWN_MIN", 180))
MIN_VOL5 = float(E("RS_MIN_VOL5", 5000))      # absolute 5m-volume floor (USD)
MIN_AVG5 = float(E("RS_MIN_AVG5", 500))       # floor for the prior-hour avg baseline
LIQ_TREND = float(E("RS_LIQ_TREND_PCT", 2))   # STRONG/RUG_RISK liquidity-trend threshold
GRAD_AGE_H = float(E("RS_GRAD_AGE_H", 24)); GRAD_LIQ = float(E("RS_GRAD_LIQ", 50000))
GRAD_VOL = float(E("RS_GRAD_VOL", 10000)); LAUNCH_CAP = int(E("RS_LAUNCH_CAP", 150))
LAUNCH_DEXES = {"pump-fun", "pumpswap", "raydium-launchlab", "letsbonk-fun", "meteora-dbc", "moonshot"}
WS = "wss://stream.binance.com:9443/stream?streams=solusdt@kline_1m/btcusdt@kline_1m"
SF = ["ts", "token", "price", "vol_m5", "vol_h1", "liq_usd"]
FF = ["ts", "kind", "bucket", "rank", "label", "token", "rule", "price", "price_chg_1h", "sol_chg_1h",
      "vol_m5", "vol_spike_x", "liq_usd", "liq_chg_5m", "liq_chg_30m", "liq_chg_1h",
      "coin_type", "fund_score", "fund_class", "rev_trend_7d", "rev_trend_30d",
      "has_real_revenue", "external_share", "business_class", "external_share_trend_7d"]
RULE_W = {"STRONG": 30, "UP_WHILE_SOL_DOWN": 25, "GRADUATED": 15, "LIQ_ADD": 10,
          "VOL_SPIKE": 5, "LIQ_DRAIN": 20, "RUG_RISK": 20}

# Stablecoins/pegged cash: their VOL_SPIKE/LIQ_ADD flags are routine noise, not a
# relative-strength event. RUG_RISK still bypasses this filter (a depeg/drain matters).
PEGADOS_EXACT = {"DAI", "FRAX", "GHO", "LUSD", "CRVUSD", "SUSD", "RLUSD", "USDB", "USD0", "USD1",
                 "USTB", "JAAA", "BUIDL", "USYC", "USDY", "PYUSD", "EURC", "EURS", "FDUSD", "TUSD",
                 "USDC", "USDT", "USDE", "USDG", "USDS", "USDP", "USDD"}
PEGADO_RE = re.compile(r"(USDC|USDT|USDE|USDG|USDY|USDS|USDP|USDD|PYUSD|EURC|EURS|FDUSD|TUSD|USD1|USD0)$")


def es_pegado(tok):
    """True for fiat-pegged/stable symbols, including wrappers like SYRUPUSDC/PSTUSDC
    and bridged forms like USDC.E/USDC-E (separator + E suffix stripped first)."""
    raw = str(tok or "").upper().split(":")[0].strip()
    raw = re.sub(r"[.\-_/\s]+E$", "", raw)
    t = re.sub(r"[^A-Z0-9]", "", raw)
    return t in PEGADOS_EXACT or bool(PEGADO_RE.search(t))


def log(m): scan.log("[listener] " + m)


def append(path, fields, row):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        if new: w.writeheader()
        w.writerow(row)


def jload(p, d):
    try: return json.load(open(p))
    except Exception: return d


def trim_hist(hist):
    """Last 13 samples per token, numbers only (what coin_rules reads)."""
    out = {}
    for tok, h in (hist or {}).items():
        if not isinstance(h, list): continue
        rows = []
        for s in h[-13:]:
            try:
                rows.append({"price": fnum(s.get("price")), "vol_m5": fnum(s.get("vol_m5")) or 0,
                             "vol_h1": fnum(s.get("vol_h1")) or 0, "liq_usd": fnum(s.get("liq_usd")) or 0})
            except (AttributeError, TypeError): continue
        if rows: out[str(tok)] = rows
    return out


def load_hist(state):
    """Sample history survives restarts (q79): without it every restart costs
    an hour of blindness (coin_rules needs 12 five-minute samples)."""
    try:
        return trim_hist((state or {}).get("hist") or {})
    except Exception:
        return {}


def notify(msg):
    if E("RS_DRY_RUN") == "1":
        print("DRY_RUN to_coco:", msg); return
    try: subprocess.run([TO_COCO, "rstrength-listener", msg[:900]], timeout=30)
    except Exception as e: log(f"to_coco failed {e}")


def pct(a, b):
    try: return round((float(b) / float(a) - 1) * 100, 2) if a and b is not None else None
    except (TypeError, ValueError, ZeroDivisionError): return None


def fnum(x):
    try: return float(x)
    except (TypeError, ValueError): return None


def coin_rules(hist):
    """hist: samples oldest..newest, 5 min apart -> (rules, deltas).
    Needs 12 samples (1h) before any rule fires: thin pairs need a real baseline."""
    cur, d = hist[-1], {}
    if len(hist) < 12:
        return [], d
    for name, n in (("5m", 1), ("30m", 6), ("1h", 12)):
        d["liq_chg_" + name] = pct(hist[-1 - n]["liq_usd"], cur["liq_usd"]) if len(hist) > n else None
    prev = [h["vol_m5"] for h in hist[-13:-1] if h.get("vol_m5") is not None]
    avg = sum(prev) / len(prev) if len(prev) >= 3 else None
    # Floor the baseline so near-zero prior windows cannot fake a x800 spike.
    avg = max(avg, MIN_AVG5) if avg is not None else None
    d["vol_spike_x"] = round(cur["vol_m5"] / avg, 2) if avg else None
    rules, liq = [], [v for v in (d["liq_chg_5m"], d["liq_chg_30m"], d["liq_chg_1h"]) if v is not None]
    if any(v >= LIQ_PCT for v in liq): rules.append("LIQ_ADD")
    if any(v <= -LIQ_PCT for v in liq): rules.append("LIQ_DRAIN")
    vol = fnum(cur.get("vol_m5")) or 0
    liq_now = fnum(cur.get("liq_usd")) or 0
    # Absolute volume floor: single tiny trades on thin pairs are not volume.
    if (d["vol_spike_x"] is not None and d["vol_spike_x"] >= VOL_X
            and vol >= max(MIN_VOL5, 0.005 * liq_now)):
        tr = d["liq_chg_30m"] if d["liq_chg_30m"] is not None else d["liq_chg_5m"]
        # STRONG/RUG_RISK need a real liquidity trend, not a bare sign.
        rules.append("STRONG" if tr is not None and tr >= LIQ_TREND
                     else ("RUG_RISK" if tr is not None and tr <= -LIQ_TREND else "VOL_SPIKE"))
    return rules, d


def drop_from_high(q):
    return round((q[-1][1] / max(c for _, c in q) - 1) * 100, 2) if len(q) >= 2 else None


def graduated(samples, age_h):
    last = samples[-3:]
    return (age_h >= GRAD_AGE_H and len(last) == 3 and
            all((s.get("liq_usd") or 0) >= GRAD_LIQ and (s.get("vol_h1") or 0) >= GRAD_VOL for s in last))


def label_rank(rule, f):
    """Rank: real project with improving fundamentals > project > unknown > meme."""
    ct, cls = f.get("coin_type"), f.get("klass")
    sc = fnum(f.get("score")) or 0
    if ct in ("revenue_project", "hybrid", "launchpad_platform_token") and cls == "PROJECT_IMPROVING":
        label, base = "real project, improving fundamentals", 100
    elif ct in ("revenue_project", "hybrid", "launchpad_platform_token"):
        label, base = "real project", 70
    elif ct in (None, "", "l1"):
        label, base = "unclassified", 40
    else:
        label, base = "pure memecoin volume", 10
    return label, round(base + sc / 10 + RULE_W.get(rule, 0), 1)


class Engine:
    def __init__(self):
        self.state = jload(STATE, {"cool": {}})
        self.px = {"SOLUSDT": deque(), "BTCUSDT": deque()}
        self.hist = load_hist(self.state)
        self.fund, self.mm = fund.latest(), {}
        self.launch = jload(LAUNCH, {})
        self.bucket = None; self.day = None

    def save(self):
        os.makedirs(DATA, exist_ok=True)
        self.state["hist"] = trim_hist(self.hist)
        json.dump(self.state, open(STATE, "w")); json.dump(self.launch, open(LAUNCH, "w"))

    def cooled(self, key, t):
        last = self.state["cool"].get(key)
        if last and t - last < COOLDOWN_MIN * 60: return False
        self.state["cool"][key] = t; return True

    def flag(self, t, kind, tok, rule, s, d, pc, solc, f=None):
        if rule != "RUG_RISK" and es_pegado(tok):
            log(f"SKIP pegado {tok} {rule}")
            return None
        f = f if f is not None else self.fund.get(tok, {})
        label, rank = label_rank(rule, f)
        lowt = (f.get("coin_type") == "launchpad_meme") or kind == "LAUNCH"
        row = {"ts": datetime.fromtimestamp(t, BOG).isoformat(timespec="seconds"), "kind": kind,
               "bucket": "low_trust" if lowt else "main", "rank": rank, "label": label,
               "token": tok, "rule": rule, "price": s.get("price"), "price_chg_1h": pc,
               "sol_chg_1h": solc, "vol_m5": s.get("vol_m5"), "vol_spike_x": d.get("vol_spike_x"),
               "liq_usd": s.get("liq_usd"), "liq_chg_5m": d.get("liq_chg_5m"),
               "liq_chg_30m": d.get("liq_chg_30m"), "liq_chg_1h": d.get("liq_chg_1h"),
               "coin_type": f.get("coin_type"), "fund_score": f.get("score"), "fund_class": f.get("klass"),
               "rev_trend_7d": f.get("rev_trend_7d"), "rev_trend_30d": f.get("rev_trend_30d"),
               "has_real_revenue": f.get("has_real_revenue"), "external_share": f.get("external_share"),
               "business_class": f.get("business_class"),
               "external_share_trend_7d": f.get("external_share_trend_7d")}
        append(LOWT if lowt else FLAGS, FF, row)
        log(f"FLAG {row['bucket']} {kind} {tok} {rule} rank={rank}")
        return row

    def report(self, head, rows):
        main = sorted([r for r in rows if r["bucket"] == "main" and r["rule"] != "LIQ_ADD"],
                      key=lambda r: -r["rank"])
        if not main and not head: return
        txt = "; ".join(f"{r['token']} {r['rule']} [{r['label']}] vol x{r['vol_spike_x']} liq 5m "
                        f"{r['liq_chg_5m']}% 30m {r['liq_chg_30m']}% 1h {r['liq_chg_1h']}% "
                        f"fund {r['fund_score']} ext_share {r['external_share'] if r['external_share'] not in (None, '') else 'n/a'}"
                        for r in main[:6])
        lt = sum(1 for r in rows if r["bucket"] == "low_trust")
        notify((head + " " if head else "") + "Paper only. " + (txt or "No main flags.") +
               (f" (+{lt} low-trust meme flags in data/rs_lowtrust_flags.csv)" if lt else ""))

    def handle_market(self, t, chg, sol_chg, coin_chg):
        hit = {k: v for k, v in chg.items() if v is not None and v <= -DROP_PCT}
        if not hit or not self.cooled("MARKET", t): return []
        rows = []
        for tok, c in coin_chg.items():
            if c is not None and c > 0 and sol_chg is not None and sol_chg < 0:
                h = self.hist.get(tok, [])
                d = coin_rules(h)[1] if h else {}
                row = self.flag(t, "MARKET", tok, "UP_WHILE_SOL_DOWN", h[-1] if h else {}, d, c, sol_chg)
                if row: rows.append(row)
        self.save()
        self.report("Market event: " + ", ".join(f"{k} {v}% from 1h high" for k, v in hit.items()) +
                    f". Up while SOL fell: {', '.join(r['token'] for r in rows) or 'none'}.", rows)
        return rows

    def handle_sample(self, t, sample):
        out = []
        for tok, s in sample.items():
            h = self.hist.setdefault(tok, []); h.append(s); del h[:-13]
            append(SERIES, SF, {"ts": datetime.fromtimestamp(t, BOG).isoformat(timespec="seconds"),
                                "token": tok, **{k: s.get(k) for k in SF[2:]}})
            rules, d = coin_rules(h)
            for r in rules:
                if self.cooled(f"{tok}:{r}", t):
                    pc = pct(h[0]["price"], s["price"]) if len(h) >= 13 else None
                    row = self.flag(t, "COIN", tok, r, s, d, pc, None)
                    if row: out.append(row)
        self.save()
        if any(r["rule"] in ("STRONG", "RUG_RISK", "LIQ_DRAIN") and r["bucket"] == "main" for r in out):
            self.report("Coin flags:", out)
        return out

    def handle_launch(self, t, new_pools, samples):
        """new_pools: [(mint, symbol, dex, created_ts)]; samples: {mint: sample}."""
        for mint, sym, dex, ct in new_pools:
            if dex in LAUNCH_DEXES and mint not in self.launch:
                self.launch[mint] = {"sym": sym, "dex": dex, "created": ct, "s": [], "grad": False}
        if len(self.launch) > LAUNCH_CAP:  # drop oldest non-graduated
            for k in sorted(self.launch, key=lambda k: self.launch[k]["created"])[:len(self.launch) - LAUNCH_CAP]:
                if not self.launch[k]["grad"]: self.launch.pop(k)
        out = []
        for mint, s in samples.items():
            L = self.launch.get(mint)
            if not L: continue
            L["s"] = (L["s"] + [s])[-6:]
            if not L["grad"] and graduated(L["s"], (t - L["created"]) / 3600):
                L["grad"] = True
                f = {"coin_type": "launchpad_meme"}
                row = self.flag(t, "LAUNCH", f"{L['sym']}:{mint[:6]}", "GRADUATED", s, {}, None, None, f)
                if row: out.append(row)
        self.save()
        if out:
            notify(f"Launchpad graduates (low-trust, paper only): " +
                   ", ".join(f"{r['token']} liq ${r['liq_usd']:.0f}" for r in out))
        return out

    # ----- live glue -----
    def on_kline(self, sym, t, close):
        q = self.px[sym]; q.append((t, close))
        while q and t - q[0][0] > 3600: q.popleft()
        day = datetime.fromtimestamp(t, BOG).strftime("%Y-%m-%d")
        if day != self.day:
            self.day = day
            try: self.fund = fund.refresh(dict(scan.WATCHLIST))
            except Exception as e: log(f"fundamentals refresh failed {e.__class__.__name__}")
        chg = {"SOL": drop_from_high(self.px["SOLUSDT"]), "BTC": drop_from_high(self.px["BTCUSDT"])}
        if any(v is not None and v <= -DROP_PCT for v in chg.values()) and \
                t - self.state["cool"].get("MARKET", 0) >= COOLDOWN_MIN * 60:
            subprocess.run([sys.executable, os.path.join(BASE, "scripts", "rstrength_scan.py")], timeout=900)
            coins = {}
            try:
                for c in scan.get_json("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd"
                                       "&price_change_percentage=1h&per_page=250&ids=" + ",".join(scan.WATCHLIST.values())):
                    coins[(c.get("symbol") or "").upper()] = c.get("price_change_percentage_1h_in_currency")
            except Exception as e: log(f"coingecko 1h error {e}")
            sol1h = coins.pop("SOL", None)
            self.handle_market(t, chg, sol1h if sol1h is not None else chg["SOL"], coins)
        b = int(t // 300)
        if sym == "SOLUSDT" and b != self.bucket:
            self.bucket = b
            self.handle_sample(t, dex_sample(self.mm))
            try: self.handle_launch(t, gt_new_pools(), dex_sample({m: m for m in self.launch}))
            except Exception as e: log(f"launch step failed {e.__class__.__name__}")


def mints():
    if os.path.exists(MINTS): return json.load(open(MINTS))
    ids = set(scan.WATCHLIST.values())
    ids |= {c["id"] for c in scan.markets(category="solana-ecosystem")[:scan.SOLANA_TOP_N]}
    out = {}
    for c in scan.get_json("https://api.coingecko.com/api/v3/coins/list?include_platform=true"):
        m = (c.get("platforms") or {}).get("solana")
        if c["id"] in ids and m: out[c["symbol"].upper()] = m
    json.dump(out, open(MINTS, "w"), indent=1)
    return out


def dex_sample(mm):
    """DexScreener (free, 300 req/min): sums liquidity/volume over each token's pairs."""
    out, items = {}, list(mm.items())
    for i in range(0, len(items), 30):
        chunk = items[i:i + 30]; bym = {m: s for s, m in chunk}
        try: pairs = scan.get_json("https://api.dexscreener.com/tokens/v1/solana/" + ",".join(m for _, m in chunk), tries=2) or []
        except Exception as e: log(f"dexscreener error {e.__class__.__name__}"); continue
        for p in pairs:
            s = bym.get((p.get("baseToken") or {}).get("address"))
            if not s: continue
            liq = (p.get("liquidity") or {}).get("usd") or 0; v = p.get("volume") or {}
            o = out.setdefault(s, {"liq_usd": 0, "vol_m5": 0, "vol_h1": 0, "price": None, "_b": -1})
            o["liq_usd"] += liq; o["vol_m5"] += v.get("m5") or 0; o["vol_h1"] += v.get("h1") or 0
            if liq > o["_b"]: o["_b"] = liq; o["price"] = fnum(p.get("priceUsd"))
        time.sleep(0.3)
    for o in out.values(): o.pop("_b")
    return out


def gt_new_pools():
    """GeckoTerminal solana new_pools (free, ~30 req/min); one call per 5m bucket."""
    d = scan.get_json("https://api.geckoterminal.com/api/v2/networks/solana/new_pools?include=base_token,dex", tries=2)
    out = []
    for p in d.get("data", []):
        rel = p.get("relationships", {})
        mint = rel.get("base_token", {}).get("data", {}).get("id", "").replace("solana_", "")
        dex = rel.get("dex", {}).get("data", {}).get("id")
        ca = p.get("attributes", {}).get("pool_created_at")
        name = (p.get("attributes", {}).get("name") or "?").split(" / ")[0]
        if mint and ca:
            out.append((mint, name, dex, datetime.fromisoformat(ca.replace("Z", "+00:00")).timestamp()))
    return out


def live():
    import websocket
    eng = Engine(); eng.mm = mints()
    log(f"listening; {len(eng.mm)} coins; drop {DROP_PCT}% liq {LIQ_PCT}% vol x{VOL_X} cooldown {COOLDOWN_MIN}m")
    while True:
        try:
            ws = websocket.create_connection(WS, timeout=90)
            while True:
                k = json.loads(ws.recv())["data"]["k"]
                if k["x"]: eng.on_kline(k["s"], k["T"] / 1000, float(k["c"]))
        except Exception as e:
            log(f"ws error {e.__class__.__name__}: {e}; reconnect in 15s"); time.sleep(15)


def simulate():
    import tempfile
    global DATA, SERIES, FLAGS, LOWT, STATE, LAUNCH
    DATA = tempfile.mkdtemp()
    SERIES, FLAGS, LOWT, STATE, LAUNCH = (DATA + x for x in ("/s.csv", "/f.csv", "/l.csv", "/st.json", "/lw.json"))
    os.environ["RS_DRY_RUN"] = "1"
    eng = Engine()
    eng.fund = {"GOOD": {"coin_type": "revenue_project", "klass": "PROJECT_IMPROVING", "score": "80",
                         "external_share": "0.9", "business_class": "real_business"},
                "RUG": {"coin_type": "revenue_project", "klass": "PROJECT", "score": "50"},
                "MEME": {"coin_type": "launchpad_meme", "klass": "MEME", "score": "10"}}
    t0 = 1_800_000_000
    for i in range(13):
        last = i == 12
        eng.handle_sample(t0 + i * 300, {
            "GOOD": {"price": 1.1 if last else 1, "vol_m5": 5000 if last else 1000, "vol_h1": 0, "liq_usd": 130000 if last else 100000},
            "RUG": {"price": 1, "vol_m5": 8000 if last else 1000, "vol_h1": 0, "liq_usd": 50000 if last else 100000},
            "MEME": {"price": 1, "vol_m5": 9000 if last else 1000, "vol_h1": 0, "liq_usd": 140000 if last else 100000},
            "FLAT": {"price": 1, "vol_m5": 1000, "vol_h1": 0, "liq_usd": 100000},
            # thin-pair single trade: huge multiplier on near-zero volume, liq flat (ORCA/MET case)
            "TINY": {"price": 1, "vol_m5": 440.28 if last else 0.28, "vol_h1": 0, "liq_usd": 58000 if last else 58000.04}})
    tl = t0 + 3600
    r1 = eng.handle_market(tl, {"SOL": -4.2, "BTC": -1.0}, -4.2, {"GOOD": 2.5, "FLAT": -3.0})
    r2 = eng.handle_market(tl + 600, {"SOL": -5.0, "BTC": -1.0}, -5.0, {"GOOD": 2.5})
    gs = {"liq_usd": 80000, "vol_h1": 20000, "vol_m5": 2000, "price": 0.01}
    eng.handle_launch(tl, [("MintGrad1111", "GRAD", "pump-fun", tl - 30 * 3600),
                           ("MintDead1111", "DEAD", "pump-fun", tl - 30 * 3600),
                           ("MintOther111", "OTH", "orca", tl)], {})
    g = []
    for k in range(3):
        g += eng.handle_launch(tl + k * 300, [], {"MintGrad1111": gs, "MintDead1111": {**gs, "liq_usd": 3000}})
    main = list(csv.DictReader(open(FLAGS))); low = list(csv.DictReader(open(LOWT)))
    got = {(r["token"], r["rule"]) for r in main}
    rk = {(r["token"], r["rule"]): float(r["rank"]) for r in main + low}
    checks = {
        "STRONG on GOOD (vol spike + liq up)": ("GOOD", "STRONG") in got,
        "RUG_RISK on RUG (vol spike + liq drain)": ("RUG", "RUG_RISK") in got,
        "LIQ_DRAIN on RUG": ("RUG", "LIQ_DRAIN") in got,
        "FLAT never flagged": not any(r["token"] == "FLAT" for r in main + low),
        "TINY thin-pair trade never flagged (ORCA/MET case)": not any(r["token"] == "TINY" for r in main + low),
        "warm-up: no rules before 12 samples": coin_rules(
            [{"vol_m5": 9000, "liq_usd": 100000}] * 5) == ([], {}),
        "meme spike goes to low-trust bucket only": any(r["token"] == "MEME" and r["rule"] == "STRONG" for r in low)
            and not any(r["token"] == "MEME" for r in main),
        "real improving project outranks meme spike": rk[("GOOD", "STRONG")] > rk[("MEME", "STRONG")],
        "market event flags GOOD only": [r["token"] for r in r1] == ["GOOD"],
        "cooldown blocks 2nd market event": r2 == [],
        "SOL -3.5% from 1h high detected": drop_from_high(deque([(0, 100.0), (1800, 98.0), (3500, 96.5)])) <= -DROP_PCT,
        "graduation flagged once, low-trust": len(g) == 1 and g[0]["token"].startswith("GRAD") and g[0]["bucket"] == "low_trust",
        "non-launchpad pool ignored": "MintOther111" not in eng.launch,
        "deltas + fundamentals in every coin row": all(r["liq_chg_5m"] and r["coin_type"] for r in main if r["kind"] == "COIN"),
        "external_share carried in row": any(r["external_share"] == "0.9" for r in main),
    }
    for k, v in checks.items(): print(("PASS " if v else "FAIL ") + k)
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(simulate() if "--simulate" in sys.argv else live())
