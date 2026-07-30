#!/usr/bin/env bash
set -euo pipefail

# Upload an image to KIE's temp storage for image-to-image use
# Requires: KIE_API_KEY
#
# Usage:
#   ./kie-upload.sh <image.jpg> [tag]
#
# Example:
#   ./kie-upload.sh output/kie_1234_julia.jpg julia
#   # Returns: https://tempfile.redpandaai.co/kieai/.../julia.jpg

FILE="${1:?Usage: kie-upload.sh <image.jpg> [tag]}"
TAG="${2:-$(basename "$FILE" | sed 's/\.[^.]*$//')}"
UPLOAD_BASE="https://kieai.redpandaai.co"

if [ ! -f "$FILE" ]; then
    echo "File not found: $FILE" >&2; exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT_DIR="${OUTPUT_DIR:-$SCRIPT_DIR/output}"

# Base64 encode and upload
python3 -c "
import json, base64
with open('$FILE', 'rb') as f:
    b64 = base64.b64encode(f.read()).decode()
payload = {'base64Data': 'data:image/jpeg;base64,' + b64, 'uploadPath': 'images/scenes', 'fileName': '${TAG}.jpg'}
with open('/tmp/ki3_upload_${TAG}.json', 'w') as f:
    json.dump(payload, f)
"

resp=$(curl -sS "$UPLOAD_BASE/api/file-base64-upload" \
    -H "Authorization: Bearer $KIE_API_KEY" \
    -H "Content-Type: application/json" \
    -X POST -d @/tmp/ki3_upload_${TAG}.json 2>/dev/null)

rm -f /tmp/ki3_upload_${TAG}.json

url=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('downloadUrl',''))" 2>/dev/null || echo "")

if [ -z "$url" ]; then
    echo "Upload failed: $resp" >&2; exit 1
fi

echo "$url"
