"""Reporter — Clean Markdown report from exploration."""
import sys
from datetime import datetime


def generate_report(results):
    url = results.get("url", "")
    interactions = results.get("interactions", [])
    all_endpoints = results.get("all_endpoints", [])
    out_dir = results.get("output_dir", "")

    lines = []
    lines.append(f"# {results.get('domain', '')} — API Map\n")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # All unique endpoints
    lines.append(f"## All Endpoints ({len(all_endpoints)} unique)\n")
    lines.append("| Method | URL |")
    lines.append("|--------|-----|")
    for ep in sorted(all_endpoints):
        parts = ep.split(" ", 1)
        method = parts[0]
        url_short = parts[1][:70] + ("..." if len(parts[1]) > 70 else "")
        lines.append(f"| {method} | `{url_short}` |")

    # Per-page breakdown
    lines.append(f"\n## Pages ({len(interactions)} explored)\n")
    for r in interactions:
        if not r.get("page_changed"):
            continue
        lines.append(f"### {r['nav_text']}\n")
        lines.append(f"- **URL**: `{r['url']}`")
        eps = r.get("endpoints", [])
        if eps:
            lines.append(f"- **Endpoints**: {len(eps)}\n")
            lines.append("| Method | Auth | URL |")
            lines.append("|--------|------|-----|")
            for ep in eps:
                auth = "Yes" if ep.get("auth") else ""
                url_short = ep["url"][:65] + ("..." if len(ep["url"]) > 65 else "")
                lines.append(f"| {ep['method']} | {auth} | `{url_short}` |")
        else:
            lines.append("- No API calls\n")
        lines.append("")

    # HAR files
    lines.append("## HAR Files\n")
    lines.append("Each HAR file contains the full request/response for that interaction.\n")
    lines.append("```")
    for r in interactions:
        name = r.get("har_path", "").split("/")[-1]
        eps = r.get("unique_endpoints", 0)
        lines.append(f"  {name:40s} ({eps} endpoints)")
    lines.append("```")

    return "\n".join(lines)


def save_report(report, output_path):
    with open(output_path, "w") as f:
        f.write(report)
    print(f"[report] Saved: {output_path} ({len(report)} bytes)")
    sys.stdout.flush()
