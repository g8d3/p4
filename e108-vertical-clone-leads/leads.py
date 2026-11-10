#!/usr/bin/env python3
"""e108 — vertical clone leads: the angry-customer list, from sources we can actually read.

Turning a 1-star review into a lead only needs three things about a business:
it already pays for bloated vertical SaaS, it hates the vendor, and its staff use
three workflows. Reviews give (2) and the workflow words; the vendor+vertical give (1);
the business identity is the part reviews withhold, so this tool names what it can
and never invents what it cannot ("unknown stays empty", ESTANDAR rule).

Source: Trustpilot review pages through a real Chrome (agent-browser), because
G2 answers a bot challenge and Trustpilot answers a page. Nothing is hardcoded:
verticals, URLs, signals, offer numbers all live in config.json.

Usage:
  python3 leads.py                 # all verticals in config.json
  python3 leads.py servicetitan    # only these (by name)
  python3 leads.py --sheet         # rebuild data/leads.md from the newest jsonl
"""
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CFG = json.loads((ROOT / "config.json").read_text())
DATA = ROOT / "data"

EXTRACT = r"""JSON.stringify([...document.querySelectorAll('article')].map(a=>a.innerText))"""


def browser(*args, timeout=90):
    return subprocess.run(["agent-browser", *args], capture_output=True, text=True,
                          timeout=timeout).stdout.strip()


def scrape(vertical, stars):
    url = vertical["trustpilot"] + ("?stars=%d" % stars)
    browser("open", url)
    # the review list is client-rendered: wait for it instead of crying "no leads"
    for _ in range(8):
        n = browser("eval", "document.querySelectorAll('article').length")
        if n.strip('"').isdigit() and int(n.strip('"')) > 0:
            break
        time.sleep(1)
    raw = browser("eval", EXTRACT)
    try:
        rows = json.loads(json.loads(raw)) if raw.startswith('"') else json.loads(raw)
    except Exception:
        rows = []
    out = []
    for text in rows:
        out.append(parse(vertical, text, stars))
    return [r for r in out if r]


DATE = re.compile(r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},\s+\d{4}|\d+\s+(?:hour|day|week|month)s?\s+ago)")
BUSINESS = re.compile(
    r"((?:[A-Z][\w&'.-]+\s+){0,3}[A-Z][\w&'.-]*\s+"
    r"(?:Heating|Air|Plumbing|Electric(?:al)?|Mechanical|HVAC|Roofing|Dental|Med ?Spa|"
    r"Salon|Studio|Gym|Fitness|Pools?|Freight|Logistics|Law|Clinic))")


def fresh(when):
    """A lead we cannot date is a lead we cannot rank; a lead from 2021 is a museum piece."""
    months = CFG.get("max_age_months", 18)
    m = re.match(r"(\d+)\s+(hour|day|week|month)", when or "")
    if m:
        n, unit = int(m.group(1)), m.group(2)
        return n <= {"hour": 24, "day": months * 31, "week": months * 5, "month": months}[unit]
    try:
        from datetime import datetime as _dt
        d = _dt.strptime(when, "%b %d, %Y")
        return (datetime.now() - d).days <= months * 31
    except Exception:
        return False


def parse(vertical, text, stars):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines:
        return None
    body = text.replace("\n", " ")
    # reviewer name is the first line; Trustpilot repeats the star row twice for rated posts
    name = lines[0]
    stars_found = text.count("\u2605")
    rating = stars_found // 2 if stars_found else stars
    m = DATE.search(body)
    when = m.group(1) if m else ""
    pain = [s for s in CFG["signals"] if any(k.lower() in body.lower() for k in s["any"])]
    if not pain or not fresh(when):
        return None
    biz = BUSINESS.search(body)
    return {
        "vertical": vertical["name"],
        "vendor": vertical["vendor"],
        "reviewer": name,
        "business": biz.group(1) if biz else "",  # unknown stays empty, never guessed
        "country": next((l for l in lines[1:4] if len(l) == 2 and l.isupper()), ""),
        "when": when,
        "rating": rating,
        "pains": [s["id"] for s in pain],
        "rebuild": sorted({w for s in pain for w in s["rebuild"]}),
        "quote": body[:400],
        "source": vertical["trustpilot"] + "?stars=%d" % stars,
        "seen": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def score(lead):
    return len(lead["pains"]) * 10 + len(lead["rebuild"]) * 5 + (5 if lead["rating"] == 1 else 0)


def sheet(rows):
    offer = CFG["offer"]
    price_rows = (
        ["| one-time build | $%s |" % offer["price"],
         "| deposit | $%s |" % offer["deposit"]]
        if offer.get("price") else
        ["| pricing | at cost (%s) |" % offer["pricing"],
         "| network fee | %.0f%% of measured cost |" % (offer["network_fee"] * 100)]
    )
    lines = [
        "# Vertical clone leads",
        "",
        "One line each: who is angry, at what, and which of the three workflows their staff ",
        "actually use we would rebuild. Business identity is **unknown** unless the review ",
        "names it — nothing here is guessed.",
        "",
        "## Offer (from config.json)",
        "",
        "| | |",
        "|---|---|",
        *price_rows,
        "| dev cost to us | $%s |" % offer["dev_cost"],
        "| what replaces | %s |" % offer["replaces"],
        "| workflows rebuilt | %s |" % ", ".join(offer["workflows"]),
        "",
        "## Leads, by score",
        "",
    ]
    seen = set()
    for r in sorted(rows, key=score, reverse=True):
        key = (r["vertical"], r["reviewer"], r["quote"][:80])
        if key in seen:
            continue
        seen.add(key)
        lines += [
            "### %s · %s%s — score %d" % (r["vertical"], r["reviewer"],
                                          " (%s)" % r["country"] if r["country"] else "", score(r)),
            "",
            "- vendor: %s · %s stars · %s" % (r["vendor"], r["rating"], r["when"] or "date unknown"),
            "- business: %s" % (r.get("business") or "unknown (review does not name it)"),
            "- pains: %s" % ", ".join(r["pains"]),
            "- rebuild: %s" % ", ".join(r["rebuild"]),
            "- says: «%s»" % r["quote"].replace("|", "/"),
            "- source: %s" % r["source"],
            "",
        ]
    lines += ["## Counts", ""]
    by_v = {}
    for r in rows:
        by_v[r["vertical"]] = by_v.get(r["vertical"], 0) + 1
    for v, n in sorted(by_v.items(), key=lambda kv: -kv[1]):
        lines.append("- %s: %d" % (v, n))
    return "\n".join(lines) + "\n"


def main(argv):
    DATA.mkdir(exist_ok=True)
    if "--sheet" in argv:
        newest = sorted(DATA.glob("leads-*.jsonl"))[-1]
        rows = [json.loads(l) for l in newest.read_text().splitlines() if l.strip()]
        (DATA / "leads.md").write_text(sheet(rows))
        print("sheet: %s (%d leads)" % (DATA / "leads.md", len(rows)))
        return
    wanted = [a for a in argv if not a.startswith("-")]
    verticals = [v for v in CFG["verticals"] if not wanted or v["name"] in wanted]
    rows = []
    for v in verticals:
        for stars in (1, 2):
            got = scrape(v, stars)
            rows += got
            print("%-16s %d stars: %d leads" % (v["name"], stars, len(got)))
            time.sleep(1)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out = DATA / ("leads-%s.jsonl" % stamp)
    with out.open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    (DATA / "leads.md").write_text(sheet(rows))
    print("wrote %s (%d leads) + %s" % (out, len(rows), DATA / "leads.md"))


if __name__ == "__main__":
    main(sys.argv[1:])
