#!/usr/bin/env python3
"""ag-14 charts: bucket bars per signal (1d pooled) + OBV divergence illustration."""
import pandas as pd, numpy as np
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE = os.path.join(os.path.dirname(__file__), '..', 'output')
CH = os.path.join(BASE, 'charts')
os.makedirs(CH, exist_ok=True)
FEAT = os.path.join(BASE, '_features_1d_1h.csv')

df = pd.read_csv(os.path.join(BASE, 'signals.csv'))
pooled = df[df.coin == 'ALL']

SIGNALS = {
    'move_vol': ('sig_move_vol', 'Move x volume: E[next-1d] by bucket', 'green'),
    'obv': ('sig_obv', 'OBV x price slope: E[next-1d]', 'blue'),
    'vwap_dist': ('sig_vwap', 'VWAP distance z: E[next-1d]', 'purple'),
    'ud_vol_ratio': ('sig_ratio', 'Up/down volume ratio 10: E[next-1d]', 'orange'),
    'vol_adj_ret': ('sig_voladj', 'Volume-adjusted return: E[next-1d]', 'red'),
}

def bar(signal, col, title, color):
    sub = pooled[(pooled.signal == signal) & (pooled.tf == '1d')].sort_values('bucket')
    sub = sub[~sub['bucket'].str.startswith('flat')]
    fig, ax = plt.subplots(figsize=(10, 5.5))
    x = np.arange(len(sub))
    m = sub['ret_next1_mean'].values
    md = sub['ret_next1_median'].values
    ax.bar(x - 0.2, m, 0.4, label='mean', color=color, alpha=0.85)
    ax.bar(x + 0.2, md, 0.4, label='median', color=color, alpha=0.35)
    ax.axhline(0, color='k', lw=0.8)
    ax.axhline(0.09, color='gray', ls='--', lw=1, label='fee 0.09% RT')
    ax.axhline(-0.09, color='gray', ls='--', lw=1)
    for i, (mm, mdd, nn) in enumerate(zip(m, md, sub['n'])):
        mm, mdd = float(mm), float(mdd)
        ax.text(i - 0.2, mm, f'{mm:.2f}', ha='center', va='bottom' if mm >= 0 else 'top', fontsize=7)
        ax.text(i + 0.2, mdd, f'{mdd:.2f}', ha='center', va='bottom' if mdd >= 0 else 'top', fontsize=7)
    ax.set_xticks(x)
    ax.set_xticklabels(sub['bucket'], rotation=45, ha='right', fontsize=8)
    ax.set_ylabel('next-1d return %')
    ax.set_title(title + '  (1d pooled)')
    ax.legend(fontsize=8)
    ax.grid(axis='y', alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(CH, f'{signal}_1d.png'), dpi=110)
    plt.close(fig)
    print('wrote', f'{signal}_1d.png')

for s, (col, title, color) in SIGNALS.items():
    bar(s, col, title, color)

# OBV divergence illustration: use CRV 1d (strong effect) last ~220 days
f = df[df.tf == '1d']
c = pd.read_csv(FEAT)
c = c[(c.coin == 'CRV') & (c.tf == '1d')].reset_index(drop=True)
n = len(c)
obv = c['sig_obv']
price = c['c']
tidx = np.arange(n)
import numpy as np
obv_series = np.zeros(n)
run = 0.0
rets = c['ret'].values
for i in range(n):
    if np.isnan(rets[i]):
        run = 0.0
    else:
        run += (1.0 if rets[i] > 0 else -1.0 if rets[i] < 0 else 0.0) * c['v'].values[i]
    obv_series[i] = run
win = slice(max(0, n - 230), n)
fig, ax = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
ax[0].plot(tidx[win], price.values[win], color='k', lw=1.2, label='close')
ax[0].set_title('CRV 1d — price vs OBV (divergence illustration)')
ax[0].legend(fontsize=8)
ax[0].grid(alpha=0.3)
obv_norm = (obv_series - obv_series.min()) / (obv_series.max() - obv_series.min())
ax[1].plot(tidx[win], obv_norm[win], color='blue', lw=1.2, label='OBV (normalized)')
# shade bearish divergence regions: price up-slope & obv down-slope
bear = c['sig_obv'] == 'obv_dn/price_up(bear_div)'
bull = c['sig_obv'] == 'obv_up/price_dn(bull_div)'
ax[1].fill_between(tidx[win], 0, 1, where=bear.values[win], color='red', alpha=0.25, label='bearish div')
ax[1].fill_between(tidx[win], 0, 1, where=bull.values[win], color='green', alpha=0.25, label='bullish div')
ax[1].legend(fontsize=8)
ax[1].grid(alpha=0.3)
ax[1].set_xlabel('bar index (last 230 days)')
fig.tight_layout()
fig.savefig(os.path.join(CH, 'obv_divergence_illustration.png'), dpi=110)
plt.close(fig)
print('wrote obv_divergence_illustration.png')
