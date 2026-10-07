#!/bin/bash
# One content pass: drafts next pilot post per persona, appends to public log (dry-run, no posting).
cd "$(dirname "$0")/.."
python3 - <<'PY'
import json
ps = json.load(open('data/personas.json'))
with open('data/logs.jsonl','a') as f:
  import time
  for p in ps:
    f.write(json.dumps({"ts":int(time.time()),"kind":"draft","text":"DRAFT for %s: %s" % (p["name"], p["pilot_posts"][0][:90])}, ensure_ascii=False)+"\n")
print("drafted", len(ps), "posts to public log")
PY
