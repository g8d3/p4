"""REAL-DATA collector (stdlib only).

Pulls REAL public no-key facts into REAL datasets:
  crypto-spot: BTC/USD + ETH/USD spot prices
    1st choice CoinGecko simple/price (free, no key), fallback Coinbase spot,
    then Kraken ticker. First live answer wins; the winning origin is stored
    per row as `source` so anyone can re-pull the same fact and match it.
  usd-fx: USD/EUR + USD/GBP + USD/JPY daily reference rates
    open.er-api.com (free, no key).

Every ingested row carries {source, fetched_at} (+ upstream_at for FX).
Only changed-or-new values are ingested (no dupe spam); snapshots republish
every successful tick. Rate respect: cache-first per source (at most one
upstream hit per 5 min), CoinGecko single try, 20s timeouts, <=2 tries with
backoff elsewhere; HTTP 429 triggers a 10-min backoff serving cache only;
failures log fetch-failed and keep serving cache — the daemon never hammers
a blocked endpoint.

Runs as the prod collector node (needs.json collector_name, test:false).
"""
import json
import os
import time
import urllib.request

DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}

# Rate-limit respect: at most one upstream hit per source per TTL; on HTTP 429
# the source backs off (no retry storm) and ticks serve cache instead.
CACHE_TTL = 300
BACKOFF_429 = 600


def _cfg():
    with open(os.path.join(DIR, "needs.json")) as f:
        return json.load(f)


def _now():
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _get(url, timeout=20):
    req = urllib.request.Request(url, headers=UA, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read(200000).decode("utf-8", "replace"))


def _try(url, tries=2):
    last = None
    for i in range(tries):
        try:
            return _get(url), None
        except Exception as e:
            code = getattr(e, "code", None)
            if code == 429:
                return None, "429 rate-limited (backing off, serving cache)"
            last = str(e)[:200]
            time.sleep(1 + i * 2)
    return None, last


def _parse_at(s):
    import datetime
    try:
        dt = datetime.datetime.fromisoformat(str(s))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.timestamp()
    except Exception:
        return 0


def _load_cache():
    try:
        c = _cfg()
        fp = os.path.join(DIR, str(c.get("collect_cache_path",
                                        "data/collect_cache.json")))
        if os.path.exists(fp):
            d = json.load(open(fp))
            return d if isinstance(d, dict) else {}
    except Exception:
        pass
    return {}


def _save_cache(cache):
    try:
        c = _cfg()
        fp = os.path.join(DIR, str(c.get("collect_cache_path",
                                        "data/collect_cache.json")))
        json.dump(cache, open(fp, "w"), indent=1)
    except Exception:
        pass


def _cache_get(key):
    """Fresh cached payload for key, or None (TTL = CACHE_TTL)."""
    entry = _load_cache().get(key)
    if not isinstance(entry, dict):
        return None
    if time.time() - _parse_at(entry.get("at", "")) < CACHE_TTL:
        return entry
    return None


def _limited(state, key):
    """True while a 429 backoff is in force for key."""
    try:
        return time.time() < float(
            (state.get("rate_limited_until") or {}).get(key, 0))
    except Exception:
        return False


def _mark_limited(state, key):
    lim = state.setdefault("rate_limited_until", {})
    lim[key] = time.time() + BACKOFF_429
    return state


def get_crypto(state):
    """(payload, source, from_cache) or (None, error, False). Cache-first:
    a fresh cache hit means zero upstream requests; a 429 backoff means
    cache-only."""
    hit = _cache_get("crypto")
    if hit and (hit.get("data") or hit.get("payload")):
        return (hit.get("data") or hit.get("payload"),
                hit.get("source", "cache"), True)
    if _limited(state, "crypto"):
        stale = _load_cache().get("crypto") or {}
        if stale.get("data") or stale.get("payload"):
            return (stale.get("data") or stale.get("payload"),
                    (stale.get("source", "cache") + "+cache"), True)
        return None, "429 backoff in force, no cache yet", False
    payload, src = fetch_crypto()
    if payload is None and str(src).startswith("429"):
        _mark_limited(state, "crypto")
        stale = _load_cache().get("crypto") or {}
        if stale.get("data") or stale.get("payload"):
            return (stale.get("data") or stale.get("payload"),
                    (stale.get("source", "cache") + "+cache"), True)
    if payload is not None:
        _save_cache({**_load_cache(), "crypto":
                       {"at": _now(), "data": payload, "source": src}})
    return payload, src, False


