#!/bin/bash
# tds — Text Delta Stream CLI
# Usage: tds watch|record|replay [args]

exec python3 -m tds.cli "$@"
