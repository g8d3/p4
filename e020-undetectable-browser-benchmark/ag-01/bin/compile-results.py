#!/usr/bin/env python3
"""Compile individual test results into a comparison table."""
import json
import os
import glob

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

result_files = glob.glob(os.path.join(OUTPUT_DIR, "*-result.json"))

rows = []
for f in sorted(result_files):
    with open(f) as fh:
        data = json.load(fh)

    browser = data.get("browser", os.path.basename(f))
    captcha = data.get("captcha")
    search = data.get("search")
    authenticated = data.get("authenticated")
    error = data.get("error", "")

    captcha_str = {True: "YES", False: "no", None: "?"}[captcha]
    search_str = {True: "YES", False: "no", None: "?"}[search]
    auth_str = {True: "YES", False: "no", None: "?"}[authenticated]
    error_str = error if error else "OK"

    rows.append({
        "browser": browser,
        "captcha": captcha_str,
        "search": search_str,
        "authenticated": auth_str,
        "status": error_str,
    })

# CSV output
csv_path = os.path.join(OUTPUT_DIR, "results.csv")
with open(csv_path, "w") as f:
    f.write("browser,captcha,search,authenticated,status\n")
    for r in rows:
        f.write(f'{r["browser"]},{r["captcha"]},{r["search"]},{r["authenticated"]},{r["status"]}\n')

# Summary output
summary_path = os.path.join(OUTPUT_DIR, "summary.md")
with open(summary_path, "w") as f:
    f.write("# Undetectable Browser Benchmark Results\n\n")
    f.write("| Browser | Captcha Blocked | Search Succeeded | Authenticated | Status |\n")
    f.write("|---------|----------------|-----------------|---------------|--------|\n")
    for r in rows:
        f.write(f'| {r["browser"]} | {r["captcha"]} | {r["search"]} | {r["authenticated"]} | {r["status"]} |\n')

print(f"Results written to {csv_path} and {summary_path}")
print()
with open(summary_path) as f:
    print(f.read())
