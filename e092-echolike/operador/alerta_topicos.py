#!/usr/bin/env python3
"""Code-only topic cluster alert (no AI): when Nova likes 5+ posts on the same
topic within 24h, ping Coco via bin/to_coco.sh with the post links.

Topics are plain keyword/hashtag/cashtag regexes. State (already alerted
today) lives in estado/alerta_topicos.json. Usage:
python3 operador/alerta_topicos.py [--dry]   (dry prints, does not ping)
"""
import datetime as dt
import json
import os
import re
import subprocess
import sys

D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOG = dt.timezone(dt.timedelta(hours=-5))
JSONL = os.path.join(D, "estado", "likes_extension.jsonl")
STATE = os.path.join(D, "estado", "alerta_topicos.json")
TO_COCO = os.path.expanduser("~/code/p4/e100-openbot/bin/to_coco.sh")
VENTANA_H = 24
UMBRAL = 5

TOPICS = {
    "fairer launchpads": [r"launchpad", r"pumpfun", r"\$launch\b", r"\blaunch(?:es|ed|ing)?\b",
                           r"\bvamp(?:s)?\b", r"\bido\b", r"presale", r"\btge\b"],
}


def cargar():
    rows = []
    try:
        f = open(JSONL, encoding="utf-8")
    except OSError:
        return rows
    with f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def ts(d):
    for k in ("clicked_at", "recv_at"):
        v = d.get(k)
        if v:
            try:
                return dt.datetime.fromisoformat(str(v).replace("Z", "+00:00"))
            except ValueError:
                continue
    return None


def main(argv):
    dry = "--dry" in argv
    ahora = dt.datetime.now(dt.timezone.utc)
    desde = ahora - dt.timedelta(hours=VENTANA_H)
    likes = [d for d in cargar() if d.get("kind") == "like" and (ts(d) or ahora) >= desde]
    try:
        state = json.load(open(STATE, encoding="utf-8"))
    except Exception:
        state = {"alerts": []}
    hoy = ahora.astimezone(BOG).strftime("%Y-%m-%d")
    salidas = []
    for topic, pats in TOPICS.items():
        rx = [re.compile(p, re.I) for p in pats]
        hits = [d for d in likes if any(r.search(d.get("text") or "") for r in rx)]
        if len(hits) < UMBRAL:
            continue
        if any(a.get("topic") == topic and a.get("day") == hoy for a in state["alerts"]):
            salidas.append(f"SKIP {topic}: already alerted today ({len(hits)} likes)")
            continue
        links = [d.get("url") for d in hits if d.get("url")]
        msg = (f"Topic alert: {len(hits)} likes in 24h on '{topic}'. "
               + " ".join(links[:10]))
        if dry:
            salidas.append(f"DRY {topic}: {len(hits)} likes :: {msg[:200]}")
        else:
            r = subprocess.run([TO_COCO, "alerta-topicos", msg], capture_output=True, text=True, timeout=60)
            salidas.append(f"SENT {topic}: {len(hits)} likes (curl_exit={r.returncode})")
            if r.returncode == 0:
                state["alerts"].append({"topic": topic, "day": hoy, "count": len(hits)})
    if not dry:
        tmp = STATE + ".tmp"
        json.dump(state, open(tmp, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        os.replace(tmp, STATE)
    for s in salidas:
        print(s)
    if not salidas:
        print(f"OK no cluster: {len(likes)} likes in 24h below threshold")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