def get_fx(state):
    """(payload, source, upstream_at, from_cache). Same cache rules."""
    hit = _cache_get("fx")
    if hit and hit.get("data"):
        return (hit["data"], hit.get("source", "cache"),
                hit.get("upstream_at", ""), True)
    if _limited(state, "fx"):
        stale = _load_cache().get("fx") or {}
        if stale.get("data"):
            return (stale["data"], stale.get("source", "cache") + "+cache",
                    stale.get("upstream_at", ""), True)
        return None, "429 backoff in force, no cache yet", "", False
    payload, src, upstream = fetch_fx()
    if payload is None and str(src).startswith("429"):
        _mark_limited(state, "fx")
        stale = _load_cache().get("fx") or {}
        if stale.get("data"):
            return (stale["data"], stale.get("source", "cache") + "+cache",
                    stale.get("upstream_at", ""), True)
    if payload is not None:
        _save_cache({**_load_cache(), "fx":
                       {"at": _now(), "data": payload, "source": src,
                        "upstream_at": upstream}})
    return payload, src, upstream, False


def fetch_crypto():
    """Returns ({BTC: price, ETH: price}, source) or (None, error)."""
    data, err = _try(
        "https://api.coingecko.com/api/v3/simple/price"
        "?ids=bitcoin,ethereum&vs_currencies=usd", tries=1)
    if data and isinstance(data, dict) and "bitcoin" in data:
        try:
            return ({"BTC": float(data["bitcoin"]["usd"]),
                     "ETH": float(data["ethereum"]["usd"])}, "coingecko")
        except (KeyError, TypeError, ValueError):
            pass
    out = {}
    for sym in ("BTC", "ETH"):
        data, err = _try(
            f"https://api.coinbase.com/v2/prices/{sym}-USD/spot", tries=2)
        try:
            out[sym] = float(data["data"]["amount"])
        except (TypeError, KeyError, ValueError):
            out = {}
            break
    if out == {"BTC": out.get("BTC"), "ETH": out.get("ETH")} and len(out) == 2:
        return out, "coinbase"
    data, err = _try(
        "https://api.kraken.com/0/public/Ticker?pair=XBTUSD,ETHUSD", tries=2)
    try:
        r = data["result"]
        return ({"BTC": float(r["XXBTZUSD"]["c"][0]),
                 "ETH": float(r["XETHZUSD"]["c"][0])}, "kraken")
    except (TypeError, KeyError, ValueError, IndexError):
        pass
    return None, "all crypto sources failed%s" % (
        (" (last: %s)" % err) if err else "")


def fetch_fx():
    """Returns ({USD/EUR: rate, ...}, source, upstream_at) or (None, err, '')."""
    data, err = _try("https://open.er-api.com/v6/latest/USD", tries=2)
    try:
        rates = data["rates"]
        out = {"USD/EUR": float(rates["EUR"]),
               "USD/GBP": float(rates["GBP"]),
               "USD/JPY": float(rates["JPY"])}
        return out, "open.er-api.com", str(data.get("time_last_update_utc", ""))
    except (TypeError, KeyError, ValueError):
        pass
    return None, "fx source failed%s" % ((" (last: %s)" % err) if err else ""), ""


