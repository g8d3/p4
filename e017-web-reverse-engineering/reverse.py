#!/usr/bin/env python3
"""
reverse.py — Web Reverse Engineering CLI

Usage:
    uv run --with httpx reverse.py <url>                     # Full analysis
    uv run --with httpx reverse.py <url> --output report.md  # Custom output
    uv run --with httpx reverse.py <url> --no-interact       # Skip probing
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

from core.browser_manager import discover_browsers, pick_best_browser, get_browser_summary
from core.analyzer import analyze_page
from core.reporter import generate_report, save_report


def main():
    parser = argparse.ArgumentParser(description="Reverse engineer any website")
    parser.add_argument("url", help="URL to analyze")
    parser.add_argument("--output", "-o", default=None, help="Output report path")
    parser.add_argument("--no-interact", action="store_true", help="Skip interaction probing")
    parser.add_argument("--browser", "-b", type=int, default=None, help="Force CDP port")
    parser.add_argument("--json", action="store_true", help="Also save raw JSON data")
    args = parser.parse_args()

    url = args.url
    if not url.startswith("http"):
        url = "https://" + url

    from urllib.parse import urlparse
    domain = urlparse(url).netloc

    # ── Step 1: Detect browsers ──
    print(f"\n{'='*60}")
    print(f"STEP 1: Detecting browsers")
    print(f"{'='*60}")
    sys.stdout.flush()

    browsers = discover_browsers()
    print(get_browser_summary(browsers))
    sys.stdout.flush()

    if args.browser:
        port = args.browser
    elif browsers:
        best = pick_best_browser(browsers, domain)
        port = best.port
    else:
        print("\n[re] No browsers found! Start Chrome with:")
        print("  google-chrome --remote-debugging-port=9222")
        sys.exit(1)

    print(f"\n[re] Using port: {port}")
    sys.stdout.flush()

    # ── Step 2: Snapshot + Screenshots + Interactions ──
    print(f"\n{'='*60}")
    print(f"STEP 2: Analyzing {domain}")
    print(f"{'='*60}")
    sys.stdout.flush()

    t0 = time.time()
    analysis = analyze_page(url, probe_interactions=not args.no_interact)
    elapsed = time.time() - t0

    # Summary
    dom = analysis.get("dom", {})
    counts = dom.get("element_counts", {})
    net = analysis.get("network_calls", [])
    inter = analysis.get("interactions", [])

    print(f"\n{'='*60}")
    print(f"RESULTS ({elapsed:.0f}s)")
    print(f"{'='*60}")
    print(f"  Title:    {dom.get('title', '?')}")
    print(f"  Buttons:  {counts.get('buttons', 0)}")
    print(f"  Links:    {counts.get('links', 0)}")
    print(f"  Images:   {counts.get('images', 0)}")
    print(f"  Network calls: {len(net)}")
    print(f"  Interactions probed: {len(inter)}")
    print(f"  Screenshots: {len([v for v in analysis.get('screenshots', {}).values() if v])}")
    sys.stdout.flush()

    # ── Step 3: Generate report ──
    print(f"\n{'='*60}")
    print(f"STEP 3: Generating report")
    print(f"{'='*60}")
    sys.stdout.flush()

    report = generate_report(analysis)

    if args.output:
        output_path = args.output
    else:
        output_dir = os.path.join(os.path.dirname(__file__), "output")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{domain.replace('.', '_')}.md")

    save_report(report, output_path)

    if args.json:
        json_path = output_path.rsplit(".", 1)[0] + ".json"
        with open(json_path, "w") as f:
            json.dump(analysis, f, indent=2, default=str)
        print(f"[re] JSON saved to {json_path}")

    print(f"\nDONE: {output_path}")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
