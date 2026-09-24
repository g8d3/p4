#!/usr/bin/env python3
"""Dodo readiness gate. Checks site vs product-packet. Appends nothing; prints JSON."""
import json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
PACKET = json.loads((ROOT / "data" / "product-packet.json").read_text())

REQUIRED_PAGES = ["index.html", "pricing.html", "terms.html", "privacy.html", "refunds.html", "contact.html"]
FOOTER_LINKS = ["pricing.html", "terms.html", "privacy.html", "refunds.html", "contact.html"]

checks = []
def check(name, ok, detail=""):
    checks.append({"name": name, "ok": bool(ok), "detail": detail})

for p in REQUIRED_PAGES:
    check(f"page:{p}", (SITE / p).exists(), "exists" if (SITE / p).exists() else "MISSING")

index = (SITE / "index.html").read_text() if (SITE / "index.html").exists() else ""
pricing = (SITE / "pricing.html").read_text() if (SITE / "pricing.html").exists() else ""

for link in FOOTER_LINKS:
    check(f"footer-link:{link} on index", link in index, "found" if link in index else "missing from index footer")
    check(f"footer-link:{link} on pricing", link in pricing, "found" if link in pricing else "missing from pricing footer")

check("pricing:amount visible", "$6" in pricing and "$49" in pricing, "Pro $6/mo + $49 lifetime" if "$6" in pricing else "price missing")
check("pricing:interval visible", "mo" in pricing.lower() and ("lifetime" in pricing.lower() or "one-time" in pricing.lower()), "interval stated")
check("product:description on index", PACKET["description"][:20] in index, "packet description matches site" if PACKET["description"][:20] in index else "MISMATCH site vs packet")
check("contact:route visible", "support@" in index or "support@" in (SITE / "contact.html").read_text() if (SITE / "contact.html").exists() else False, "support email present")
check("refunds:policy visible", "refund" in (SITE / "refunds.html").read_text().lower() if (SITE / "refunds.html").exists() else False, "refund policy present")

mechanical_passed = sum(1 for c in checks if c["ok"])
mechanical_total = len(checks)

# Stage gates: mechanical is not enough. Seriousness is required.
# Stage 2 functional: real extraction, no fake demo
stage2 = []
has_real_extract = ("pdf.js" in index.lower() or "pdfjs" in index.lower()) and ("demo:" not in index.lower() and "demo runs locally" not in index.lower())
stage2.append({"name": "stage2:real-extraction", "ok": has_real_extract, "detail": "client-side PDF text extraction works" if has_real_extract else "demo button is fake — needs real pdf.js extraction"})
has_sample = (SITE / "sample.pdf").exists() or ("sample" in index.lower() and ".pdf" in index.lower())
stage2.append({"name": "stage2:sample-file", "ok": has_sample, "detail": "sample PDF present" if has_sample else "no sample file to try"})
# Stage 3 trust: about, how-it-works, real domain, non-template look
stage3 = []
stage3.append({"name": "stage3:about-page", "ok": (SITE / "about.html").exists(), "detail": "about/founder page" if (SITE / "about.html").exists() else "MISSING about/founder page"})
stage3.append({"name": "stage3:how-page", "ok": (SITE / "how.html").exists(), "detail": "how-it-works with screenshots" if (SITE / "how.html").exists() else "MISSING how-it-works"})
uses_example = "example.com" in index.lower()
stage3.append({"name": "stage3:real-domain-contact", "ok": not uses_example, "detail": "contact uses real domain" if not uses_example else "still on example.com — not submittable"})
# Stage 4 reviewer: only passes when 1-3 all pass
stage1_ok = mechanical_passed == mechanical_total
stage2_ok = all(c["ok"] for c in stage2)
stage3_ok = all(c["ok"] for c in stage3)
all_checks = checks + stage2 + stage3
passed = sum(1 for c in all_checks if c["ok"])
total = len(all_checks)
stages = [
  {"stage": 1, "name": "Mechanical (footer/pricing/legal)", "ok": stage1_ok, "state": "DONE" if stage1_ok else "WORKING"},
  {"stage": 2, "name": "Functional (real product works)", "ok": stage2_ok, "state": "DONE" if stage2_ok else "PENDING"},
  {"stage": 3, "name": "Trust (about/docs/brand/domain)", "ok": stage3_ok, "state": "DONE" if stage3_ok else "PENDING"},
  {"stage": 4, "name": "Reviewer (would Dodo approve?)", "ok": stage1_ok and stage2_ok and stage3_ok, "state": "SUBMITTABLE" if (stage1_ok and stage2_ok and stage3_ok) else "DO-NOT-SUBMIT"},
]
result = {"passed": passed, "total": total, "ready": stage1_ok and stage2_ok and stage3_ok, "stages": stages, "checks": all_checks, "packet": PACKET}
print(json.dumps(result, indent=2))
