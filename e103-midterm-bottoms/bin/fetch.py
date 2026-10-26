#!/usr/bin/env python3
"""Download raw inputs into data/raw/. No keys needed: Shiller .xls + FRED CSVs."""
import json
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
NEEDS = json.load(open(ROOT / "needs.json"))


def get(url, dest):
    dest = RAW / dest
    print("fetch", url, "->", dest)
    req = urllib.request.Request(url, headers={"User-Agent": "p4-e103-research"})
    dest.write_bytes(urllib.request.urlopen(req, timeout=120).read())
    print("  saved", dest.stat().st_size, "bytes")


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    get(NEEDS["sources"]["shiller_xls"], "ie_data.xls")
    for sid in NEEDS["sources"]["fred_monthly"] + [NEEDS["sources"]["fred_daily_spx"]]:
        url = NEEDS["sources"]["fred_csv"].format(id=sid)
        get(url, f"fred_{sid.lower()}.csv")
    print("done")


if __name__ == "__main__":
    main()
