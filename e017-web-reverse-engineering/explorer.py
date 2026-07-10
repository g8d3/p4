#!/usr/bin/env python3
"""
explorer.py — Web Reverse Engineering Explorer

Records HAR per interaction, extracts auth, clean analysis.
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))

from core.browser_manager import discover_browsers, pick_best_browser, get_browser_summary
from core.explorer import Explorer
from core.reporter import generate_report, save_report


def main():
    parser = argparse.ArgumentParser(description="Explore and reverse engineer a website")
    parser.add_argument("url", help="URL to explore")
    parser.add_argument("--output", "-o", default=None, help="Output report path")
    parser.add_argument("--browser", "-b", type=int, default=None, help="Force CDP port")
    args = parser.parse_args()

    url = args.url
    if not url.startswith("http"):
        url = "https://" + url

    from urllib.parse import urlparse
    domain = urlparse(url).netloc

    print(f"\n{'='*60}")
    print(f"  STEP 1: Detecting browsers")
    print(f"{'='*60}\n")

    browsers = discover_browsers()
    print(get_browser_summary(browsers))

    port = args.browser or (pick_best_browser(browsers, domain).port if browsers else None)
    if not port:
        print("\n[!] No browsers found.")
        sys.exit(1)

    print(f"\n  Using port: {port}\n")

    print(f"{'='*60}")
    print(f"  STEP 2: Exploring {domain}")
    print(f"{'='*60}\n")

    explorer = Explorer(port=port)
    results = explorer.explore(url, domain)

    print(f"\n{'='*60}")
    print(f"  STEP 3: Generating report")
    print(f"{'='*60}\n")

    report = generate_report(results)

    out_dir = results.get("output_dir", "output")
    if args.output:
        output_path = args.output
    else:
        output_path = os.path.join(out_dir, "report.md")

    save_report(report, output_path)
    print(f"\n  Report: {output_path}")


if __name__ == "__main__":
    main()
