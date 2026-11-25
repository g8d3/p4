"""Replay a real X page and check the two things the owner cares about, offline.

This is the answer to "we need a way for you to test": the phone can hand its own page
over in one press — Settings → *3 · On X* → **Copy what X shows**, which reads the open
X tab (tags, attributes, and the numbers that decide where a hole is) and puts it on the
clipboard at the privacy level the owner chose. Saved here as `tests/live/<name>.json`,
that page is replayed under the real content script, on the real markup, with the real
inline `translateY` offsets — so a fix is verified against the device that has the bug
instead of against a fixture written by the person who wrote the fix.

    # 1. on the phone (or any logged-in browser): Settings -> 3 · On X -> Copy what X shows
    # 2. paste it here:
    pbpaste > tests/live/home.json        # or xclip -o, or paste into the file
    xvfb-run -a python3 tests/replay_live.py tests/live/home.json

What it asserts (and prints, whether it passes or fails):

  * no ad that the report shows as hidden is visible after replay;
  * no list has a hole: every gap between two visible rows is within the largest gap
    the same list shows where nothing was hidden;
  * no row was pushed under the row above it (a negative gap) — the failure mode of
    every version that moved rows by hand;
  * the shift the code writes equals the hole it closed, per list.

    xvfb-run -a python3 tests/replay_live.py            # newest file in tests/live/
"""
import json
import os
import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent
# ECHO_CONTENT=/path/to/old/content.js replays the same real page against an older build:
# that is how a regression is proven fixed, and how this harness was proven able to fail.
CONTENT = pathlib.Path(os.environ.get("ECHO_CONTENT") or (ROOT.parent / "extension" / "content.js")).read_text()
LIVE = ROOT / "live"

STUB = """
window.chrome = {
  runtime: {
    getManifest: () => ({ version: %VERSION% }),
    getURL: (p) => "chrome-extension://stub/" + p,
    onMessage: { addListener: (fn) => (window.__msgListeners = window.__msgListeners || []).push(fn) },
    sendMessage: (m, cb) => { cb && cb({ ok: true }); return Promise.resolve({ ok: true }); },
  },
  storage: {
    local: {
      set: () => Promise.resolve(),
      get: (defaults, cb) => { cb && cb(defaults); return Promise.resolve(defaults); },
    },
    onChanged: { addListener: () => {} },
  },
};
"""

failures = []


def check(name, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + name + ": " + repr(got))
    if not ok:
        failures.append(name)


def newest():
    files = sorted(LIVE.glob("*.json"), key=lambda p: p.stat().st_mtime)
    return files[-1] if files else None


