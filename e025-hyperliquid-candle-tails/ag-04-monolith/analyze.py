import json
import numpy as np
import pandas as pd
from scipy.stats import skew as sc_skew, kurtosis as sc_kurt
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT = 'output'
rng = np.random.default_rng(42)

df = pd.read_csv('../ag-01-data/output/candles_raw.csv')
df = df.sort_values(['coin', 'tf', 't_ms']).reset_index(drop=True)

g = df.groupby(['coin', 'tf'], group_keys=False)
df['ret'] = g['c'].pct_change() * 100.0
df['range'] = (df['h'] - df['l']) / df['l'] * 100.0

d = df[df['ret'].notna()].copy()
d['v0'] = (d['v'] <= 0).astype(int)

# ---------------- stats.csv ----------------
rows = []
for (coin, tf), sub in d.groupby(['coin', 'tf']):
    r = sub['ret']
    rows.append({
        'coin': coin, 'tf': tf, 'n': int(len(r)),
        'mean': r.mean(), 'stdev': r.std(ddof=1),
        'skew': sc_skew(r.values, bias=False),
        'kurtosis': sc_kurt(r.values, bias=False, fisher=False),
        'p50': r.quantile(.5), 'p90': r.quantile(.9), 'p99': r.quantile(.99),
        'p99_9': r.quantile(.999), 'min': r.min(), 'max': r.max(),
        'v0_count': int(sub['v0'].sum()),
    })
stats = pd.DataFrame(rows)
stats.to_csv(f'{OUT}/stats.csv', index=False)

# ---------------- hist_<tf>.csv ----------------
hist = {}
for tf in sorted(d['tf'].unique()):
    r = d.loc[d['tf'] == tf, 'ret']
    M = r.abs().quantile(0.999)
    edges = np.linspace(-M, M, 61)
    counts, _ = np.histogram(r, bins=edges)
    h = pd.DataFrame({'bucket_low': edges[:-1], 'bucket_high': edges[1:], 'count': counts})
    h.to_csv(f'{OUT}/hist_{tf}.csv', index=False)
    hist[tf] = {'M': float(M), 'total': int(counts.sum()), 'nonzero_bins': int((counts > 0).sum())}

# ---------------- charts ----------------
TF_COLORS = {'5m': '#1f77b4', '1h': '#ff7f0e', '1d': '#2ca02c', '1w': '#d62728'}
for tf in sorted(d['tf'].unique()):
    h = pd.read_csv(f'{OUT}/hist_{tf}.csv')
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(h['bucket_low'], h['count'], width=h['bucket_high'] - h['bucket_low'],
           color=TF_COLORS[tf], alpha=0.85, edgecolor='none')
    ax.set_yscale('log')
    ax.set_xlabel('close-to-close return (%)')
    ax.set_ylabel('count (log)')
    ax.set_title(f'{tf} pooled-coin return histogram (log y, bins centered on 0)')
    fig.tight_layout()
    fig.savefig(f'{OUT}/charts/hist_{tf}.png', dpi=110)
    plt.close(fig)

fig, ax = plt.subplots(figsize=(10, 5.5))
for tf in sorted(d['tf'].unique()):
    sub = d[d['tf'] == tf]
    z = (sub['ret'] - sub.groupby('coin')['ret'].transform('mean')) / sub.groupby('coin')['ret'].transform('std')
    edges = np.linspace(-5, 5, 61)
    counts, _ = np.histogram(z, bins=edges)
    ax.plot(edges[:-1] + (edges[1] - edges[0]) / 2, counts, label=tf, color=TF_COLORS[tf])
ax.set_yscale('log')
ax.set_xlabel('z-score of return (per coin,tf)')
ax.set_ylabel('count (log)')
ax.set_title('Tail heaviness overlay: pooled z-score distributions per timeframe')
ax.legend()
fig.tight_layout()
fig.savefig(f'{OUT}/charts/tail_overlay.png', dpi=110)
plt.close(fig)

# ---------------- conditional ----------------
dd = d.copy()
g2 = dd.groupby(['coin', 'tf'], group_keys=False)
dd['next_ret'] = g2['ret'].shift(-1)
dd['z'] = g2['ret'].transform(lambda x: (x - x.mean()) / x.std(ddof=1))
dd['range_pct'] = g2['range'].rank(pct=True)
dd['vol_pct'] = g2['v'].rank(pct=True)
dd['up'] = (dd['ret'] > 0).astype(int)
dd['up5'] = g2['up'].transform(lambda x: x.rolling(5, min_periods=5).sum()) == 5

def sigmas(sub):
    return {
        'prev+2sig': sub['z'] > 2,
        'prev-2sig': sub['z'] < -2,
        'prev+3sig': sub['z'] > 3,
        'prev-3sig': sub['z'] < -3,
        'vol_top10': sub['range_pct'] >= 0.9,
        'vol_top1': sub['range_pct'] >= 0.99,
        'volspike_top1': sub['vol_pct'] >= 0.99,
        'up5': sub['up5'],
    }

def emit(coin, tf, sig, label, r):
    return {
        'coin': coin, 'tf': tf, 'signal': sig, 'group': label,
        'n': int(len(r)), 'mean_next': float(r.mean()),
        'stdev_next': float(r.std(ddof=1) if len(r) > 1 else np.nan),
        'p50_next': float(np.quantile(r, .5)),
        'p90_next': float(np.quantile(r, .9)),
        'p99_next': float(np.quantile(r, .99)),
        'p99_9_next': float(np.quantile(r, .999)),
    }

