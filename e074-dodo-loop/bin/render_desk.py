#!/usr/bin/env python3
"""Rebuild desk.html from ledger + latest check. Stdlib only."""
import json, pathlib, html, datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data" / "ledger.jsonl"
rows = []
if LEDGER.exists():
    for line in LEDGER.read_text().splitlines():
        try: rows.append(json.loads(line))
        except Exception: pass

last = rows[-1] if rows else None
total_iters = len(rows)
total_actions = sum(r.get("actions", 0) for r in rows)
total_bytes = sum(r.get("bytes_changed", 0) for r in rows)
# spend proxy: 1 action ~= 2k tokens, 1KB changed ~= 0.5k tokens. Honest label: PROXY.
proxy_tokens = total_actions * 2000 + int(total_bytes / 1024 * 500)

def esc(s): return html.escape(str(s))

check_rows = ""
if last and last.get("detail", {}).get("checks"):
    for c in last["detail"]["checks"]:
        dot = "✅" if c["ok"] else "❌"
        check_rows += f"<tr><td>{dot}</td><td>{esc(c['name'])}</td><td>{esc(c['detail'])}</td></tr>\n"

hist_rows = ""
for r in reversed(rows[-20:]):
    d = r.get("detail", {})
    hist_rows += f"<tr><td>{esc(r.get('iter'))}</td><td>{esc(r.get('ts',''))}</td><td>{esc(r.get('result'))}</td><td>{d.get('passed','')}/{d.get('total','')}</td><td>{esc(r.get('actions'))}</td><td>{esc(r.get('note',''))}</td></tr>\n"

stage_rows = ""
if last and last.get("detail", {}).get("stages"):
    for s in last["detail"]["stages"]:
        dot = "✅" if s["ok"] else "⏳"
        stage_rows += f"<tr><td>{dot}</td><td>Stage {s['stage']}: {esc(s['name'])}</td><td>{esc(s['state'])}</td></tr>\n"
gates = ""
if last:
    ready = last.get("detail", {}).get("ready", False)
    gates += f"<tr><td>Product data (agent)</td><td>{'SUBMITTABLE — all 4 stages pass' if ready else 'DRAFT — do NOT submit to Dodo yet'}</td><td>data/product-packet.json</td></tr>\n"
    gates += "<tr><td>Persona KYC (you)</td><td>LOCKED until SUBMITTABLE — I tell you when</td><td>Dodo Dashboard &gt; Verification</td></tr>\n"
    gates += "<tr><td>Bank IBAN (you)</td><td>LOCKED until SUBMITTABLE — name must match ID</td><td>Dodo Dashboard &gt; Verification</td></tr>\n"

