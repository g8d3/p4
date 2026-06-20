#!/usr/bin/env bash
set -euo pipefail

curl -s -X POST -d "$1" http://localhost:8080/subtitle
