#!/usr/bin/env bash
# Code-only: push data/status.json (written every 2 min by scripts/echolike_pmm.py) to
# g8d3/echolike-site liquidity/status.json, which the /liquidity/ demo section reads.
set -euo pipefail
cd "$(dirname "$0")"
f=data/status.json; [ -s "$f" ] || exit 0
p=liquidity/status.json; r=repos/g8d3/echolike-site/contents/$p
sha=$(gh api "$r" --jq .sha 2>/dev/null || true)
gh api -X PUT "$r" -f message="liquidity demo status" -f content="$(base64 -w0 "$f")" ${sha:+-f sha="$sha"} --jq .commit.sha
