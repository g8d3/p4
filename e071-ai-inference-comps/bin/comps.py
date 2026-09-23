#!/usr/bin/env python3
"""e071 comps: pure math from data/ cache → output/comps.json/.csv + venues.json + unlocks.json.

Atomic numeric columns only. Prose lives in methodology strings, never in cells.
Sig-low: lowest daily close after ath_ts (>=7d before now) with >=20% drawdown
from ATH; else lowest post-ATH close with sig_low_weak=1 (majors via CG
market_chart; microcaps: weak proxy from available history or null).
"""
import json, os, time, csv
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "output")
os.makedirs(OUT, exist_ok=True)


def wout(path, payload, is_json=True):
    tmp = path + ".tmp"
    if is_json:
        json.dump(payload, open(tmp, "w"), indent=1)
    else:
        payload(tmp)
    os.replace(tmp, path)  # readers never see half files
UNI = json.load(open(os.path.join(ROOT, "universe.json")))["tokens"]

def load(p):
    fp = os.path.join(DATA, p)
    return json.load(open(fp)) if os.path.exists(fp) else None

def hist_of(sym):
    try:
        d = load(f"gt_ohlcv__{sym}.json")
        lst = d["data"]["attributes"]["ohlcv_list"]
        closes = sorted((int(ts), float(c)) for ts, o, h, l, c, v in lst if c)
        return closes
    except Exception:
        return []


def siglow_full(closes, now_ts):
    if len(closes) < 10:
        return None, None, None
    ath = max(c for _, c in closes)
    ath_ts = min(ts for ts, c in closes if c == ath)
    post = [(ts, c) for ts, c in closes if ts > ath_ts and ts <= now_ts - 7 * 86400]
    if not post:
        return None, None, None
    deep = [(ts, c) for ts, c in post if (ath - c) / ath >= 0.20]
    pool, weak = (deep, 0) if deep else (post, 1)
    ts, px = min(pool, key=lambda x: x[1])
    return px, ts, weak


def supply_total_of(sym, chain):
    try:
        t = load(f"gt_token__{sym}.json")
        ns = ((t or {}).get("data") or {}).get("attributes") or {}
        if ns.get("normalized_total_supply"):
            return float(ns["normalized_total_supply"])
    except Exception:
        pass
    try:
        r = load(f"rpc_supply__{sym}.json")
        if chain == "solana":
            return float(r["result"]["value"]["uiAmountString"])
        if chain == "base":
            tot = int(r["totalSupply"], 16)
            dec = int(r["decimals"], 16)
            return tot / (10 ** dec)
    except Exception:
        pass
    return None


def ep(s):
    try:
        if s is None: return None
        return int(datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp())
    except Exception:
        return None

def cg_socials(det):
    # CoinGecko /coins detail links -> (site, x, telegram, discord)
    L = (det.get("links") or {})
    hp = [u for u in (L.get("homepage") or []) if u]
    site = hp[0] if hp else None
    tw = L.get("twitter_screen_name")
    x = ("https://x.com/" + tw) if tw else None
    tg = L.get("telegram_channel_identifier")
    tg = ("https://t.me/" + tg) if tg else None
    chats = [u for u in (L.get("chat_url") or []) if u]
    dc = next((u for u in chats if "discord" in u), None)
    return site, x, tg, dc

def dex_socials(pairs):
    # DexScreener pair info -> (site, x, telegram, discord); first pair carrying info wins
    info = None
    for p in pairs or []:
        inf = p.get("info") or {}
        if inf.get("websites") or inf.get("socials"):
            info = inf; break
    if not info:
        return None, None, None, None
    webs = [w.get("url") for w in (info.get("websites") or []) if w.get("url")]
    site = webs[0] if webs else None
    sm = {}
    for s in (info.get("socials") or []):
        t = (s.get("type") or "").lower()
        if s.get("url") and t not in sm:
            sm[t] = s["url"]
    return site, sm.get("twitter"), sm.get("telegram"), sm.get("discord")