cond_rows = []
for (coin, tf), sub in dd.groupby(['coin', 'tf']):
    if sub['next_ret'].notna().sum() < 2:
        continue
    base = sub.loc[sub['next_ret'].notna(), 'next_ret'].values
    for sig, mask in sigmas(sub).items():
        sel = sub.loc[mask & sub['next_ret'].notna(), 'next_ret'].values
        comp = sub.loc[~mask & sub['next_ret'].notna(), 'next_ret'].values
        for label, grp in [('yes', sel), ('no', comp), ('base', base)]:
            if len(grp) == 0:
                continue
            cond_rows.append(emit(coin, tf, sig, label, grp))

# pooled ALL rows (per tf, per signal) for the significance layer
sig_results = {}
for tf in sorted(dd['tf'].unique()):
    sub = dd[dd['tf'] == tf]
    sub = sub[sub['next_ret'].notna()]
    for sig, mask in sigmas(sub).items():
        yes = sub.loc[mask, 'next_ret'].values
        no = sub.loc[~mask, 'next_ret'].values
        if len(yes) < 300:
            verdict = 'insufficient'
            p = None
        else:
            idx = rng.integers(0, len(yes), size=(2000, len(yes)))
            boot_p99 = np.quantile(yes[idx], .99, axis=1)
            ci = (float(np.quantile(boot_p99, .025)), float(np.quantile(boot_p99, .975)))
            base_p99 = float(np.quantile(sub['next_ret'].values, .99))
            from scipy.stats import mannwhitneyu
            if len(no) > 0:
                u = mannwhitneyu(yes, no, alternative='two-sided')
                p = float(u.pvalue)
            else:
                p = None
            verdict = 'edge' if (ci[0] > base_p99 or ci[1] < base_p99) and p is not None and p < 0.05 else 'no edge'
        sig_results[f'{tf}:{sig}'] = {
            'n_yes': int(len(yes)), 'n_no': int(len(no)), 'p99_yes': float(np.quantile(yes, .99)) if len(yes) else np.nan,
            'p999_yes': float(np.quantile(yes, .999)) if len(yes) else np.nan,
            'p99_base': float(np.quantile(sub['next_ret'].values, .99)),
            'p999_base': float(np.quantile(sub['next_ret'].values, .999)),
            'ci99_yes': ci if len(yes) >= 300 else None, 'mw_p': p, 'verdict': verdict,
        }
        row = {
            'coin': 'ALL', 'tf': tf, 'signal': sig, 'group': 'yes',
            'n': int(len(yes)),
            'mean_next': float(yes.mean()) if len(yes) else np.nan,
            'stdev_next': float(yes.std(ddof=1)) if len(yes) > 1 else np.nan,
            'p50_next': float(np.quantile(yes, .5)) if len(yes) else np.nan,
            'p90_next': float(np.quantile(yes, .9)) if len(yes) else np.nan,
            'p99_next': float(np.quantile(yes, .99)) if len(yes) else np.nan,
            'p99_9_next': float(np.quantile(yes, .999)) if len(yes) else np.nan,
        }
        cond_rows.append(row)

cond = pd.DataFrame(cond_rows)
cols = ['coin', 'tf', 'signal', 'group', 'n', 'mean_next', 'stdev_next',
        'p50_next', 'p90_next', 'p99_next', 'p99_9_next']
cond = cond[cols].sort_values(['tf', 'coin', 'signal', 'group']).reset_index(drop=True)
cond.to_csv(f'{OUT}/cond_next.csv', index=False)

# ---------------- findings json ----------------
stats_summary = {}
for tf in sorted(stats['tf'].unique()):
    s = stats[stats['tf'] == tf]
    stats_summary[tf] = {
        'n_pooled': int(s['n'].sum()),
        'kurt_range': [float(s['kurtosis'].min()), float(s['kurtosis'].max())],
        'p999_range': [float(s['p99_9'].min()), float(s['p99_9'].max())],
        'p99_range': [float(s['p99'].min()), float(s['p99'].max())],
        'max_coin': s.loc[s['kurtosis'].idxmax(), 'coin'],
    }

findings = {
    'n_rows_raw': int(len(df)), 'n_rows_ret': int(len(d)),
    'per_coin': {f"{r['coin']}:{r['tf']}": {
        'n': int(r['n']), 'kurt': float(r['kurtosis']), 'p999': float(r['p99_9']),
        'p99': float(r['p99']), 'stdev': float(r['stdev']),
        'max': float(r['max']), 'min': float(r['min']), 'v0': int(r['v0_count'])}
        for _, r in stats.iterrows()},
    'stats_summary': stats_summary,
    'hist': hist,
    'signals': sig_results,
}
with open(f'{OUT}/findings.json', 'w') as f:
    json.dump(findings, f, indent=2)

print('DONE')
print(json.dumps(stats_summary, indent=2))
print('signals verdicts:')
for k, v in sig_results.items():
    print(f"  {k}: n_yes={v['n_yes']} p99_yes={v['p99_yes']:.4f} base={v['p99_base']:.4f} "
          f"ci={v['ci99_yes']} mw_p={v['mw_p']} -> {v['verdict']}")