now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
gate_passed = last.get("detail", {}).get("passed", 0) if last else 0
gate_total = last.get("detail", {}).get("total", 0) if last else 0
gate_ready = last.get("detail", {}).get("ready", False) if last else False
gate_label = f"{gate_passed}/{gate_total}" if last else "—"
gate_state = "READY ✅" if gate_ready else "WORKING 🔧"
desk = f"""<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>e074 desk — Dodo Loop</title>
<style>body{{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ccc;padding:.35rem .5rem;font-size:.85rem;text-align:left}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:.6rem;margin:1rem 0}}.card{{border:1px solid #ccc;padding:.6rem;border-radius:8px}}.card b{{font-size:1.2rem}}small{{color:#666}}a{{color:#06c}}</style></head><body>
<div id=live style="padding:.7rem 1rem;border-radius:10px;font-weight:600;background:#fff3cd;border:1px solid #e6c200">… connecting to loop …</div>
<h1>e074 — Dodo Loop desk</h1><small>rendered {now} · watch this page, not the chat · live parts update without reload</small>
<script>
let lastIter = {total_iters};
async function poll(){{
  try{{
    const r = await fetch('data/heartbeat.json?x='+Date.now(), {{cache:'no-store'}});
    const h = await r.json();
    const age = Math.max(0, Math.round((Date.now() - Date.parse(h.ts))/1000));
    const alive = age < 60;
    document.getElementById('live').style.background = alive ? '#d4edda' : '#f8d7da';
    document.getElementById('live').style.borderColor = alive ? '#28a745' : '#dc3545';
    document.getElementById('live').textContent = (alive ? '🟢 WORKING' : '🔴 STALLED') + ' — Stage ' + h.stage + ' — ' + h.task + ' — tick ' + age + 's ago (iter ' + h.iter + ') — you do: ' + h.you_do;
    if (h.iter !== lastIter) location.reload();
  }}catch(e){{
    document.getElementById('live').textContent = '⚪ CONNECTING — fetching heartbeat… (if this persists, ticker is down)';
  }}
}}
async function feed(){{
  try{{
    const r = await fetch('data/activity.jsonl?x='+Date.now(), {{cache:'no-store'}});
    const t = await r.text();
    const lines = t.trim().split('\n').slice(-15).reverse();
    document.getElementById('feed').innerHTML = lines.map(l => {{
      try{{ const a = JSON.parse(l); return '<div>• <b>'+a.actor+'</b> '+a.action+' — '+a.detail+' <small>'+a.ts+'</small></div>'; }}
      catch(e){{ return '<div>'+l+'</div>'; }}
    }}).join('');
  }}catch(e){{}}
}}
setInterval(poll, 5000); poll();
setInterval(feed, 5000); feed();
</script>
<div class=cards>
<div class=card><div>PULSE</div><b>{'🟢 LIVE' if rows else '⚪ IDLE'}</b><br><small>iters {total_iters} · last {esc(last.get('ts','—') if last else '—')}</small></div>
<div class=card><div>SPEND (proxy)</div><b>~{proxy_tokens:,} tok</b><br><small>{total_actions} actions · {total_bytes:,} bytes changed · proxy, not billing</small></div>
<div class=card><div>DODO GATE</div><b>{gate_label}</b><br><small>{gate_state}</small></div>
<div class=card><div>SITE</div><b><a href="site/index.html">open site</a></b><br><small><a href="site/pricing.html">pricing</a> · packet: data/product-packet.json</small></div>
</div>
<h2>Live work — real agent actions (no proxy)</h2><div id=feed style="background:#111;color:#0f0;padding:.7rem;border-radius:8px;font-family:monospace;font-size:.8rem">… waiting for activity …</div><p><small>Every write/edit/bash by owner + builder lands here with timestamp. Proxy token card below is estimate only — this feed is truth. Full transcripts: ask in chat for session <code>01a0d4e7</code>.</small></p>\n<h2>Plan — where we are</h2><table><tr><th></th><th>Stage</th><th>State</th></tr>{stage_rows}</table><p><small>Stage 1 mechanical only is NOT submittable. You should wait until Stage 4 says SUBMITTABLE. No action from you until then.</small></p>\n<h2>Human gates</h2><table><tr><th>Gate</th><th>State</th><th>Where</th></tr>{gates}</table>
<h2>Dodo checklist (latest)</h2><table><tr><th></th><th>Check</th><th>Detail</th></tr>{check_rows}</table>
<h2>Iterations (newest first)</h2><table><tr><th>#</th><th>Time</th><th>Result</th><th>Gate</th><th>Actions</th><th>Note</th></tr>{hist_rows}</table>
<h2>Explore</h2><nav><a href="site/index.html">Site home</a> · <a href="site/pricing.html">Pricing</a> · <a href="site/terms.html">Terms</a> · <a href="site/privacy.html">Privacy</a> · <a href="site/refunds.html">Refunds</a> · <a href="site/contact.html">Contact</a> · <a href="data/product-packet.json">product-packet.json</a> · <a href="data/ledger.jsonl">ledger.jsonl</a> · <a href="log/loop.log">loop.log</a> · <a href="AGENTS.md">AGENTS.md</a> · <a href="desk.html">desk (same as this page)</a></nav><p><a href="./">← back to hub</a> · every page links back here.</p>\n<h2>Site preview (live)</h2><iframe src="site/index.html" style="width:100%;height:480px;border:1px solid #ccc;border-radius:8px"></iframe>\n<h2>How to advance</h2><p><code>bash bin/loop.sh</code> from <code>e074-dodo-loop/</code>. Each run appends one ledger row and re-renders this page.</p>\n</body></html>"""
(ROOT / "desk.html").write_text(desk)
(ROOT / "index.html").write_text(desk)
print("desk.html + index.html rendered")