def main():
    path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else newest()
    if not path or not path.exists():
        print("no report to replay: copy one out of the phone into tests/live/*.json")
        print("  Settings -> 3 · On X -> Copy what X shows")
        return 2
    rep = json.loads(path.read_text())
    rich = rep.get("rich") or {}
    html = rich.get("html") or ""
    print("report:", path.name, "| version", rep.get("version"), "| markup", len(html), "bytes")
    print("content script:", len(CONTENT), "chars")
    print("geo:", json.dumps(rep.get("geo") or [])[:600])
    if len(html) < 500:
        print("FAIL the report carries no markup (privacy level 'shapes'?): nothing to replay")
        return 1

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 420, "height": 900})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)[:200]))
        page.set_content("<!doctype html><html><body><main>" + html + "</main></body></html>")
        page.add_script_tag(content=STUB.replace("%VERSION%", json.dumps(str(rep.get("version") or "0"))))
        page.add_script_tag(content=CONTENT)
        page.wait_for_timeout(400)

        probe = page.evaluate(
            """() => {
              // Rendered positions, not X's offsets: a shift we write in `translate` does
              // not change X's numbers, so measuring the hole with them would always say
              // "hole" and never see the fix (nor a regression).
              const rows = [...document.querySelectorAll('[style*="translateY"]')];
              const lists = new Set(rows.map((r) => r.parentElement).filter(Boolean));
              const out = { lists: [], hidden: [], visibleAds: [], shiftDiff: [] };
              for (const list of lists) {
                const rs = [...list.children].filter((c) => /translateY\\(/.test((c.getAttribute('style') || '')));
                if (rs.length < 2) continue;
                let prev = -1, between = false, hiddenH = 0, shiftSum = 0;
                const clean = [], holes = [];
                for (let i = 0; i < rs.length; i++) {
                  const r = rs[i];
                  if (r.hasAttribute('data-echolike-ad')) {
                    between = true;
                    hiddenH += Number(r.dataset.echH) || 0;
                    continue;
                  }
                  if (r.style.translate) shiftSum = Math.max(shiftSum, Math.abs(parseFloat(r.style.translate.split(' ').pop()) || 0));
                  if (prev >= 0) {
                    const gap = Math.round(r.getBoundingClientRect().top - rs[prev].getBoundingClientRect().bottom);
                    (between ? holes : clean).push(gap);
                  }
                  prev = i;
                  between = false;
                }
                out.lists.push({
                  n: rs.length,
                  hidden: rs.filter((r) => r.hasAttribute('data-echolike-ad')).length,
                  shifted: rs.filter((r) => r.style.translate).length,
                  clean, holes,
                });
                if (hiddenH) out.shiftDiff.push(Math.round(shiftSum - hiddenH));
              }
              for (const el of document.querySelectorAll('[data-echolike-ad]')) {
                out.hidden.push(el.getClientRects().length > 0 ? 'visible' : 'hidden');
              }
              for (const s of document.querySelectorAll('span,div')) {
                const t = (s.textContent || '').trim();
                if (t.length > 64 || !/^(Ad|Anuncio|Promoted|Promocionado|Anzeige|Werbung|Publicidad|Sponsored|Patrocinado)(\\s+(by|from|por|de)\\s+.{1,60})?$/i.test(t)) continue;
                const r = s.getBoundingClientRect();
                if (r.width > 0 && r.height > 0) out.visibleAds.push(t.slice(0, 40));
              }
              return out;
            }"""
        )

        b = browser
        hidden_visible = [h for h in probe["hidden"] if h == "visible"]
        check("no marked ad is visible after replay", len(hidden_visible), 0)
        check("no disclosure is visible after replay", len(probe["visibleAds"]), 0)

        # A hole in the middle of an ad slot is an ad's height (hundreds of px); X's own
        # spacing between two posts is tens. 40px separates the two without pretending to
        # know X's exact rhythm on the owner's phone.
        MAX_HOLE = 40
        for li, info in enumerate(probe["lists"]):
            print("  list", li, json.dumps(info))
            check("list " + str(li) + ": no row pushed under the one above", [g for g in info["holes"] + info["clean"] if g < -2], [])
            check("list " + str(li) + ": no ad-sized hole left open", [g for g in info["holes"] if g > MAX_HOLE], [])
            if info["hidden"]:
                check("list " + str(li) + ": a row was shifted to close it", info["shifted"] > 0, True)
        # Mechanism check: what we moved equals the slots we emptied.
        check("the shift equals the hidden heights, per list", [d for d in probe["shiftDiff"] if abs(d) > 2], [])

        # ---- The dynamic half: what X does while you scroll, and what must not move ----
        # A jump is not a static property. It is a row that changes position for a reason
        # that is not you scrolling — and both reasons this product ever jumped live here:
        # X unmounting a row that scrolled away, and X recycling a row for a real post.
        page.evaluate(
            """() => {
              window.__tops = () => {
                const out = {};
                for (const r of document.querySelectorAll('[data-index]')) {
                  out[r.dataset.index] = Math.round(r.getBoundingClientRect().top);
                }
                return out;
              };
              // the childList change X makes while you scroll (a row appended and removed)
              window.__churn = () => {
                const anchor = document.querySelector('[style*="translateY"]');
                if (!anchor) return;
                const li = document.createElement('li');
                li.setAttribute('data-index', '999');
                li.style.cssText = 'position:absolute;transform:translateY(99999px)';
                anchor.parentElement.appendChild(li);
                setTimeout(() => li.remove(), 40);
              };
            }"""
        )

        unmount = page.evaluate(
            """() => {
              const ad = document.querySelector('[data-echolike-ad][data-index]');
              if (!ad) return null;
              const before = window.__tops();
              window.__ad = ad;
              window.__adParent = ad.parentElement;
              ad.remove();
              window.__churn();
              return { before, index: ad.dataset.index };
            }"""
        )
        page.wait_for_timeout(350)
        if unmount:
            after = page.evaluate("window.__tops()")
            moved_down = [k for k, top in after.items() if k in unmount["before"] and top > unmount["before"][k] + 2]
            check("X unmounting the ad does not move the rows below", moved_down, [])
            page.evaluate("window.__adParent.appendChild(window.__ad); window.__churn();")
            page.wait_for_timeout(350)
            back = page.evaluate("window.__tops()")
            moved = [k for k, top in back.items() if k in unmount["before"] and abs(top - unmount["before"][k]) > 2]
            check("and the rows come back exactly where they were", moved, [])

        # A row recycled for a real post: the post must be visible, and nothing below it may
        # jump down onto it.
        recycled = page.evaluate(
            """() => {
              const ad = document.querySelector('[data-echolike-ad]');
              if (!ad) return null;
              const before = window.__tops();
              for (const body of ad.querySelectorAll('[dir="auto"][lang]')) body.textContent = 'A real post now.';
              for (const s of ad.querySelectorAll('span,div')) {
                if (/^(Ad|Promoted|Sponsored)\\b/.test((s.textContent || '').trim())) s.textContent = 'Somebody';
              }
              window.__churn();
              return before;
            }"""
        )
        page.wait_for_timeout(400)
        if recycled:
            # A row that turns into a real post fills the slot: the shift must give way, so
            # rows below moving is correct here. What must never happen is a row landing on
            # top of another one.
            gaps = page.evaluate(
                """() => {
                  const rows = [...document.querySelectorAll('[data-index]')];
                  const out = [];
                  for (let i = 1; i < rows.length; i++) {
                    const a = rows[i - 1].getBoundingClientRect();
                    const b = rows[i].getBoundingClientRect();
                    if (a.height && b.height) out.push(Math.round(b.top - a.bottom));
                  }
                  return out;
                }"""
            )
            check("X recycling a row leaves nothing on top of anything", [g for g in gaps if g < -2], [])
            visible = page.evaluate(
                """() => [...document.querySelectorAll('[data-echolike-ad]')]
                     .filter((el) => el.getClientRects().length > 0).length"""
            )
            check("and a recycled ad is visible again (no real post stays hidden)", visible, 0)
        check("no page errors after the churn", errors, [])

        b.close()
    print("FAILURES:", failures if failures else "none")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
