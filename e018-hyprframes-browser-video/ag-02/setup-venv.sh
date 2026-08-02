#!/usr/bin/env bash
# Set up the transcription virtualenv (NeMo/Parakeet ASR).
# Portable: run this once on any machine that needs transcription.
# Requires: uv installed, python 3.11 available, model at ~/models/parakeet-ctc-0.6b.nemo
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "Creating .venv (python 3.11)..."
  uv venv --python 3.11 .venv
fi

echo "Installing dependencies from requirements.txt..."
uv pip install --python .venv/bin/python -r requirements.txt

echo "Verifying NeMo imports..."
.venv/bin/python -c "import nemo.collections.asr; print('NeMo OK')"

MODEL="$HOME/models/parakeet-ctc-0.6b.nemo"
if [ -f "$MODEL" ]; then
  echo "Model found: $MODEL"
else
  echo "WARNING: model not found at $MODEL — download it there before transcribing."
fi

echo ""
echo "Done. Usage:"
echo "  source .venv/bin/activate"
echo "  python3 bin/model_worker.py &   # worker (loads model, ~20s)"
echo "  python3 bin/transcribe_server.py &  # HTTP server :9877"