def _collector_creds(base_url):
    """Prod collector node creds; signs up once, reuses (0600 file)."""
    c = _cfg()
    name = str(c.get("collector_name", "real-collector") or "real-collector")
    fp = os.path.join(DIR, "data", "collector.json")
    if os.path.exists(fp):
        try:
            d = json.load(open(fp))
            if d.get("node_id") and d.get("token"):
                return d["node_id"], d["token"]
        except Exception:
            pass
    body = json.dumps({"name": name}).encode()
    req = urllib.request.Request(base_url + "/api/signup", data=body,
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=20) as r:
        d = json.loads(r.read(20000).decode("utf-8", "replace"))
    creds = {"node_id": d["node_id"], "token": d["token"]}
    fd = os.open(fp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(creds, f)
    return creds["node_id"], creds["token"]


def _post(base_url, path, payload):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(base_url + path, data=body,
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read(200000).decode("utf-8", "replace"))


def collect_tick(base_url="http://127.0.0.1:8383"):
    """One fetch->ingest->publish tick. Returns the tick record."""
    c = _cfg()
    try:
        base_url = "http://127.0.0.1:%d" % int(c.get("port", 8383))
    except (TypeError, ValueError):
        pass
    at = _now()
    sfp = os.path.join(DIR, str(c.get("collect_state_path",
                                      "data/collect_state.json")))
    try:
        state = json.load(open(sfp))
    except Exception:
        state = {}
    if not isinstance(state, dict):
        state = {}
    crypto, crypto_src, crypto_cached = get_crypto(state)
    fx, fx_src, upstream_at, fx_cached = get_fx(state)
    if crypto is None and fx is None:
        rec = {"at": at, "status": "fetch-failed",
               "crypto_error": crypto_src, "fx_error": fx_src,
               "ingested": 0, "note": "both sources down; cache kept, no ingest"}
        _log(rec)
        return rec
    try:
        node_id, token = _collector_creds(base_url)
    except Exception as e:
        rec = {"at": at, "status": "signup-failed", "error": str(e)[:200],
               "ingested": 0}
        _log(rec)
        return rec
    last = state.get("last_values", {}) if isinstance(state, dict) else {}
    ingested, rows = 0, {"crypto-spot": [], "usd-fx": []}
    if crypto:
        for sym, px in crypto.items():
            if last.get("crypto:" + sym) != px:
                rows["crypto-spot"].append(
                    {"symbol": sym, "price_usd": px,
                     "source": crypto_src, "fetched_at": at})
    if fx:
        for pair, rate in fx.items():
            if last.get("fx:" + pair) != rate:
                rows["usd-fx"].append(
                    {"pair": pair, "rate": rate, "source": fx_src,
                     "fetched_at": at, "upstream_at": upstream_at})
    errors = []
    for ds, recs in rows.items():
        if not recs:
            continue
        try:
            res = _post(base_url, "/api/ingest",
                        {"node_id": node_id, "token": token, "dataset": ds,
                         "records": recs})
            ingested += int(res.get("accepted", 0))
            for r in recs:
                key = ("crypto:" + r["symbol"]) if ds == "crypto-spot" \
                    else ("fx:" + r["pair"])
                last[key] = (r.get("price_usd", r.get("rate")))
        except Exception as e:
            errors.append("%s ingest: %s" % (ds, str(e)[:150]))
    published = []
    for ds in ("crypto-spot", "usd-fx"):
        try:
            res = _post(base_url, "/api/publish",
                        {"dataset": ds, "node_id": node_id, "token": token})
            if res.get("ok"):
                published.append(ds)
            else:
                errors.append("%s publish: %s" % (ds, str(res)[:150]))
        except Exception as e:
            errors.append("%s publish: %s" % (ds, str(e)[:150]))
    state = {"at": at, "last_values": last,
             "rate_limited_until": state.get("rate_limited_until", {}),
             "ingested_total": int(state.get("ingested_total", 0)) + ingested,
             "consecutive_failures": 0 if (crypto or fx) else int(
                 state.get("consecutive_failures", 0)) + 1,
             "last_sources": {"crypto": crypto_src if crypto else None,
                              "fx": fx_src if fx else None}}
    json.dump(state, open(sfp, "w"), indent=1)
    rec = {"at": at, "status": "ok" if not errors else "partial",
           "crypto_source": crypto_src if crypto else None,
           "fx_source": fx_src if fx else None,
           "from_cache": {"crypto": bool(crypto_cached),
                          "fx": bool(fx_cached)},
           "crypto": crypto, "fx": fx,
           "ingested": ingested,
           "skipped_unchanged": sum(len(v) for v in rows.values()) == 0,
           "published": published, "errors": errors}
    _log(rec)
    return rec


def _log(rec):
    c = _cfg()
    lp = os.path.join(DIR, str(c.get("collect_log_path", "data/collect.jsonl")))
    with open(lp, "a") as f:
        f.write(json.dumps(rec) + "\n")
