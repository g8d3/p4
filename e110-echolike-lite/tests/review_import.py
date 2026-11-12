"""Import: walking an old likes list, without a schedule.

The importer is the one deliberate button in the product. This test builds a list
that only grows when it is scrolled (like X's), runs the walk against it, and
checks what really matters: it stops at the requested count, it dedupes, it hands
the items to the background in batches, and it never runs by itself.
"""
import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent
CONTENT = (ROOT.parent / "extension" / "content.js").read_text()
failures = []


def check(name, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + name + ": " + repr(got))
    if not ok:
        failures.append(name)


# A page shaped like a likes timeline: tweets are added as the scroller nears the end.
FIXTURE = """<!doctype html><html><body>
<div id="scroller" style="height:150px;overflow:auto;border:1px solid #ccc">
  <div id="feed"></div>
</div>
<script>
  window.__batch = [];
  window.__progress = [];
  window.__total = 0;
  const N = 120;
  function add(n) {
    const feed = document.getElementById('feed');
    for (let i = 0; i < n && window.__total < N; i++) {
      window.__total++;
      const id = String(1000 + window.__total);
      const art = document.createElement('article');
      art.setAttribute('data-testid', 'tweet');
      art.innerHTML =
        '<div data-testid="tweetText">old like ' + window.__total + '</div>' +
        '<a href="/someone/status/' + id + '"><time datetime="2026-11-01T10:00:00Z">10:00</time></a>' +
        '<div role="group"><button data-testid="like">1</button></div>';
      feed.appendChild(art);
    }
  }
  add(6);
  // Slow like the real thing: one batch arrives 3 s late (longer than a quiet tick),
  // which is exactly how the first attempt finished with 2 of 100.
  let slow = true;
  const sc = document.getElementById('scroller');
  sc.addEventListener('scroll', () => {
    if (sc.scrollTop + sc.clientHeight > sc.scrollHeight - 50) {
      if (slow) { slow = false; setTimeout(() => add(6), 3000); }
      else setTimeout(() => add(6), 30);
    }
  });
  window.chrome = {
    runtime: {
      lastError: null,
      sendMessage: (m, cb) => {
        if (m.type === 'capture-batch') { window.__batch.push(...m.items); cb && cb({ ok: true, added: m.items.length }); return Promise.resolve({ ok: true }); }
        if (m.type === 'hello' || m.type === 'net-online') return Promise.resolve({ ok: true });
        cb && cb({ sent: true });
        return Promise.resolve({ sent: true });
      },
      onMessage: { addListener: (fn) => { window.__importListener = fn; } },
    },
    storage: {
      local: {
        get: (d, cb) => { cb && cb(Object.assign({}, d, { hide_ads: false })); return Promise.resolve(d); },
        set: (o, cb) => { window.__progress.push(o.import_progress); cb && cb(); return Promise.resolve(); },
      },
      onChanged: { addListener: () => {} },
    },
  };
</script>
</body></html>"""

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.set_content(FIXTURE)
    page.add_script_tag(content=CONTENT)
    page.wait_for_timeout(200)

    check("no import runs by itself", page.evaluate("window.__batch.length"), 0)

    started = page.evaluate("""() => new Promise((resolve) => {
        const l = window.__importListener;
        l({type:'import-start', mode:'likes', limit:30}, null, resolve);
      })""")
    check("import started", started.get("ok"), True)
    page.wait_for_timeout(20000)

    collected = page.evaluate("window.__batch.length")
    check("it waited out a 3s stall and stopped at the count", collected, 30)
    check("it scrolled the list itself", page.evaluate("document.getElementById('scroller').scrollTop > 0"), True)
    ids = page.evaluate("window.__batch.map(i => i.id)")
    check("no duplicates", len(ids), len(set(ids)))
    check("kinds are likes", page.evaluate("new Set(window.__batch.map(i => i.kind)).size"), 1)
    check("it kept the post text", page.evaluate("window.__batch[0].text.startsWith('old like')"), True)
    done = page.evaluate("window.__progress.filter(p => p && p.state === 'done').pop()")
    check("progress reports the end", bool(done), True)
    check("and how many it collected", done.get("collected") if done else None, 30)

    # Running it again from the same DOM must not re-send what it already has:
    # dedupe happens in the background, so here we only check it can restart.
    again = page.evaluate("""() => new Promise((resolve) => {
        const l = window.__importListener;
        l({type:'import-start', mode:'likes', limit:5}, null, resolve);
      })""")
    check("a second import can start", again.get("ok"), True)
    page.wait_for_timeout(4000)
    cancel = page.evaluate("""() => new Promise((resolve) => {
        const l = window.__importListener;
        l({type:'import-cancel'}, null, resolve);
      })""")
    check("cancel answers", cancel.get("ok"), True)
    browser.close()

print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
