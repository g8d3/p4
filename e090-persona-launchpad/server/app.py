import json, os, time, urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEEDS = os.path.join(BASE, "needs.json")
PERSONAS = os.path.join(BASE, "data", "personas.json")
LOGS = os.path.join(BASE, "data", "logs.jsonl")
HOOKS = os.path.join(BASE, "data", "hooks.json")
PUBLIC = os.path.join(BASE, "public")

def load_needs():
    with open(NEEDS) as f: return json.load(f)

def load_personas():
    if not os.path.exists(PERSONAS): return []
    with open(PERSONAS) as f: return json.load(f)

def save_personas(items):
    with open(PERSONAS, "w") as f: json.dump(items, f, indent=2, ensure_ascii=False)

def read_logs(limit=200):
    if not os.path.exists(LOGS): return []
    out = []
    with open(LOGS) as f:
        for line in f:
            line = line.strip()
            if line:
                try: out.append(json.loads(line))
                except: pass
    return out[-limit:]

def append_log(entry):
    entry["ts"] = int(time.time())
    with open(LOGS, "a") as f: f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry

CHAINS = {
  "decision": "Solana first for launches, Base second for hooks moat. ONE app, pluggable chain adapters — never two codebases.",
  "solana": "Viral memecoin home. Pump-style bonding-curve launches cost cents and confirm in <1s; Raydium migration + Jupiter routing are the standard trust path; Meteora DAMM dynamic fees are Solana's closest answer to 'hooks'. Audience is the largest memecoin trader base — perfect for humor personas. No Uniswap v4 hooks (EVM-only), so custom fee-code moat is thinner; moat here is distribution + persona IP.",
  "base": "Programmability home. Clanker (40% creator / 40% interface / 20% protocol on 1% seed-pool fee) + Uniswap v4 custom hooks + Coinbase Wallet distribution. L2-cheap but slower and smaller memecoin crowd than Solana. This is where the hook marketplace + interface-fee business lives — phase 2, researched now via the Hook Directory.",
  "why_not_two_apps": "Two apps = 2x wallets, 2x infra, 2x audits, 2x trust stories, 2x marketing. Instead: chain-agnostic core (personas, scoring, public logs) + thin per-chain launcher adapters + per-chain marketing skin (Solana: speed/fun/low-cost; Base: onchain AI-agent economy).",
  "phase_plan": "Phase 1: Solana launches for both seed personas, score, find winner. Phase 2: winner expands to Base via Clanker interface (collect 40% interface cut). Phase 3: only then consider own contracts, on whichever chain the fees justify it."
}
FUNDS = {
  "launcher": "Clanker v4 on Base (what @contractclaus-style projects use)",
  "liquidity": "Initial LP is single-sided (100B supply into Uniswap pool) and the LP NFT goes to the LpLocker — no withdraw function, locked effectively forever (docs say until year 2100). Neither creator, team, nor Clanker can pull it. That is the 'liquidez bloqueada' — it prevents a classic rug on the seed pool.",
  "fees": "Default 1% swap fee on the seed pool. Split ~40% creator / 60% Clanker (or 40/40/20 when launched via an interface partner). V4 adds static or dynamic-fee hooks + auto-collect into ClankerFeeLocker; anyone can trigger collect, rewards sit claimable per recipient.",
  "goal": "The goal is NOT growing the locked liquidity (it cannot grow/withdraw). The goal is growing VOLUME: 0.4% of every trade on the seed pool accrues to the creator in perpetuity (in both token + paired ETH). More mindshare -> more volume -> more claimable fees to treasury/operations.",
  "interface_play": "We do NOT need our own contracts to earn launchpad money. Deploying via our own interface/frontend sets interfaceRewardRecipient to our treasury: split becomes ~40% persona creator / 40% us (interface) / 20% Clanker. That is the Clankpad model — launchpad revenue with zero audit cost. Own contracts (fork/hook) only make sense after proven volume.",
  "extras": "Vault up to ~30% of supply with min lock (team/community vesting), optional dev-buy at launch (buys after vault), airdrop via merkle root, MEV modules (2-block no-swap delay / descending start fee).",
  "custody": "You own the deployer wallet seed. Agent operates a local keyfile (data/secrets.env, chmod 600) for posting + deploying + claiming. Treasury = fee-recipient address you set at deploy; rotate via updateCreatorRewardRecipient."
}

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _json(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store"); self.send_header("Content-Length", str(len(b))); self.end_headers()
        self.wfile.write(b)
    def do_GET(self):
        p = urllib.parse.urlparse(self.path).path
        if p in ("/", "/index.html"):
            return self._file("index.html", "text/html")
        if p == "/api/personas": return self._json(load_personas())
        if p == "/api/logs": return self._json(read_logs())
        if p == "/api/funds": return self._json(FUNDS)
        if p == "/api/chains": return self._json(CHAINS)
        if p == "/api/hooks":
            try:
                with open(HOOKS) as f: return self._json(json.load(f))
            except Exception as e: return self._json({"error": str(e)}, 500)
        if p == "/api/needs": return self._json(load_needs())
        if p.startswith("/public/"):
            return self._file(p[8:], None)
        self.send_response(404); self.end_headers()
    def _file(self, name, ctype):
        fp = os.path.join(PUBLIC, name.lstrip("/"))
        if not os.path.exists(fp): self.send_response(404); self.end_headers(); return
        with open(fp, "rb") as f: b = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype or ("text/html" if name.endswith(".html") else "application/octet-stream"))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_POST(self):
        p = urllib.parse.urlparse(self.path).path
        n = int(self.headers.get("Content-Length", 0))
        try: body = json.loads(self.rfile.read(n) or b"{}")
        except: body = {}
        if p == "/api/personas":
            items = load_personas()
            body["id"] = body.get("id") or ("p" + str(int(time.time())))
            body["score"] = body.get("score", {"posts": 0, "likes": 0, "reposts": 0, "note": "no socials connected yet"})
            items.append(body); save_personas(items)
            append_log({"kind": "persona_created", "text": "Persona created: " + body.get("name", "?") + " [" + body.get("niche", "?") + "]"})
            return self._json(body)
        if p == "/api/log":
            return self._json(append_log({"kind": body.get("kind", "note"), "text": body.get("text", "")[:500]}))
        self.send_response(404); self.end_headers()

if __name__ == "__main__":
    needs = load_needs()
    srv = HTTPServer((needs["bind"], needs["port"]), H)
    print("e090 on %s:%s" % (needs["bind"], needs["port"]), flush=True)
    srv.serve_forever()
