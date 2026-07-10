"""
Functionalities Discovery — Search Google for site features.

Before analyzing a page, search for what it can do so we know
what to look for and what interactions to probe.
"""

import subprocess
import re
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from browser_manager import connect_to_browser, pick_best_browser, discover_browsers


def ab(*args, timeout=30):
    """Run agent-browser command."""
    cmd = ["agent-browser", "--auto-connect"]
    for arg in args:
        cmd.append(str(arg))
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def ab_eval(js, timeout=15):
    """Run JavaScript via agent-browser eval."""
    _, out, _ = ab("eval", js, timeout=timeout)
    if out.startswith('"') and out.endswith('"'):
        out = out[1:-1]
    return out


def search_google_features(query: str, browser_port: int = 9222) -> list[str]:
    """Search Google for site features and return extracted feature descriptions."""
    print(f"[functionalities] Searching: {query}")

    # Navigate to Google
    ab("open", f"https://www.google.com/search?q={query}", timeout=15)
    import time
    time.sleep(3)

    # Extract search results text
    js = """
    (() => {
        const results = [];
        // Get all search result snippets
        document.querySelectorAll('.g, [data-sokoban-container]').forEach(el => {
            const text = el.innerText.trim();
            if (text.length > 20 && text.length < 500) {
                results.push(text);
            }
        });
        // Also get any featured snippets
        document.querySelectorAll('.kp-blk, .kno-rdesc').forEach(el => {
            const text = el.innerText.trim();
            if (text.length > 20) {
                results.push('FEATURED: ' + text);
            }
        });
        return JSON.stringify(results.slice(0, 10));
    })()
    """
    raw = ab_eval(js, timeout=10)
    try:
        results = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        results = []

    print(f"[functionalities] Found {len(results)} snippets")
    return results


def extract_features_from_results(results: list[str]) -> list[str]:
    """Extract specific feature keywords from search results."""
    features = []

    # Common feature patterns
    feature_patterns = [
        r"generate\s+\w+",
        r"create\s+\w+",
        r"upload\s+\w+",
        r"download\s+\w+",
        r"share\s+\w+",
        r"edit\s+\w+",
        r"customize\s+\w+",
        r"export\s+\w+",
        r"import\s+\w+",
        r"connect\s+\w+",
        r"integrate\s+\w+",
        r"automate\s+\w+",
        r"schedule\s+\w+",
        r"collaborate\s+\w+",
        r"analyze\s+\w+",
        r"track\s+\w+",
        r"manage\s+\w+",
        r"optimize\s+\w+",
        r"transform\s+\w+",
        r"convert\s+\w+",
    ]

    for text in results:
        text_lower = text.lower()
        for pattern in feature_patterns:
            matches = re.findall(pattern, text_lower)
            for m in matches:
                feat = m.strip()
                if feat not in features:
                    features.append(feat)

    return features


def discover_site_functionalities(url: str, browser_port: int = 9222) -> dict:
    """Main entry: discover what a site can do before analyzing it.

    Returns dict with:
      - domain: the site domain
      - search_results: raw Google snippets
      - features: extracted feature keywords
      - summary: human-readable summary
    """
    from urllib.parse import urlparse
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path
    site_name = domain.replace("www.", "").split(".")[0]

    # Search for features
    queries = [
        f"{site_name} features what can you do",
        f"{site_name} tools capabilities",
        f"site:{domain} features",
    ]

    all_results = []
    for q in queries:
        results = search_google_features(q, browser_port)
        all_results.extend(results)

    # Deduplicate
    seen = set()
    unique_results = []
    for r in all_results:
        key = r[:100].lower()
        if key not in seen:
            seen.add(key)
            unique_results.append(r)

    features = extract_features_from_results(unique_results)

    summary_lines = [f"Domain: {domain}"]
    summary_lines.append(f"Search results analyzed: {len(unique_results)}")
    summary_lines.append(f"Features identified: {len(features)}")
    if features:
        summary_lines.append("Features:")
        for f in features[:20]:
            summary_lines.append(f"  - {f}")

    return {
        "domain": domain,
        "site_name": site_name,
        "search_results": unique_results[:15],
        "features": features,
        "summary": "\n".join(summary_lines),
    }


if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://higgsfield.ai"
    info = discover_site_functionalities(url)
    print(f"\n{'='*60}")
    print(info["summary"])
    print(f"{'='*60}")
    print("\nRaw results:")
    for r in info["search_results"][:5]:
        print(f"\n---\n{r[:200]}")
