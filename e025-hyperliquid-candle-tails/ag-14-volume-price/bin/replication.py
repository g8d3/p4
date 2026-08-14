#!/usr/bin/env python3
"""ag-14 replication: per-coin replication rate + split-half consistency.

For each declared headline effect (see session-log.md grid):
  effect = E[next1 | bucket_A] - E[next1 | bucket_B]   (mean next1, %)
- pooled effect (all coins) and pooled effect per half
- per-coin effect for coins with n>=30 in both buckets
- replication rate = fraction of coins where per-coin effect sign == pooled sign
- split-half consistency = pooled effect sign in h1 == pooled effect sign in h2
Writes output/replication.csv (next1 and next5 horizons).
"""
import pandas as pd, numpy as np, os

OUTDIR = os.path.join(os.path.dirname(__file__), '..', 'output')
sig = pd.read_csv(os.path.join(OUTDIR, 'signals.csv'))

# Declared headline effects: (signal, effect_name, bucket_A, bucket_B)
EFFECTS = [
    ('move_vol', 'up_hi_vol_minus_lo', 'up|>99', 'up|<50'),
    ('move_vol', 'dn_hi_vol_minus_lo', 'down|>99', 'down|<50'),
    ('obv', 'bear_div_minus_up_conf', 'obv_dn/price_up(bear_div)', 'obv_up/price_up'),
    ('obv', 'bull_div_minus_dn_conf', 'obv_up/price_dn(bull_div)', 'obv_dn/price_dn'),
    ('vwap_dist', 'stretched_up_minus_dn', '>1', 'z<-1'),
    ('ud_vol_ratio', 'hi_ratio_minus_lo', '>2', '<0.5'),
    ('vol_adj_ret', 'up_q5_minus_q1', 'up_q5', 'up_q1'),
    ('vol_adj_ret', 'dn_q5_minus_q1', 'down_q5', 'down_q1'),
]

def effect_from_rows(rows, col='ret_next1_mean'):
    rows = rows.dropna(subset=[col])
    if len(rows) < 2:
        return np.nan
    a = rows[rows['bucket'] == bucket_map['A']]
    b = rows[rows['bucket'] == bucket_map['B']]
    if len(a) == 0 or len(b) == 0:
        return np.nan
    return float(a[col].iloc[0] - b[col].iloc[0])

out_rows = []
for signal, name, ba, bb in EFFECTS:
    bucket_map = {'A': ba, 'B': bb}
    for tf in ('1d', '1h'):
        for tgt in ('ret_next1_mean', 'ret_next5_mean'):
            pooled = sig[(sig['signal'] == signal) & (sig['tf'] == tf) &
                         (sig['coin'] == 'ALL')]
            eff = effect_from_rows(pooled, tgt)
            # split-half effects on next1 mean (per-half pooled means are in signals.csv)
            eff_h1 = effect_from_rows(pooled, 'h1_next1_mean') if tgt == 'ret_next1_mean' else np.nan
            eff_h2 = effect_from_rows(pooled, 'h2_next1_mean') if tgt == 'ret_next1_mean' else np.nan

            coin_rows = sig[(sig['signal'] == signal) & (sig['tf'] == tf) &
                            (sig['coin'] != 'ALL') & (sig['n'] >= 30)]
            per_coin = {}
            for coin, g in coin_rows.groupby('coin'):
                e = effect_from_rows(g, tgt)
                per_coin[coin] = e
            valid = {c: e for c, e in per_coin.items() if not np.isnan(e)}
            n_coins = len(valid)
            if n_coins and not np.isnan(eff) and eff != 0:
                same = sum(1 for e in valid.values() if np.sign(e) == np.sign(eff))
                repl = same / n_coins
            else:
                repl = np.nan
            split_consistent = (not np.isnan(eff_h1) and not np.isnan(eff_h2)
                                and np.sign(eff_h1) == np.sign(eff_h2)) if tgt == 'ret_next1_mean' else np.nan
            out_rows.append({
                'signal': signal, 'effect': name, 'tf': tf, 'target': tgt,
                'bucket_A': ba, 'bucket_B': bb,
                'pooled_effect': eff, 'effect_h1': eff_h1, 'effect_h2': eff_h2,
                'n_coins_valid': n_coins, 'replication_rate': repl,
                'split_half_consistent': split_consistent,
                'per_coin_effects': repr(valid),
            })

rep = pd.DataFrame(out_rows)
rep.to_csv(os.path.join(OUTDIR, 'replication.csv'), index=False)
pd.set_option('display.width', 200)
pd.set_option('display.max_columns', 30)
print(rep[['signal', 'effect', 'tf', 'target', 'pooled_effect', 'effect_h1', 'effect_h2',
           'n_coins_valid', 'replication_rate', 'split_half_consistent']].round(4).to_string(index=False))