def genesis_ts(s):
    # curated "YYYY-MM-DD" in universe.json -> epoch UTC (majors age; CG genesis_date is null)
    try:
        if not s: return None
        return int(datetime.strptime(str(s)[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
    except Exception:
        return None

def pct(a, b):
    try:
        if a is None or b in (None, 0): return None
        return round((a - b) / abs(b) * 100, 2)
    except Exception:
        return None

def main():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    now_ts = int(datetime.now(timezone.utc).timestamp())
    mk = load("cg_markets.json") or []
    by_cg = {m["id"]: m for m in mk}
    sol_px = ((load("cg_sol.json") or {}).get("solana") or {}).get("usd")
    # pass 1: base quotes
    base = []
    for t in UNI:
        sym, ch = t["symbol"], t.get("chain")
        q = {"symbol": sym, "tier": t.get("tier"), "chain": ch,
             "source": None, "stale": 0, "through": None}
        if t.get("coingecko_id") and t["coingecko_id"] in by_cg:
            m = by_cg[t["coingecko_id"]]
            det = load(f"cg_coin__{t['coingecko_id']}.json") or {}
            md = (det.get("market_data") or {})
            site, xh, tgh, dch = cg_socials(det)
            q.update({
                "source": "coingecko", "price_usd": m.get("current_price"),
                "mcap_usd": m.get("market_cap"), "fdv_usd": m.get("fully_diluted_valuation"),
                "volume_24h_usd": m.get("total_volume"),
                "chg_1h_pct": m.get("price_change_percentage_1h_in_currency"),
                "chg_24h_pct": m.get("price_change_percentage_24h"),
                "chg_7d_pct": m.get("price_change_percentage_7d_in_currency"),
                "chg_30d_pct": m.get("price_change_percentage_30d_in_currency"),
                "ath_usd": m.get("ath"), "ath_ts": ep(m.get("ath_date")),
                "atl_usd": m.get("atl"), "atl_ts": ep(m.get("atl_date")),
                "supply_circ": m.get("circulating_supply"),
                "supply_total": md.get("total_supply"), "supply_max": m.get("max_supply"),
                "born_ts": genesis_ts(t.get("genesis_date")),
                "through": now[:10], "liquidity_usd": None, "txns_24h": None,
                "site_url": site, "x_url": xh, "tg_url": tgh, "discord_url": dch,
            })
        elif ch in ("solana", "base", "robinhood") and t.get("mint"):
            raw = load(f"dex__{sym}__{t['mint'].replace('/','_')}.json")
            pairs = raw if isinstance(raw, list) else []
            if pairs:
                vols = sum((p.get("volume") or {}).get("h24") or 0 for p in pairs)
                liq = sum((p.get("liquidity") or {}).get("usd") or 0 for p in pairs)
                tx = sum(sum((x or 0) for x in (p.get("txns") or {}).get("h24", {}).values()) for p in pairs)
                p0 = pairs[0]
                f0 = float(p0.get("priceUsd") or 0) or None
                borns = [int(p["pairCreatedAt"]) // 1000 for p in pairs if p.get("pairCreatedAt")]
                born_ts = min(borns) if borns else None
                site, xh, tgh, dch = dex_socials(pairs)
                closes = hist_of(sym)
                if closes:
                    h_ath = max(c for _, c in closes)
                    h_ath_ts = min(ts for ts, c in closes if c == h_ath)
                    h_atl = min(c for _, c in closes)
                    h_atl_ts = min(ts for ts, c in closes if c == h_atl)
                    h_hist = [c for _, c in closes[-30:]]
                    h_thru = datetime.fromtimestamp(closes[-1][0], timezone.utc).strftime("%Y-%m-%d")
                else:
                    h_ath = h_ath_ts = h_atl = h_atl_ts = None
                    h_hist, h_thru = [], now[:10]
                h_sup = supply_total_of(sym, ch)
                try:
                    _gt = load(f"gt_token__{sym}.json")
                    gtid = (((_gt or {}).get("data") or {}).get("attributes") or {}).get("coingecko_coin_id")
                except Exception:
                    gtid = None
                q.update({
                    "source": "dexscreener", "price_usd": f0,
                    "mcap_usd": p0.get("marketCap"), "fdv_usd": p0.get("fdv"),
                    "volume_24h_usd": vols or None, "liquidity_usd": liq or None,
                    "txns_24h": tx or None,
                    "chg_5m_pct": (p0.get("priceChange") or {}).get("m5"),
                    "chg_1h_pct": (p0.get("priceChange") or {}).get("h1"),
                    "chg_6h_pct": (p0.get("priceChange") or {}).get("h6"),
                    "chg_24h_pct": (p0.get("priceChange") or {}).get("h24"),
                    "ath_usd": h_ath, "ath_ts": h_ath_ts, "atl_usd": h_atl, "atl_ts": h_atl_ts,
                    "supply_circ": None, "supply_total": h_sup, "supply_max": None,
                    "through": h_thru, "born_ts": born_ts, "hist30": h_hist,
                    "site_url": site, "x_url": xh, "tg_url": tgh, "discord_url": dch,
                    "coingecko_gt": gtid,
                })
            else:
                q.update({"source": "dexscreener_empty", "stale": 1,
                          "price_usd": None, "mcap_usd": t.get("seed_mcap_usd"),
                          "fdv_usd": None, "volume_24h_usd": None, "born_ts": None,
                          "site_url": None, "x_url": None, "tg_url": None, "discord_url": None})
        else:
            q.update({"source": "tweet_seed", "stale": 1,
                      "price_usd": None, "mcap_usd": t.get("seed_mcap_usd"),
                      "fdv_usd": None, "volume_24h_usd": None,
                      "liquidity_usd": None, "txns_24h": None,
                      "ath_usd": None, "ath_ts": None, "atl_usd": None,
                      "atl_ts": None, "supply_circ": None,
                      "supply_total": None, "supply_max": None,
                      "through": "2026-09-21", "born_ts": None,
                      "site_url": None, "x_url": None, "tg_url": None, "discord_url": None})
        base.append(q)
    tot_mcap = sum((b.get("mcap_usd") or 0) for b in base) or 1
    tot_vol = sum((b.get("volume_24h_usd") or 0) for b in base) or 0
    tot_liq = sum((b.get("liquidity_usd") or 0) for b in base) or 0
    # pass 2: derived multiples (all numeric; null where feed missing)
    mint_by = {x["symbol"]: x.get("mint") for x in UNI}
    # taker_fee, maker_fee, variable-flag per venue (public fee schedules;
    # meteora/uniswap dynamic tiers -> variable=1, fee null, never faked)
    FEE_SCHEDULE = {"pumpswap": (25, None, 0), "raydium": (25, None, 0),
                    "orca": (30, None, 0), "meteora": (None, None, 1),
                    "uniswap": (None, None, 1), "aerodrome": (None, None, 1),
                    "ramses": (None, None, 1)}
    VENUE_TYPE = {"pumpswap": "amm", "raydium": "amm", "orca": "amm",
                  "meteora": "amm", "uniswap": "amm", "aerodrome": "amm"}
    def dex_first_pair_url(sym):
        t = next((x for x in UNI if x["symbol"] == sym), None)
        if not t or not t.get("mint"):
            return None
        raw = load(f"dex__{sym}__{t['mint'].replace('/', '_')}.json")
        if not isinstance(raw, list) or not raw:
            return None
        p1 = raw[0]
        ch, pair = p1.get("chainId"), p1.get("pairAddress")
        return f"https://dexscreener.com/{ch}/{pair}" if (ch and pair) else None
    rows, venues = [], []
    for b in base:
        mc, fdv = b.get("mcap_usd"), b.get("fdv_usd")
        vol = b.get("volume_24h_usd")
        liq = b.get("liquidity_usd")
        # inference sales proxy v0: SQUIRE 1100 SOL creator fees; else null
        if b["symbol"] == "SQUIRE" and sol_px:
            sales_ann = round(1100 * sol_px, 2)
        else:
            sales_ann = None
        earn_ann = None  # needs protocol-vs-holder revenue split per project
        tvl = None
        p_sales = round(mc / sales_ann, 2) if mc and sales_ann else None
        p_earn = None
        fdv_sales = round(fdv / sales_ann, 2) if fdv and sales_ann else None
        # PEG-style: P/S divided by revenue CAGR proxy (chg_30d as growth g). null v0 except majors
        g = b.get("chg_30d_pct")
        peg = round(p_sales / g, 3) if p_sales and g else None
        # draws
        drop_ath = pct(b.get("price_usd"), b.get("ath_usd")) if b.get("ath_usd") else None
        # drop_from_ath should be negative-or-zero; pct(price,ath) already that
        rise_atl = pct(b.get("price_usd"), b.get("atl_usd")) if b.get("atl_usd") else None
        # DEX rows: full 1d-candle sig-low; majors: weak proxy = atl if post-ath
        sig_low, sig_ts, weak, rise_sig = None, None, None, None
        if b.get("source") == "dexscreener" and b.get("ath_usd"):
            closes = hist_of(b["symbol"])
            sig_low, sig_ts, weak = siglow_full(closes, now_ts)
            rise_sig = pct(b.get("price_usd"), sig_low) if sig_low else None
        elif b.get("ath_ts") and b.get("atl_ts") and b["atl_ts"] > b["ath_ts"]:
            sig_low, sig_ts, weak = b["atl_usd"], b["atl_ts"], 1
            rise_sig = pct(b.get("price_usd"), sig_low) if sig_low else None
        if b.get("supply_circ") is None and mc and b.get("price_usd"):
            b["supply_circ"] = mc / b["price_usd"]
        if b.get("source") == "dexscreener":
            t2 = next((x for x in UNI if x["symbol"] == b["symbol"]), None)
            try:
                raw2 = load(f"dex__{b['symbol']}__{t2['mint'].replace('/', '_')}.json") or []
                bb = sum((pp.get("txns") or {}).get("h24", {}).get("buys") or 0 for pp in raw2)
                ss = sum((pp.get("txns") or {}).get("h24", {}).get("sells") or 0 for pp in raw2)
                if bb + ss:
                    b["buys_minus_sells_proxy"] = round((bb - ss) / (bb + ss) * 100, 2)
            except Exception:
                pass
        # supply deltas (numeric where CG gives totals)
        circ, tot, mx = b.get("supply_circ"), b.get("supply_total"), b.get("supply_max")
        minted_pct = round((tot - circ) / tot * 100, 2) if tot and circ else None
        net_pct = round((circ - mx) / mx * 100, 2) if circ and mx else None
        u = next(x for x in UNI if x["symbol"] == b["symbol"])
        gid = b.get("coingecko_gt") or u.get("coingecko_id")
        rows.append({
            **b,
            "sales_ann_usd": sales_ann, "earnings_ann_usd": earn_ann, "tvl_usd": tvl,
            "p_sales": p_sales, "p_earnings": p_earn, "fdv_to_sales": fdv_sales,
            "peg_proxy": peg, "revenue_growth_30d_pct": g,
            "mcap_share_pct": round((mc or 0) / tot_mcap * 100, 4),
            "volume_share_pct": round(vol / tot_vol * 100, 4) if (vol and tot_vol) else None,
            "liquidity_share_pct": round(liq / tot_liq * 100, 4) if (liq and tot_liq) else None,
            "sales_share_pct": None, "usage_share_pct": None,
            "drop_from_ath_pct": drop_ath,
            "days_since_ath": round((now_ts - b["ath_ts"]) / 86400, 1) if b.get("ath_ts") else None,
            "rise_from_atl_pct": rise_atl,
            "days_since_atl": round((now_ts - b["atl_ts"]) / 86400, 1) if b.get("atl_ts") else None,
            "sig_low_usd": sig_low, "sig_low_ts": sig_ts, "sig_low_weak": weak,
            "rise_from_siglow_pct": rise_sig,
            "fdv_to_mcap": round(fdv / mc, 3) if fdv and mc else None,
            "circ_pct_of_max": round(circ / mx * 100, 2) if circ and mx else None,
            "volume_ann_proxy_usd": round(vol * 365, 2) if vol else None,
            "mcap_to_vol_24h": round(mc / vol, 2) if mc and vol else None,
            "liq_to_mcap_pct": round(liq / mc * 100, 3) if liq and mc else None,
            "vol_to_liq_turnover": round(vol / liq, 3) if vol and liq else None,
            "buys_minus_sells_proxy": b.get("buys_minus_sells_proxy"),
            "supply_minted_pct": minted_pct, "supply_burned_pct": None,
            "supply_net_pct": net_pct,
            "unlock_next_ts": None, "unlock_next_pct": None,
            "born_ts": b.get("born_ts"),
            "age_days": round((now_ts - b["born_ts"]) / 86400, 1) if b.get("born_ts") else None,
            "gmgn_url": (("https://gmgn.ai/sol/token/" + mint_by[b["symbol"]])
                           if (b.get("chain") == "solana" and mint_by.get(b["symbol"]))
                           else ("https://gmgn.ai/base/token/" + mint_by[b["symbol"]]
                                 if (b.get("chain") == "base" and mint_by.get(b["symbol"])) else None)),
            "dex_url": dex_first_pair_url(b["symbol"]),  # null for majors/seeds (no DEX pair)
            "coingecko_url": (("https://www.coingecko.com/en/coins/" + gid)
                                if gid else None),
            "cmc_url": (("https://coinmarketcap.com/currencies/" + u["cmc_slug"] + "/")
                          if u.get("cmc_slug") else None),
            "tvl_to_sales": round(tvl / sales_ann, 3) if tvl and sales_ann else None,
            "price_hist_30d": b.get("hist30") or [],
            "fetched_at": now,
        })
        # venues: one row per dex pair. Taker reads fee+slippage at size;
        # maker/LP reads fee APR on deployed depth. AMM rows carry taker_fee;
        # maker_fee applies on CLOB rows (none listed yet — columns reserved).
        t = next(x for x in UNI if x["symbol"] == b["symbol"])
        if b["source"] == "dexscreener" and t.get("mint"):
            raw = load(f"dex__{b['symbol']}__{t['mint'].replace('/','_')}.json") or []
            for p in raw if isinstance(raw, list) else []:
                v = (p.get("volume") or {}).get("h24") or 0
                l = (p.get("liquidity") or {}).get("usd") or 0
                tx = p.get("txns", {}).get("h24", {})
                dex = (p.get("dexId") or "?").lower()
                taker, maker, varflag = FEE_SCHEDULE.get(dex, (None, None, 1))
                venues.append({
                    "symbol": b["symbol"], "venue": (p.get("dexId") or "?"),
                    "venue_type": VENUE_TYPE.get(dex, "amm"),
                    "chain": p.get("chainId"), "pair": p.get("pairAddress"),
                    "price_usd": float(p.get("priceUsd") or 0) or None,
                    "volume_24h_usd": v or None, "liquidity_usd": l or None,
                    "trades_24h": ((tx.get("buys") or 0) + (tx.get("sells") or 0)) or None,
                    "buys_24h": tx.get("buys"), "sells_24h": tx.get("sells"),
                    "taker_fee_bps": taker, "maker_fee_bps": maker,
                    "fee_variable": varflag,
                    "slip_1k_bps": round(1000 / (l / 2) * 10000, 1) if l else None,
                    "slip_10k_bps": round(10000 / (l / 2) * 10000, 1) if l else None,
                    "lp_apr_proxy_pct": round(v * (taker / 1e4) / l * 365 * 100, 2) if (v and l and taker) else None,
                    "lp_turnover": round(v / l, 4) if v and l else None,
                    "trader_depth": l or None,
                })
    # oldest through for STALE_MASK badge
    thrus = sorted(str(r.get("through") or "") for r in rows if r.get("through"))
    oldest = thrus[0] if thrus else now[:10]
    out = {"as_of": now, "server_ts": now_ts, "through_oldest": oldest, "tokens": len(rows),
           "sol_usd": sol_px, "universe_mcap_usd": tot_mcap,
           "universe_volume_24h_usd": tot_vol, "universe_liquidity_usd": tot_liq,
           "method": {"sales_proxy_v0": "SQUIRE=1100 SOL*SOLpx; others null until per-project inference-revenue feeds land",
                      "shares": "mcap_share=capital dominance only; volume_share/liquidity_share live; sales_share=revenue/universe_revenue and usage_share=tokens-or-calls/universe total, both null until per-project inference-revenue feeds land",
                      "history": "DEX rows: GeckoTerminal day candles -> ATH/ATL/dates, full-rule sig-low, 30d spark; supply_total prefers GT normalized supply, else public-RPC totalSupply",
                      "sig_low": "lowest 1d close post-ATH (>=7d old) with >=20pct drawdown else weakest post-ATH low (weak=1)",
                      "age": "DEX rows: oldest pairCreatedAt; majors: curated genesis_date in universe.json (TAO 2021-01-09, VVV 2025-01-27, DOT 2020-05-26; ROUTER null, uncertain row)",
                      "venues": "taker cost=taker_fee+slippage at size (CPMM 50/50 proxy); maker/lp economics=lp_apr_proxy on depth; dynamic-fee venues flagged, never faked"},
           "columns_note": "every cell numeric/epoch/null; names+urls never in cells (venues/unlocks are rows, not strings)",
           "tokens_rows": rows}
    wout(os.path.join(OUT, "comps.json"), out)
    wout(os.path.join(OUT, "venues.json"), {"as_of": now, "server_ts": now_ts, "n": len(venues), "rows": venues,
               "note": "taker: taker_fee_bps+slip at size; maker/lp: lp_apr_proxy_pct on depth"})
    wout(os.path.join(OUT, "unlocks.json"), {"as_of": now, "server_ts": now_ts, "n": 0, "rows": [],
               "note": "unlock_next_ts/pct null for all rows; fill from tokenomics docs + vesting contracts"})
    # csv (flat numerics)
    keys = ["symbol","tier","chain","source","stale","price_usd","mcap_usd","fdv_usd","sales_ann_usd",
            "p_sales","p_earnings","fdv_to_sales","peg_proxy","revenue_growth_30d_pct","mcap_share_pct",
            "volume_share_pct","liquidity_share_pct","sales_share_pct","usage_share_pct",
            "drop_from_ath_pct","days_since_ath","rise_from_atl_pct","days_since_atl",
            "sig_low_usd","sig_low_ts","sig_low_weak","rise_from_siglow_pct",
            "volume_24h_usd","mcap_to_vol_24h","liquidity_usd","liq_to_mcap_pct","vol_to_liq_turnover",
            "chg_1h_pct","chg_24h_pct","txns_24h","supply_circ","supply_total","supply_max",
            "supply_minted_pct","supply_burned_pct","supply_net_pct","tvl_to_sales",
            "born_ts","age_days","gmgn_url","dex_url","coingecko_url","cmc_url",
            "site_url","x_url","tg_url","discord_url","through"]
    def _csv(tmp):
        with open(tmp, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
            w.writeheader()
            for r in rows: w.writerow(r)
    wout(os.path.join(OUT, "comps.csv"), _csv, is_json=False)
    print(f"comps ok: {len(rows)} rows, {len(venues)} venue rows, oldest={oldest}")

if __name__ == "__main__":
    main()
