#!/usr/bin/env bash
# bin/publish.sh — release EchoLike Lite: build zip + signed crx, publish, verify.
#
# The crx is what makes the Update button in Quetta (and the extensions page)
# work: the browser reads manifest.update_url, downloads extension_update_lite.json,
# compares versions and installs the newer crx. A zip install can never do that.
#
#   bin/publish.sh            build, verify, publish to echolike.app, verify live
#   bin/publish.sh --build    build and verify locally only (no push, no deploy)
set -euo pipefail
cd "$(dirname "$0")/.."

EXT=extension
KEY=.secrets/echolike_lite_crx.pem
PAGES_REPO="${PAGES_REPO:-g8d3/echolike-site}"
UPDATE_JSON=extension_update_lite.json
CRX=echolike-lite.crx
ZIP=echolike-lite.zip
BUILD_ONLY=0
[ "${1:-}" = "--build" ] && BUILD_ONLY=1

VER=$(python3 -c "import json;print(json.load(open('$EXT/manifest.json'))['version'])")
echo "== EchoLike Lite $VER"

# 1) zip (the desktop "load unpacked" path)
rm -f "$ZIP"
(cd "$EXT" && zip -qr ../"$ZIP" . -x ".*")
unzip -p "$ZIP" manifest.json | python3 -c "import json,sys;v=json.load(sys.stdin)['version'];assert v=='$VER',v;print('   zip manifest',v)"

# 2) crx (the auto-update path). npm's crx packs CRX3 the way Chromium's creator does.
[ -f "$KEY" ] || { echo "missing $KEY (signs the crx; never committed)"; exit 1; }
CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/echolike-crx"
if [ ! -d "$CACHE/node_modules/crx/src" ]; then
  echo "   installing crx packer in $CACHE"
  mkdir -p "$CACHE" && (cd "$CACHE" && npm i crx --no-audit --no-fund --silent)
fi
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
unzip -q "$ZIP" -d "$TMP/x"
node -e '
const Crx = require(process.argv[1] + "/node_modules/crx");
const fs = require("fs");
const [key, root, out] = process.argv.slice(2);
new Crx({ rootDirectory: root, privateKey: fs.readFileSync(key) })
  .pack()
  .then(buf => fs.writeFileSync(out, buf))
  .catch(e => { console.error("crx pack failed:", e.message); process.exit(1); });
' "$CACHE" "$KEY" "$TMP/x" "$CRX"

# 3) the update manifest the browser fetches, with the appid of the key that signed it
APPID=$(openssl rsa -in "$KEY" -pubout -outform DER 2>/dev/null | python3 -c "
import hashlib,sys
print(''.join(chr(97+(b>>4))+chr(97+(b&15)) for b in hashlib.sha256(sys.stdin.buffer.read()).digest()[:16]))")
python3 - "$APPID" "$VER" "$UPDATE_JSON" <<'PY'
import sys
appid, ver, out = sys.argv[1], sys.argv[2], sys.argv[3]
open(out, "w").write(
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<gupdate xmlns="http://www.google.com/update2/response" protocol="2.0">\n'
    f'  <app appid="{appid}">\n'
    f'    <updatecheck codebase="https://echolike.app/echolike-lite.crx" version="{ver}" />\n'
    '  </app>\n</gupdate>\n')
print("   appid", appid)
PY

# 4) verify before shipping: a crx the browser rejects fails silently on the phone
python3 bin/check_crx.py "$CRX" --appid "$APPID" --version "$VER"
grep -q "version=\"$VER\"" "$UPDATE_JSON" && grep -q "appid=\"$APPID\"" "$UPDATE_JSON" && echo "   update json matches"
[ "$BUILD_ONLY" = "1" ] && { echo "== build only: not published"; exit 0; }

# 5) publish: page, artifacts, update json
W=$(mktemp -d); trap 'rm -rf "$TMP" "$W"' EXIT
gh repo clone "$PAGES_REPO" "$W/site" -- --depth 1 -q
cp site/index.html site/docs.html server.py "$W/site/"
cp "$ZIP" "$CRX" "$UPDATE_JSON" "$W/site/"
python3 - "$W/site/index.html" "$VER" <<'PY'
import re, sys
p, ver = sys.argv[1], sys.argv[2]
h = open(p).read()
h = re.sub(r"Download \d+(?:\.\d+)+", "Download " + ver, h)
open(p, "w").write(h)
print("   page says:", re.search(r"Download [\d.]+", h).group(0))
PY
cd "$W/site"
if git diff --quiet; then echo "== nothing to change: $VER is already published"; exit 0; fi
git add -A && git commit -q -m "lite $VER" && git push -q origin HEAD
CLOUDFLARE_API_TOKEN="${CLOUDFLARE_API_TOKEN:-${CLOUDFLARE_PAGES_API_KEY:-${CLOUDFLARE_FOCALIS_API_KEY:-}}}" \
  wrangler pages deploy "$W/site" --project-name echolike --branch main --commit-dirty=true 2>&1 | tail -n 2

# 6) verify what the browser will actually see: the manifest AND the artifact it
#    will download. A json that advertises 1.17.5 next to a stale crx makes the
#    browser loop on "Updating…" for ever, and the local checks cannot see it.
GOT=""
for i in $(seq 1 12); do
  got=$(curl -s -m 10 "https://echolike.app/$UPDATE_JSON?b=$RANDOM" | grep -o "version=\"$VER\"" || true)
  if [ -n "$got" ]; then GOT=$got; break; fi
  sleep 10
done
if [ -z "$GOT" ]; then echo "== pushed, but echolike.app still does not report $VER"; exit 2; fi
echo "   update json live: $GOT"

# The artifact itself, as a browser would download it: same signature, same version.
DL=$(mktemp)
curl -s -m 60 -o "$DL" "https://echolike.app/$CRX?b=$RANDOM"
if python3 bin/check_crx.py "$DL" --appid "$APPID" --version "$VER" >/tmp/crx-live.txt 2>&1; then
  echo "== LIVE: echolike.app serves $CRX $VER (manifest + artifact verified)"
  rm -f "$DL"
  exit 0
fi
echo "== the update json says $VER but the served $CRX does not:"
tail -5 /tmp/crx-live.txt
echo "   the browser will stay on 'Updating…' until the artifact matches"
rm -f "$DL"
exit 3
