#!/usr/bin/env python3
"""e059 free TVL column (run160): DefiLlama keyless /protocols + /v2/chains -> output/tvl.json.
Re-run: timeout 120 python3 bin/tvl.py. No keys, $0."""
import json, datetime, urllib.request
def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':'e059-tvl/1.0'})
    return json.load(urllib.request.urlopen(req,timeout=60))
protos=get('https://api.llama.fi/protocols'); by_slug={p['slug']:p for p in protos}
chains=get('https://api.llama.fi/v2/chains'); by_chain={c['gecko_id']:c for c in chains if c.get('gecko_id')}
CHAINMAP={'ethereum':'ethereum','solana':'solana','bitcoin':'bitcoin','bsc':'binancecoin','tron':'tron','avalanche':'avalanche-2','arbitrum':'arbitrum','op-mainnet':'optimism','sui':'sui','near':'near','aptos':'aptos','injective':'injective'}
m=json.load(open('output/multiples.json'))['protocols']
out=[]; hit=0
for p in m:
    tvl=src=None
    for s in p.get('slugs_used',[]):
        if s in by_slug and by_slug[s].get('tvl'): tvl=by_slug[s]['tvl']; src=f'llama/protocol/{s}'; break
        if s in CHAINMAP and CHAINMAP[s] and CHAINMAP[s] in by_chain and by_chain[CHAINMAP[s]].get('tvl'):
            tvl=by_chain[CHAINMAP[s]]['tvl']; src=f'llama/chain/{CHAINMAP[s]}'; break
    if tvl: hit+=1
    mcap=p.get('market_cap_usd')
    out.append({'symbol':p['symbol'],'tvl_usd':round(tvl) if tvl else None,'tvl_src':src,
                'p_tvl':round(mcap/tvl,2) if (tvl and mcap) else None,'data_through':'2026-09-15'})
doc={'track':'e059','as_of':datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ'),
     'source':'DefiLlama free (api.llama.fi/protocols + /v2/chains, keyless)','coverage':f'{hit}/{len(m)}','rows':out}
json.dump(doc,open('output/tvl.json','w'),indent=1)
print('tvl coverage',doc['coverage'])
