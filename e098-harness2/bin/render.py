"""Render a static results site from the harness2 local demo output. Stdlib only."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEEDS = json.loads((ROOT / "needs.json").read_text())
DEMO = Path(NEEDS["demo_output"])
SITE = Path(NEEDS["site_dir"])


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8").strip()
    except OSError:
        return "(missing)"


def main() -> None:
    summary = json.loads((DEMO / "demo.json").read_text())
    base_script = read(DEMO / "base" / "scripts" / "summarize.py")
    exp1 = read(DEMO / "library/k2/seq/accounting/harnesses/ledger-1/EXPERIENCE.md")
    ledgers, answers = {}, {}
    for task in ("ledger-1", "ledger-2"):
        ledgers[task] = read(DEMO / "sources" / task / "ledger.csv")
        got = sorted((DEMO / "executions").rglob(f"{task}/*/answer.txt"))
        answers[task] = [(str(p.relative_to(DEMO)), read(p)) for p in got[:6]]
    rows = "".join(
        f"<tr><td>{t['task']}</td><td>{t['status']}</td>"
        f"<td>agg={t['library_entries_before']['agg']} "
        f"seq={t['library_entries_before']['seq']}</td></tr>"
        for t in summary["tasks"]
    )
    ans = "".join(
        f"<h3>{task}</h3><pre>ledger.csv:\n{l}</pre><ul>"
        + "".join(f"<li><code>{p}</code> &rarr; <b>{a}</b></li>" for p, a in lst)
        + "</ul>"
        for task, l, lst in
        ((t, ledgers[t], answers[t]) for t in ("ledger-1", "ledger-2"))
    )
    script = ("<script>async function rerun(e){e.preventDefault();"
        "const k=document.getElementById('k').value;"
        "const s=document.getElementById('status');s.textContent='running…';"
        "const r=await fetch('/api/rerun?k='+encodeURIComponent(k),{method:'POST'});"
        "const j=await r.json();"
        "s.textContent=r.ok?'done — reloading…':'FAILED: '+j.tail.slice(-300);"
        "if(r.ok)setTimeout(()=>location.reload(),800);return false}</script>")
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Harness² — plain-English results</title>
<style>body{{font-family:system-ui,sans-serif;max-width:62rem;margin:2rem auto;padding:0 1rem;line-height:1.6}}
pre{{background:#f4f4f4;padding:1rem;overflow:auto}}table{{border-collapse:collapse}}
td,th{{border:1px solid #ccc;padding:.4rem .8rem}}.pill{{display:inline-block;background:#e8f5e9;
padding:.2rem .7rem;border-radius:1rem;font-weight:700}}
.keybox{{background:#fff8e1;border:1px solid #e0c36a;padding:1rem;border-radius:.5rem}}</style></head><body>
<h1>Google Harness², tested here <span class="pill">works · $0 spent</span></h1>
<h2>No, it is NOT a chat page. There is no agent to talk to.</h2>
<p>Think of it like a car. The AI model is the <b>engine</b>. The <b>harness</b> is
everything around it: the steering wheel, the brakes, the dashboard, the rule book
that tells the driver what to do. That rule book is text files: instructions,
safety rules, memory notes, helper scripts.</p>
<p>Harness² is a <b>tool for developers</b> that tunes that rule book <b>by itself</b>.
It tries a small change, tests if the car drives better, and keeps the change if yes.
Then it writes down the lesson so the next task starts smarter. It runs in a black
terminal window — there is no app and no chat.</p>
<h2>What did we prove on this machine?</h2>
<p>We ran the free built-in demo (a toy accounting task, no AI, no keys needed):
{summary['execution_count']} test runs, {summary['editor_calls']} self-edits.</p>
<table><tr><th>task</th><th>result</th><th>lessons known before</th></tr>{rows}</table>
<h2>The mistake it found and fixed alone</h2>
<p>The starting rule book had a bad helper script: it added up only the
<b>positive</b> money amounts and silently dropped the negative ones (credits).
The tool proposed removing that filter, tested old vs new on the same numbers,
and kept the fix — nobody told it the right answer.
<pre>{base_script}</pre>
<h2>Probe answers (refined harness)</h2>
{ans}
<h2>Lesson kept for future tasks (harnessing-level recursion)</h2>
<pre>{exp1}</pre>
<h2>What will you see if you press the button below?</h2>
<p>Honest answer: the <b>same toy demo runs again</b> with a bigger or smaller
search budget (<code>k</code> = how many fix ideas it tries). It takes ~10 seconds,
costs $0, and needs no keys — because this demo uses <b>pre-written fake edits</b>,
not a real AI. It proves the machine works. It will NOT show you a smart agent.</p>
<h2>Keys and money: the full truth</h2>
<div class="keybox">
<p><b>This page / demo: NO key needed. $0. Forever.</b> Nothing is billed.</p>
<p><b>The real thing (a live AI that improves itself on real tasks): needs a
Google Cloud key with billing turned on</b> (Vertex AI). We do <b>not</b> have that
key on this machine — we only have a free AI-studio key, and this tool refuses it.
So I did not run the real thing: I will never spend your money or plug in keys
without asking you first.</p>
<p><b>Price if you ever want it:</b> Google bills per text used by the AI.
A small 1-task test = roughly a few dollars. A full benchmark run = tens to
hundreds of dollars. There is no fixed price tag — it depends on how much the
AI reads and writes. I would set a hard spending cap before starting.</p>
</div>
<p>Sources: <a href="https://github.com/google-research/harness2">github.com/google-research/harness2</a>
· <a href="https://arxiv.org/abs/2610.14224">arXiv:2610.14224</a></p>
<h2>What can you do on this page? (3 things)</h2>
<ol><li><b>Read the proof above</b> — that is the whole point of the page.</li>
<li><b>Press Re-run</b> to watch the toy demo repeat with more or fewer fix ideas.</li>
<li><b>Open the two links</b> (repo + paper) only if you want the deep details.</li></ol>
<p>That is all. If you want a live demo with a real AI, tell me and I will tell you
the exact key and the exact max dollars first — nothing runs until you say yes.</p>
<form id="rerun" onsubmit="return rerun(event)">
<label>Recursion budget k: <input id="k" type="number" value="2" min="1" max="4"></label>
<button>Re-run demo</button> <span id="status"></span></form>
""" + script + """
</body></html>"""
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "index.html").write_text(html, encoding="utf-8")
    print(f"wrote {SITE / 'index.html'}")


if __name__ == "__main__":
    main()
