#!/usr/bin/env python3
"""ag-14 volume-price interaction analysis.

Declared grid (see output/session-log.md):
  signals: move_vol, obv, vwap_dist, ud_vol_ratio, vol_adj_ret
  tfs:     1d (primary), 1h (secondary sensitivity)
  targets: next1 = (c[t+1]/c[t]-1)*100, next5 = (c[t+5]/c[t]-1)*100 (pct)
  buckets per signal as declared. Split-sample 50/50 by time per (coin,tf).
  Per-coin rows only where bucket n>=30. Causal features only.
"""
import pandas as pd
import numpy as np
import sys, os

INPUT = '../ag-01-data/output/candles_raw.csv'
OUTDIR = os.path.join(os.path.dirname(__file__), '..', 'output')

def pct_bucket(x):
    if x < 50: return '<50'
    if x < 90: return '50-90'
    if x < 99: return '90-99'
    return '>99'

def vwap_z_bucket(z):
    if pd.isna(z): return None
    if z < -1: return 'z<-1'
    if z < -0.5: return '-1..-0.5'
    if z < 0.5: return '-0.5..0.5'
    if z < 1: return '0.5..1'
    return '>1'

def ratio_bucket(r):
    if pd.isna(r): return None
    if r < 0.5: return '<0.5'
    if r < 0.8: return '0.5-0.8'
    if r < 1.25: return '0.8-1.25'
    if r < 2: return '1.25-2'
    return '>2'

def slope(ser, w=10):
    """Linear regression slope of ser over trailing w rows (causal)."""
    return ser.rolling(w, min_periods=w).apply(
        lambda a: np.polyfit(np.arange(len(a)), a, 1)[0], raw=True)

def compute_group(g):
    """g: one (coin, tf) block sorted by t_ms. Returns feature rows."""
    n = len(g)
    c = g['c'].values
    v = g['v'].values
    o, h, l = g['o'].values, g['h'].values, g['l'].values
    ret = np.full(n, np.nan)
    ret[1:] = (c[1:] / c[:-1] - 1.0) * 100.0
    ret_next1 = np.full(n, np.nan)
    ret_next1[:-1] = (c[1:] / c[:-1] - 1.0) * 100.0
    ret_next5 = np.full(n, np.nan)
    ret_next5[:-5] = (c[5:] / c[:-5] - 1.0) * 100.0

    sr = pd.Series(ret)

    # causal trailing volume percentile within (coin,tf)
    vp = pd.Series(v).rolling(101, min_periods=30).apply(
        lambda a: (a[-1] <= a).mean() * 100.0, raw=True)

    # 1. move_vol buckets: sign(ret) x vol_pct
    sign_ret = np.where(ret > 0, 'up', np.where(ret < 0, 'down', 'flat'))
    vol_bucket = vp.map(pct_bucket)

    # 2. OBV
    obv = np.full(n, np.nan)
    run = 0.0
    for i in range(n):
        if pd.isna(ret[i]):
            run = 0.0
        else:
            run += (1.0 if ret[i] > 0 else -1.0 if ret[i] < 0 else 0.0) * v[i]
        obv[i] = run
    obv_s = pd.Series(obv)
    obv_slope = slope(obv_s, 10)
    price_slope = slope(pd.Series(c), 10)
    def obv_bucket(o_s, p_s):
        if pd.isna(o_s) or pd.isna(p_s): return None
        if o_s >= 0 and p_s >= 0: return 'obv_up/price_up'
        if o_s < 0 and p_s >= 0: return 'obv_dn/price_up(bear_div)'
        if o_s >= 0 and p_s < 0: return 'obv_up/price_dn(bull_div)'
        return 'obv_dn/price_dn'
    obv_b = [obv_bucket(o_s, p_s) for o_s, p_s in zip(obv_slope.values, price_slope.values)]

    # 3. VWAP distance (N=20)
    p_typ = (h + l + c) / 3.0
    pv = pd.Series(p_typ * v)
    vw = pd.Series(v)
    vwap = pv.rolling(20, min_periods=20).sum() / vw.rolling(20, min_periods=20).sum()
    dist = pd.Series(c) / vwap - 1.0
    dist_sig = dist.rolling(20, min_periods=20).std()
    z = dist / dist_sig
    vwap_b = z.map(vwap_z_bucket)

    # 4. up/down volume ratio over trailing 10
    upv = np.where(ret > 0, v, 0.0)
    dnv = np.where(ret < 0, v, 0.0)
    up_sum = pd.Series(upv).rolling(10, min_periods=10).sum()
    dn_sum = pd.Series(dnv).rolling(10, min_periods=10).sum()
    ratio = up_sum / dn_sum.replace(0, np.nan)
    ratio_b = ratio.map(ratio_bucket)

    # 5. volume-adjusted return
    med_v = np.median(v)
    rel_vol = pd.Series(v) / med_v if med_v > 0 else pd.Series(np.full(n, np.nan))
    vol_adj = sr / rel_vol
    q = vol_adj.abs().rank(pct=True)  # per-(coin,tf) quintile of |vol_adj|
    qint = (q * 5).clip(0, 4)
    qint = qint.where(qint.notna(), np.nan).astype('float')
    def va_bucket(sig, qi):
        if pd.isna(qi): return None
        return f"{sig}_q{int(qi) + 1}"
    va_b = [va_bucket(s, qi) for s, qi in zip(sign_ret, qint)]

    return pd.DataFrame({
        't_ms': g['t_ms'].values,
        'c': c, 'v': v,
        'ret': ret, 'ret_next1': ret_next1, 'ret_next5': ret_next5,
        'sig_move_vol': [f"{s}|{vb}" if vb else None for s, vb in zip(sign_ret, vol_bucket)],
        'sig_obv': obv_b,
        'sig_vwap': vwap_b,
        'sig_ratio': ratio_b,
        'sig_voladj': va_b,
        'z': z.values,
    })

