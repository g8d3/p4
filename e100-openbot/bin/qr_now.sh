#!/bin/bash
# One step: open Settings > Mobile Connect, generate a one-time QR, save /tmp/openbot_qr.png
cd "$(dirname "$0")/.." || exit 1
python3 bin/ui.py Settings >/dev/null 2>&1
python3 bin/ui.py "Mobile Connect" >/dev/null 2>&1
python3 bin/qr.py >/tmp/qrlog 2>&1 && echo "QR ready /tmp/openbot_qr.png $(date +%H:%M:%S) (valid 2 min, single use)"
