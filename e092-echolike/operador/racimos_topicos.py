#!/usr/bin/env python3
"""Topic cluster retrospective (code-only, no AI, no network, read-only).

Same rule and same topics as the live alerter operador/alerta_topicos.py
(UMBRAL likes on one topic in VENTANA_H hours — imported from that module so
the two can never drift apart), but looks BACKWARD: for each of the last N
Bogota CALENDAR days it prints which clusters would have fired, with the real
stored post links. Windows are fixed calendar days ending 23:59:59 Bogota, not
the live alerter's rolling 24h — fine for a look back. Nothing is invented,
sent, or written — dry-run only. The live alerter (alerta_topicos.py, cron)
stays canonical for actual pings.

Extra exploratory topics (ai-trading-bots, memecoins) live behind --extra;
without it only the live alerter's topics are evaluated.

Usage: python3 operador/racimos_topicos.py [--days 7] [--desde YYYY-MM-DD] [--estado DIR] [--extra]
  --days: how many Bogota days back (default 7). --desde: last window end
  (default today). --estado: dir holding likes_extension.jsonl + x_items.json
  (default: estado/ next to the script). Reads only, warns when files are missing.
"""
import datetime as dt
import json
import os
import re
import sys

# Single source of truth: the live alerter in the e092 checkout.
sys.path.insert(0, "/home/vuos/code/p4/e092-echolike/operador")
try:
    from alerta_topicos import TOPICS as LIVE_TOPICS, UMBRAL, VENTANA_H
except ImportError:
    LIVE_TOPICS, UMBRAL, VENTANA_H = None, 5, 24

BOG = dt.timezone(dt.timedelta(hours=-5))

# Exploratory only (--extra): grounded in Oct 2026 liked texts, NOT live rules.
EXTRA_TOPICS = {
    "ai-trading-bots": [r"ai agent", r"trading bot", r"grok bot", r"inference",
                        r"prompts", r"\bswarm\b", r"hotbot"],
    "memecoins": [r"(\$[A-Z]{2,10}\b.*){2,}", r"\baped\b", r"\bmcap\b",
                  r"market cap", r"dexscreener"],
}


def ts(d):
    for k in ("clicked_at", "recv_at", "visto"):
        v = d.get(k)
        if v:
            try:
                t = dt.datetime.fromisoformat(str(v).replace("Z", "+00:00"))
                return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)
            except ValueError:
                continue
    return None


def _agregar(rows, vistos, d, iid, t):
    # One post = one like: x_items mirrors jsonl rows (same URL, often a
    # different id, plus exact row duplicates). Dedupe by URL when present.
    url = d.get("url") or ""
    key = ("url", url) if url else ("id", iid)
    if key in vistos:
        return
    vistos.add(key)
    rows.append({"id": iid, "t": t, "text": d.get("text") or "",
                 "url": url, "handle": d.get("handle") or ""})


def cargar(estado_dir):
    rows, vistos, faltan = [], set(), []
    jsonl = os.path.join(estado_dir, "likes_extension.jsonl")
    xitems = os.path.join(estado_dir, "x_items.json")
    try:
        f = open(jsonl, encoding="utf-8")
    except OSError:
        f = None
        faltan.append(jsonl)
    if f:
        with f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if d.get("kind") != "like":
                    continue
                t = ts(d)
                if not t:
                    continue
                _agregar(rows, vistos, d, str(d.get("id") or ""), t)
    try:
        items = json.load(open(xitems, encoding="utf-8")).get("items") or []
    except Exception:
        items = []
        faltan.append(xitems)
    for d in items:
        if d.get("type") != "like":
            continue
        t = ts(d)
        if not t:
            continue
        _agregar(rows, vistos, d, str(d.get("id") or ""), t)
    return rows, faltan


def topic_de(rx, texto):
    return [topic for topic, pats in rx.items()
            if any(p.search(texto or "") for p in pats)]


def main(argv):
    days, desde, estado, extra = 7, None, None, False
    for i, a in enumerate(argv):
        if a == "--days" and i + 1 < len(argv):
            days = max(1, int(argv[i + 1]))
        if a == "--desde" and i + 1 < len(argv):
            d0 = dt.datetime.strptime(argv[i + 1], "%Y-%m-%d").replace(tzinfo=BOG)
            desde = d0.replace(hour=23, minute=59, second=59, microsecond=0)
        if a == "--estado" and i + 1 < len(argv):
            estado = argv[i + 1]
        if a == "--extra":
            extra = True
    if LIVE_TOPICS is None:
        print("error: cannot import TOPICS from alerta_topicos.py "
              "(e092 checkout missing); retrospective needs the live rule", file=sys.stderr)
        return 2
    topics = dict(LIVE_TOPICS)
    if extra:
        topics.update(EXTRA_TOPICS)
    if estado is None:
        estado = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "estado")
    rx = {t: [re.compile(p, re.I) for p in pats] for t, pats in topics.items()}
    likes, faltan = cargar(estado)
    for f in faltan:
        print(f"warning: missing {f} (use --estado DIR or run where estado/ exists)", file=sys.stderr)
    if desde is None:
        ahora_bog = dt.datetime.now(dt.timezone.utc).astimezone(BOG)
        desde = ahora_bog.replace(hour=23, minute=59, second=59, microsecond=0)
    fired, out = set(), []
    for back in range(days):
        fin = desde - dt.timedelta(days=back)
        ini = fin - dt.timedelta(hours=VENTANA_H)
        win = [r for r in likes if ini < r["t"] <= fin]
        etiqueta = fin.strftime("%Y-%m-%d")
        grupos = {}
        for r in win:
            for t in topic_de(rx, r["text"]):
                grupos.setdefault(t, []).append(r)
        if not grupos:
            out.append(f"{etiqueta}: {len(win)} likes, no topic hits")
            continue
        for topic in sorted(grupos):
            hits = grupos[topic]
            if len(hits) < UMBRAL:
                out.append(f"{etiqueta}: {topic}: {len(hits)} likes (<{UMBRAL}, no fire)")
                continue
            marca = " (repeat)" if topic in fired else ""
            fired.add(topic)
            seen, links = set(), []
            for h in hits:
                if h["url"] and h["url"] not in seen:
                    seen.add(h["url"])
                    links.append(h["url"])
            out.append(f"{etiqueta}: FIRE {topic}: {len(hits)} likes, {len(links)} unique links{marca}")
            for u in links[:10]:
                out.append(f"  - {u}")
            if len(links) > 10:
                out.append(f"  (+{len(links) - 10} more)")
            if len(links) < len(hits):
                out.append(f"  ({len(hits) - len(links)} without stored/duplicate link, not shown)")
    print(f"retrospective: {len(likes)} likes loaded, {days} windows ending {desde.strftime('%Y-%m-%d')}")
    for s in out:
        print(s)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
