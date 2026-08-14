#!/usr/bin/env python3
"""
ag-10 -- Cross-sectional: relative strength, long-short portfolio, co-movement.
Reads candles_raw.csv (1d focus), produces all deliverables.
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

OUT = Path('output')
OUT.mkdir(exist_ok=True)
(OUT / 'charts').mkdir(exist_ok=True)

# -- Load & prepare --
df = pd.read_csv('../ag-01-data/output/candles_raw.csv')
df = df.sort_values(['coin', 'tf', 't_ms']).reset_index(drop=True)

d = df[df['tf'] == '1d'].copy()
d['date'] = pd.to_datetime(d['t_ms'], unit='ms')
d['ret'] = d.groupby('coin')['c'].pct_change() * 100

coins = sorted(d['coin'].unique())
print(f"Coins: {len(coins)}, date range: {d['date'].min()} to {d['date'].max()}")
print("Days per coin:")
for c in coins:
    n = (d['coin'] == c).sum()
    print(f"  {c}: {n}")

# Split halves by time per coin
midpoints = {}
for c in coins:
    coin_dates = d.loc[d['coin'] == c, 'date'].sort_values()
    mid = coin_dates.iloc[len(coin_dates) // 2]
    midpoints[c] = mid
d['half'] = d.apply(lambda r: 1 if r['date'] <= midpoints[r['coin']] else 2, axis=1)

# ====================================================================
# Q1: RELATIVE STRENGTH
# ====================================================================
print("\n=== Q1: Relative Strength ===")

results_rs = []
for N in [5, 20]:
    d[f'trail_{N}'] = d.groupby('coin')['c'].pct_change(N) * 100

    def assign_bucket(group, trail_col=f'trail_{N}'):
        if len(group) < 3:
            group = group.copy()
            group['bucket'] = np.nan
            return group
        group = group.copy()
        group['rank'] = group[trail_col].rank(ascending=True)
        top = group.nlargest(3, 'rank')
        bottom = group.nsmallest(3, 'rank')
        group.loc[top.index, 'bucket'] = 'top3'
        group.loc[bottom.index, 'bucket'] = 'bottom3'
        mid_mask = ~group.index.isin(top.index) & ~group.index.isin(bottom.index)
        group.loc[mid_mask, 'bucket'] = 'middle'
        return group

    d = d.groupby('date', group_keys=False).apply(assign_bucket)

    # Forward returns
    for coin in coins:
        mask = d['coin'] == coin
        c_vals = d.loc[mask, 'c'].values
        fwd1 = np.empty(len(c_vals))
        fwd5 = np.empty(len(c_vals))
        fwd1[:] = np.nan
        fwd5[:] = np.nan
        for i in range(len(c_vals) - 1):
            fwd1[i] = (c_vals[i+1] - c_vals[i]) / c_vals[i] * 100
        for i in range(len(c_vals) - 5):
            fwd5[i] = (c_vals[i+5] - c_vals[i]) / c_vals[i] * 100
        d.loc[mask, 'fwd1'] = fwd1
        d.loc[mask, 'fwd5'] = fwd5

    for half_label, half_val in [('full', None), ('H1', 1), ('H2', 2)]:
        sub = d if half_val is None else d[d['half'] == half_val]
        for bucket in ['top3', 'middle', 'bottom3']:
            b = sub[sub['bucket'] == bucket]
            for horizon, col in [('next_day', 'fwd1'), ('next_5day', 'fwd5')]:
                valid = b[col].dropna()
                if len(valid) > 0:
                    results_rs.append({
                        'N': N, 'half': half_label, 'bucket': bucket,
                        'horizon': horizon, 'n': len(valid),
                        'mean': round(valid.mean(), 4),
                        'median': round(valid.median(), 4),
                        'std': round(valid.std(), 4),
                    })

rs_df = pd.DataFrame(results_rs)
rs_df.to_csv(OUT / 'relative_strength.csv', index=False)
print(rs_df.to_string(index=False))

# Chart: RS bucket bars
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
for i, N in enumerate([5, 20]):
    ax = axes[i]
    sub = rs_df[(rs_df['N'] == N) & (rs_df['half'] == 'full') & (rs_df['horizon'] == 'next_day')]
    buckets = ['bottom3', 'middle', 'top3']
    means = [sub[sub['bucket'] == b]['mean'].values[0] if len(sub[sub['bucket'] == b]) > 0 else 0 for b in buckets]
    colors = ['#d32f2f', '#9e9e9e', '#388e3c']
    ax.bar(buckets, means, color=colors, edgecolor='black')
    ax.set_title(f'Trail {N}-day -> Next-Day Return by RS Bucket')
    ax.set_ylabel('Mean next-day return (%)')
    ax.axhline(0, color='black', linewidth=0.5)
    ax.set_xlabel('RS Bucket')
plt.tight_layout()
plt.savefig(OUT / 'charts' / 'rs_bucket_bars.png', dpi=150)
plt.close()
print("\nSaved rs_bucket_bars.png")

# ====================================================================
# Q2: LONG-SHORT PORTFOLIO
# ====================================================================
print("\n=== Q2: Long-Short Portfolio ===")

FEE_PER_SIDE = 0.00045  # 0.045%

ls_results = {}
for N in [5, 20]:
    oos = d[d['half'] == 2].copy()
    daily_pnl = []

    for date_val, grp in oos.groupby('date'):
        valid = grp.dropna(subset=[f'trail_{N}', 'fwd1'])
        if len(valid) < 6:
            continue

        top3 = valid.nlargest(3, f'trail_{N}')
        bottom3 = valid.nsmallest(3, f'trail_{N}')

        long_ret = top3['fwd1'].mean() / 100
        short_ret = -bottom3['fwd1'].mean() / 100

        gross = long_ret + short_ret
        fees = 2 * FEE_PER_SIDE  # 2 legs x 0.045%
        net = gross - fees

        daily_pnl.append({
            'date': date_val,
            'n_coins': len(valid),
            'long_ret_pct': round(long_ret * 100, 4),
            'short_ret_pct': round(short_ret * 100, 4),
            'gross_pct': round(gross * 100, 4),
            'fees_pct': round(fees * 100, 4),
            'net_pct': round(net * 100, 4),
            'top3_coins': ','.join(top3['coin'].values),
            'bottom3_coins': ','.join(bottom3['coin'].values),
        })

    ls_df = pd.DataFrame(daily_pnl)
    ls_df.to_csv(OUT / f'long_short_N{N}.csv', index=False)
    ls_results[N] = ls_df

    if len(ls_df) > 0:
        cum_net = (1 + ls_df['net_pct'] / 100).cumprod()
        total_ret = (cum_net.iloc[-1] - 1) * 100
        mean_daily = ls_df['net_pct'].mean()
        sharpe = ls_df['net_pct'].mean() / ls_df['net_pct'].std() * np.sqrt(252) if ls_df['net_pct'].std() > 0 else 0
        max_dd = ((cum_net / cum_net.cummax()) - 1).min() * 100
        win_rate = (ls_df['net_pct'] > 0).mean() * 100

        print(f"\nN={N} Long-Short (OOS, second half):")
        print(f"  Trading days: {len(ls_df)}")
        print(f"  Total return: {total_ret:.2f}%")
        print(f"  Mean daily: {mean_daily:.4f}%")
        print(f"  Sharpe: {sharpe:.2f}")
        print(f"  Max DD: {max_dd:.2f}%")
        print(f"  Win rate: {win_rate:.1f}%")

combined_ls = pd.concat([ls_results[5].assign(N=5), ls_results[20].assign(N=20)], ignore_index=True)
combined_ls.to_csv(OUT / 'long_short.csv', index=False)

# Equity curves
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
for i, N in enumerate([5, 20]):
    ax = axes[i]
    ls_df = ls_results[N]
    if len(ls_df) > 0:
        cum_net = (1 + ls_df['net_pct'] / 100).cumprod()
        cum_gross = (1 + ls_df['gross_pct'] / 100).cumprod()
        ax.plot(ls_df['date'].values, cum_net.values, label='Net of fees', color='#1565c0', linewidth=1.5)
        ax.plot(ls_df['date'].values, cum_gross.values, label='Gross', color='#90caf9', linewidth=1, alpha=0.7)
        ax.axhline(1, color='black', linewidth=0.5, linestyle='--')
    ax.set_title(f'Long-Short Equity Curve (N={N}, OOS)')
    ax.set_ylabel('Growth of $1')
    ax.legend()
    ax.tick_params(axis='x', rotation=30)
plt.tight_layout()
plt.savefig(OUT / 'charts' / 'long_short_equity.png', dpi=150)
plt.close()
print("\nSaved long_short_equity.png")

# ====================================================================
# Q3: CO-MOVEMENT
# ====================================================================
print("\n=== Q3: Co-Movement ===")

coin_stats = d.groupby('coin')['ret'].agg(['mean', 'std']).reset_index()
coin_stats.columns = ['coin', 'ret_mean', 'ret_std']

d2 = d.merge(coin_stats, on='coin', how='left')
d2['z_ret'] = (d2['ret'] - d2['ret_mean']) / d2['ret_std']
d2['extreme_3s'] = d2['z_ret'].abs() > 3

pivot = d2.pivot_table(index='date', columns='coin', values='ret')

co_move_results = []
for coin in coins:
    events = d2[(d2['coin'] == coin) & (d2['extreme_3s'])].copy()
    if len(events) == 0:
        continue
    for _, ev in events.iterrows():
        date_val = ev['date']
        direction = 1 if ev['z_ret'] > 0 else -1
        other_coins = [c for c in coins if c != coin]
        if date_val not in pivot.index:
            continue
        other_rets = pivot.loc[date_val, other_coins].dropna()
        if len(other_rets) == 0:
            continue
        same_dir = (other_rets > 0).sum() if direction > 0 else (other_rets < 0).sum()
        frac = same_dir / len(other_rets)
        co_move_results.append({
            'trigger_coin': coin,
            'date': date_val,
            'trigger_direction': 'up' if direction > 0 else 'down',
            'trigger_ret': round(ev['ret'], 4),
            'trigger_z': round(ev['z_ret'], 4),
            'n_others': len(other_rets),
            'n_same_dir': same_dir,
            'frac_same_dir': round(frac, 4),
        })

cm_df = pd.DataFrame(co_move_results)
if len(cm_df) > 0:
    summary = cm_df.groupby('trigger_direction').agg(
        n_events=('date', 'count'),
        mean_frac=('frac_same_dir', 'mean'),
        median_frac=('frac_same_dir', 'median'),
    ).reset_index()
    summary['expected_if_independent'] = 0.5
    print("\nCo-movement summary (3sigma events):")
    print(summary.to_string(index=False))

    per_coin = cm_df.groupby(['trigger_coin', 'trigger_direction']).agg(
        n_events=('date', 'count'),
        mean_frac=('frac_same_dir', 'mean'),
    ).reset_index()
    print("\nPer-coin co-movement:")
    print(per_coin.to_string(index=False))
else:
    print("No 3sigma events found!")

if len(cm_df) > 0:
    cm_df.to_csv(OUT / 'co_movement.csv', index=False)

    fig, ax = plt.subplots(figsize=(8, 5))
    dirs = ['down', 'up']
    means = [cm_df[cm_df['trigger_direction'] == d]['frac_same_dir'].mean() for d in dirs]
    counts = [cm_df[cm_df['trigger_direction'] == d]['frac_same_dir'].count() for d in dirs]
    colors = ['#d32f2f', '#388e3c']
    bars = ax.bar(dirs, means, color=colors, edgecolor='black', width=0.5)
    ax.axhline(0.5, color='gray', linewidth=1, linestyle='--', label='Expected if independent (50%)')
    ax.set_title(f'Co-Movement on 3sigma Event Days (n={sum(counts)} events)')
    ax.set_ylabel('Mean fraction same direction')
    ax.set_ylim(0, 1)
    ax.legend()
    for bar, count, m in zip(bars, counts, means):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                f'{m:.1%}\nn={count}', ha='center', fontsize=10)
    plt.tight_layout()
    plt.savefig(OUT / 'charts' / 'co_movement.png', dpi=150)
    plt.close()
    print("\nSaved co_movement.png")

print("\n=== DONE ===")
