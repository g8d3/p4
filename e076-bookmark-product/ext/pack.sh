#!/bin/bash
# Owner-build packer: stamps ext/build.json (version + UTC time + git rev), then zips.
set -e
cd "$(dirname "$0")"
VER=$(python3 -c "import json; print(json.load(open('manifest.json'))['version'])")
REV=$(git rev-parse --short HEAD 2>/dev/null || echo nogit)
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
python3 -c "import json; json.dump({'version':'$VER','built_at':'$NOW','rev':'$REV'}, open('build.json','w'), indent=1)"
rm -f bookmarkvault-ext.zip
zip -qr bookmarkvault-ext.zip manifest.json build.json background.js loader.js panel.js page-tap.js resilience.js onboarding.html sidepanel/ icons/ -x "*.zip"
echo "packed BookmarkVault v$VER ($NOW UTC, $REV)"
