/* e070 tribe v0: landing + referral leaderboard. Static HTML served by Worker, KV-backed.
   GET /                  -> landing (reads ?ref=, shows board)
   GET /join?code=X&ref=Y -> join + credit referrer (JSON)
   GET /board             -> top 20 (JSON) */
const LANDING = `<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>The First 100 — weekly trading tribe</title>
<style>body{font-family:system-ui;max-width:640px;margin:0 auto;padding:20px;line-height:1.5;color:#1c1a15;background:#f6f4ee}
.card{background:#fff;border:1px solid #e6e1d4;border-radius:14px;padding:16px;margin-bottom:12px}
h1{font-size:26px;margin:0 0 4px}.mut{color:#6f6a5c}.big{font-size:22px;font-weight:700}
input,button{font-size:16px;padding:8px 12px;border-radius:8px;border:1px solid #ccc}
button{background:#1c1a15;color:#fff;border:none;cursor:pointer}
table{width:100%;border-collapse:collapse;font-size:14px}
td{border-bottom:1px solid #eee;padding:6px 2px}</style></head><body>
<h1>The First 100</h1>
<p class=mut>A weekly tribe for funding-rate alerts. Free forever for founders. Every Friday the top 3 inviters split <b>$10 USDC</b> — paid on-chain, posted here.</p>
<div class=card><b>How it works</b><br>1. Claim your code below.<br>2. Invite with your link <span class=mut>(?ref=YOURCODE)</span> — each join on your link = 2 points.<br>3. Top 3 each Friday split $10 USDC (5 / 3 / 2).</div>
<div class=card><b>Claim your code</b><br><br><input id=c placeholder=yourcode maxlength=16> <input id=r placeholder="invited by (optional)" maxlength=16> <button id=j>Join</button> <span id=m class=mut></span></div>
<div class=card><b>Leaderboard</b><table id=b><tr><td class=mut>···</td></tr></table></div>
<div class=card class=mut>Week 0 — board is empty. Founders take it all. Payouts every Friday, verifiable on Arbitrum.</div>
<script>
const q=new URLSearchParams(location.search);
if(q.get('ref'))document.getElementById('r').value=q.get('ref');
async function board(){try{const r=await fetch('/board');const d=await r.json();
document.getElementById('b').innerHTML=d.length?d.map((x,i)=>'<tr><td>'+(i+1)+'</td><td><b>'+x.code+'</b></td><td>'+x.points+' pts</td></tr>').join(''):'<tr><td class=mut>Empty — you could be #1.</td></tr>'}catch(e){}}
document.getElementById('j').onclick=async()=>{const c=document.getElementById('c').value.trim().toLowerCase();const r=document.getElementById('r').value.trim().toLowerCase();
const m=document.getElementById('m');m.textContent='···';
try{const q2=await fetch('/join?code='+encodeURIComponent(c)+'&ref='+encodeURIComponent(r));const j=await q2.json();
m.textContent=j.ok?('In! Your link: '+location.origin+location.pathname+'?ref='+c):('('+(j.error||'no')+')');board()}catch(e){m.textContent='(network?)'}};
board();
</script></body></html>`;

const ok = (o) => new Response(JSON.stringify(o), { headers: { 'Content-Type': 'application/json' } });

async function handle(req, env) {
  const REFS = env.REFS;
  const u = new URL(req.url);
  if (u.pathname === '/board') {
    const list = await REFS.list();
    const rows = [];
    for (const k of list.keys.slice(0, 60)) {
      const v = await REFS.get(k.name, 'json');
      if (v) rows.push(v);
    }
    rows.sort((a, b) => b.points - a.points);
    return ok(rows.slice(0, 20).map((v) => ({ code: v.code, points: v.points })));
  }
  if (u.pathname === '/join') {
    const code = (u.searchParams.get('code') || '').toLowerCase().replace(/[^a-z0-9]/g, '').slice(0, 16);
    const ref = (u.searchParams.get('ref') || '').toLowerCase().replace(/[^a-z0-9]/g, '').slice(0, 16);
    if (code.length < 3) return ok({ ok: false, error: 'code needs 3+ letters/numbers' });
    if (await REFS.get('m:' + code)) return ok({ ok: false, error: 'code taken — pick another' });
    await REFS.put('m:' + code, JSON.stringify({ code, points: 1, ts: Date.now() }));
    if (ref && ref !== code) {
      const r = await REFS.get('m:' + ref, 'json');
      if (r) { r.points += 2; await REFS.put('m:' + ref, JSON.stringify(r)); }
    }
    return ok({ ok: true });
  }
  return new Response(LANDING, { headers: { 'Content-Type': 'text/html;charset=utf-8' } });
}
export default { fetch: (req, env) => handle(req, env) };
