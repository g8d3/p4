#!/usr/bin/env bash
# e071 e2e: fail-closed on shape. NEVER run comps.py/fetch.py standalone in prod (use refresh.sh).
set -e
cd "$(dirname "$0")/.."
for f in output/comps.json output/venues.json output/unlocks.json output/sources.json output/comps.csv output/index.html output/version.json; do
  [ -f "$f" ] || { echo "FAIL missing $f"; exit 1; }
done
python3 -c "
import json
d=json.load(open('output/comps.json'))
assert d['tokens']>=20, 'universe shrank'
for r in d['tokens_rows']:
    for k in ['symbol','price_usd','mcap_usd','p_sales','mcap_share_pct','volume_share_pct','liquidity_share_pct','drop_from_ath_pct','rise_from_atl_pct','sig_low_usd','supply_net_pct','age_days','gmgn_url','dex_url','through','stale']:
        assert k in r, f'missing col {k} in {r[\"symbol\"]}'
    assert isinstance(r['mcap_share_pct'],(int,float)), 'mcap_share not numeric'
v=json.load(open('output/venues.json'))
assert v['n'] >= 6, 'venues missing'
for w in v['rows']:
    for k in ['symbol','venue','venue_type','taker_fee_bps','fee_variable','slip_1k_bps','lp_apr_proxy_pct']:
        assert k in w, f'missing venue col {k}'
print('shape ok:', d['tokens'], 'rows,', v['n'], 'venues, oldest', d['through_oldest'])
s=json.load(open('output/sources.json'))
assert s['n'] >= 10, 'sources directory shrank'
for r in s['rows']:
    for k in ['source','kind','covers','access','cadence','status']:
        assert k in r, f'missing sources col {k}'
    assert r['status'] in ('live','planned'), 'bad source status'
print('sources ok:', s['n'], 'entries')
"
python3 ../e000-fundamentals/bin/table_check.py e071-ai-inference-comps --served output/index.html
echo "E2E PASS"