def add_split(df, coin, tf):
    half_t = np.median(df['t_ms'].values)
    df['split'] = np.where(df['t_ms'] < half_t, 'h1', 'h2')

def agg_block(df, signal, bucket_col, coin, tf):
    rows = []
    for b, gb in df.groupby(bucket_col, sort=False):
        if b is None or (isinstance(b, float) and pd.isna(b)):
            continue
        n = len(gb)
        r = {'signal': signal, 'tf': tf, 'coin': coin, 'bucket': str(b), 'n': n}
        for tgt in ('ret_next1', 'ret_next5'):
            s = gb[tgt].dropna()
            if len(s):
                r[f'{tgt}_mean'] = s.mean()
                r[f'{tgt}_median'] = s.median()
                r[f'{tgt}_win'] = (s > 0).mean()
            else:
                r[f'{tgt}_mean'] = r[f'{tgt}_median'] = r[f'{tgt}_win'] = np.nan
        for half in ('h1', 'h2'):
            s = gb.loc[gb['split'] == half, 'ret_next1'].dropna()
            r[f'{half}_next1_mean'] = s.mean() if len(s) else np.nan
            r[f'{half}_next1_median'] = s.median() if len(s) else np.nan
            r[f'{half}_next1_win'] = (s > 0).mean() if len(s) else np.nan
        rows.append(r)
    return rows

def main():
    df = pd.read_csv(INPUT)
    df = df[df['v'] > 0].copy()
    df = df[df['tf'].isin(['1d', '1h'])].copy()
    df.sort_values(['coin', 'tf', 't_ms'], inplace=True)
    df.reset_index(drop=True, inplace=True)

    all_rows = []
    feature_frames = []
    for (coin, tf), g in df.groupby(['coin', 'tf']):
        g = g.reset_index(drop=True)
        f = compute_group(g)
        f['coin'] = coin
        f['tf'] = tf
        add_split(f, coin, tf)
        for signal, col in [('move_vol', 'sig_move_vol'), ('obv', 'sig_obv'),
                            ('vwap_dist', 'sig_vwap'), ('ud_vol_ratio', 'sig_ratio'),
                            ('vol_adj_ret', 'sig_voladj')]:
            all_rows += agg_block(f, signal, col, coin, tf)
        feature_frames.append(f)
    sig = pd.DataFrame(all_rows)
    sig['n'] = pd.to_numeric(sig['n'])

    # pooled across coins: aggregate the raw per-row feature frame directly
    feat = pd.concat(feature_frames, ignore_index=True)
    pooled_rows = []
    for signal, col in [('move_vol', 'sig_move_vol'), ('obv', 'sig_obv'),
                        ('vwap_dist', 'sig_vwap'), ('ud_vol_ratio', 'sig_ratio'),
                        ('vol_adj_ret', 'sig_voladj')]:
        for (tf, b), gb in feat.groupby(['tf', col], sort=False):
            if b is None or (isinstance(b, float) and pd.isna(b)):
                continue
            r = {'signal': signal, 'tf': tf, 'coin': 'ALL', 'bucket': str(b), 'n': len(gb)}
            for tgt in ('ret_next1', 'ret_next5'):
                s = gb[tgt].dropna()
                r[f'{tgt}_mean'] = s.mean() if len(s) else np.nan
                r[f'{tgt}_median'] = s.median() if len(s) else np.nan
                r[f'{tgt}_win'] = (s > 0).mean() if len(s) else np.nan
            for half in ('h1', 'h2'):
                s = gb.loc[gb['split'] == half, 'ret_next1'].dropna()
                r[f'{half}_next1_mean'] = s.mean() if len(s) else np.nan
                r[f'{half}_next1_median'] = s.median() if len(s) else np.nan
                r[f'{half}_next1_win'] = (s > 0).mean() if len(s) else np.nan
            pooled_rows.append(r)
    pooled = pd.DataFrame(pooled_rows)

    sig_full = pd.concat([pooled, sig], ignore_index=True)
    sig_full = sig_full[['signal', 'tf', 'coin', 'bucket', 'n',
                         'ret_next1_mean', 'ret_next1_median', 'ret_next1_win',
                         'ret_next5_mean', 'ret_next5_median', 'ret_next5_win',
                         'h1_next1_mean', 'h1_next1_median', 'h1_next1_win',
                         'h2_next1_mean', 'h2_next1_median', 'h2_next1_win']]
    sig_full.to_csv(os.path.join(OUTDIR, 'signals.csv'), index=False)

    # per-coin: drop buckets with n<30 per (coin,tf) for replication
    sig_coin = sig_full[sig_full['coin'] != 'ALL'].copy()
    sig_coin = sig_coin[sig_coin['n'] >= 30]

    print("signals.csv rows:", len(sig_full))
    print("per-coin rows (n>=30):", len(sig_coin))
    print(sig_full.groupby(['signal', 'tf']).size())
    feat.to_csv(os.path.join(OUTDIR, '_features_1d_1h.csv'), index=False)

if __name__ == '__main__':
    main()
