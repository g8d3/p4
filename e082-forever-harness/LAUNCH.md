# Launch kit — Forever Harness (e082), first 10 users

Live board (replace if the tailnet IP rotates — see `bash bin/serve.sh` output):

- Public board: `http://100.102.52.59:8342`
- Share page: `http://100.102.52.59:8342/share`
- Proof JSON: `http://100.102.52.59:8342/api/proof`
- LAN: `http://192.168.0.177:8342` · local: `http://127.0.0.1:8342`

> In the copy below, `HARNESS_URL` = the public board URL above.

## X thread (5 posts, copy-paste)

1/ My agent kept dying on long runs — context bloat, silent quality drift,
runaway spend. So I built a keep-going loop: every 60s it ticks
(heartbeat → verify gates → compact → ship one micro-goal) and stops itself
before it can collapse. Live proof: HARNESS_URL/share 🧵

2/ The loop enforces 6 verify gates per tick: policy valid, budget remaining,
heartbeat fresh, diff cap, checkpoint fresh, context budget.
Quality = 100 − 15 × failed gates. Right now mine sits at 100/100.
Raw JSON, no screenshots: HARNESS_URL/api/proof

3/ Install takes <5 min if you already run pi or opencode:
download plugin.zip from the board, paste 3 lines, press Start.
Same policy file drives the server AND your own harness.
HARNESS_URL — click "Download plugin.zip".

4/ What sold me: the budget ledger. Every tick appends real token cost;
the loop refuses to tick when spend ≥ budget. My run so far: pennies,
auditable per cycle. HARNESS_URL/api/ledger

5/ If it works for 10 strangers I'll productize it as an $8–15/mo plugin
(uptime + quality history as the receipt). Try it, break it, tell me which
gate fails first 👇 HARNESS_URL

## Agent-builder community post (opencode Discord #showcase — picked because the plugin ships opencode install + tool snippet natively)

Title: keep-going plugin for opencode — my agent has run 60+ cycles without collapsing

Body:
Hey all — I run a tiny stdlib loop server ("Forever Harness") that keeps an
agent working indefinitely: heartbeat + stuck detection, 6 verify gates per
tick, checkpoints + compaction so context stays flat, a spend ledger with a
hard budget stop. It ships as an opencode plugin (tool snippet + hooks in
`plugin/opencode.json`, skill doc, same policy file as the server).

Install (<5 min): grab `plugin.zip` at HARNESS_URL/download/plugin.zip,
unzip to `~/.config/opencode/keep-going`, set `FOREVER_HARNESS_URL` +
`FOREVER_HARNESS_TOKEN`, then `keep-going.sh tick opencode`.

Live demo of my own loop: HARNESS_URL/share (cycle, quality, version) and
HARNESS_URL/api/proof (uptime, quality history, ledger).
Looking for 10 testers — what breaks first for you?

## IndieHackers / Reddit post (r/SideProject)

Title: I built a loop that keeps my AI agent working forever (heartbeat + verify gates + budget stop) — live proof, roast it?

Body:
Problem: every long agent run I tried died the same way — context bloated,
quality silently drifted, spend ran away while I wasn't looking.

What I built: a ~600-line stdlib Python server + single-file UI + a plugin
for pi/opencode. Configure once, then every 60s it ticks: heartbeat → 6
verify gates → compact old cycles into a rolling summary → ship one
micro-goal → append cost to a ledger. Stop conditions always win: user stop,
budget out, quality floor breach, goal done.

Proof instead of promises (all live):
- Share page: HARNESS_URL/share
- Proof JSON (uptime, cycles shipped, quality history, ledger): HARNESS_URL/api/proof
- Install: HARNESS_URL (Download plugin.zip, 3-line snippet, Start)

Current state: 60+ cycles, quality 100/100, spend $0.15 of a $10 budget.
Plan: if 10 strangers run it, I'll sell it as an $8–15/mo plugin with the
proof page as the receipt.

Ask: run the plugin for a day and tell me which gate fails first, or why you
wouldn't pay for this. Be brutal.

## Directory / community checklist

- [NEEDS OWNER] Post the X thread from the owner account (I have no X credentials).
- [NEEDS OWNER] Post in opencode Discord #showcase (requires a human Discord account; I cannot join/post).
- [NEEDS OWNER] Post in r/SideProject (requires human Reddit account + karma; I cannot post).
- [NEEDS OWNER] Optional: submit to Hacker News "Show HN" once 10 users confirm it works (human account).
- [NEEDS OWNER] Optional: list in pi plugin directory / awesome-opencode list (human PR from owner account).
- [DONE BY AGENT] All links, proof endpoints, share page, download counter live on the board.

## What to measure (and where it shows on the board)

| Metric | Source | Where on the board |
|---|---|---|
| Plugin installs | `GET /download/plugin.zip` hits → `data/stats.json: downloads` | Proof card ("plugin downloads N") + `/api/proof.downloads` |
| Active loops | heartbeat freshness (`heartbeat_age_minutes`, `stuck` flag) | Status card (RUNNING badge, STUCK warning) + `/api/proof.running` |
| Shares / virality | `GET /share` hits → `data/stats.json: share_views` | Proof card ("share views N") + `/api/proof.share_views` |
| Retention proxy | `cycles_shipped`, `quality_history` trend | Proof card + `/api/proof` |
| Spend efficiency | `ledger.used` vs `budget_total` | Status budget bar + Proof card |

Targets for users 1–10: ≥10 downloads, ≥3 loops ticking concurrently
(fresh heartbeats), ≥5 share views, zero 401-spikes in `data/server.log`
(sign of token-confusion), quality_history without floor breaches.
