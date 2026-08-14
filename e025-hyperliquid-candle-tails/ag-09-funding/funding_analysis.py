#!/usr/bin/env python3
"""
ag-09-funding analysis: funding sentiment edge
Tests whether crowding (extreme funding) predicts reversals.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timezone
import matplotlib.pyplot as plt
import os
import warnings
warnings.filterwarnings('ignore')

# Load data
print("Loading data...")
funding_df = pd.read_csv('../ag-01-data/output/funding_raw.csv')
candles_df = pd.read_csv('../ag-01-data/output/candles_raw.csv')

# Clean funding data - cast fundingRate to float
funding_df['fundingRate'] = funding_df['fundingRate'].astype(float)
funding_df['premium'] = funding_df['premium'].astype(float)

# Check for XMR (should have 0 rows)
xmr_rows = funding_df[funding_df['coin'] == 'XMR']
print(f"XMR funding rows: {len(xmr_rows)} (expected: 0)")

# Get common coins between datasets
funding_coins = set(funding_df['coin'].unique())
candle_coins = set(candles_df['coin'].unique())
common_coins = list(funding_coins & candle_coins)
print(f"Common coins: {sorted(common_coins)}")
print(f"Coins in funding only: {sorted(funding_coins - candle_coins)}")
print(f"Coins in candles only: {sorted(candle_coins - funding_coins)}")

# Filter to common coins
funding_df = funding_df[funding_df['coin'].isin(common_coins)].copy()
candles_df = candles_df[candles_df['coin'].isin(common_coins)].copy()

print(f"Filtered funding rows: {len(funding_df)}")
print(f"Filtered candle rows: {len(candles_df)}")

# Convert time to datetime
funding_df['datetime'] = pd.to_datetime(funding_df['time_ms'], unit='ms')
candles_df['datetime'] = pd.to_datetime(candles_df['t_ms'], unit='ms')

# Work primarily with daily timeframe for funding analysis
daily_candles = candles_df[candles_df['tf'] == '1d'].copy()
print(f"Daily candles: {len(daily_candles)}")

# For each daily candle, get the funding at the day's open
# Convention: use the funding payment closest to the day's open time
# Fundings are hourly, so we'll use the funding with time_ms <= candle open, closest to it

def get_funding_at_day_open(day_open_time, coin_funding):
    """Get funding rate closest to but not after day open time"""
    before_open = coin_funding[coin_funding['datetime'] <= day_open_time]
    if len(before_open) == 0:
        return None
    # Get the most recent funding before open
    return before_open.iloc[-1]

# Create daily dataframe with funding
daily_with_funding = []

for coin in common_coins:
    coin_candles = daily_candles[daily_candles['coin'] == coin].sort_values('datetime')
    coin_funding = funding_df[funding_df['coin'] == coin].sort_values('datetime')
    
    for _, candle in coin_candles.iterrows():
        funding_row = get_funding_at_day_open(candle['datetime'], coin_funding)
        if funding_row is not None:
            daily_with_funding.append({
                'coin': coin,
                'date': candle['datetime'],
                't_ms': candle['t_ms'],
                'open': candle['o'],
                'high': candle['h'],
                'low': candle['l'],
                'close': candle['c'],
                'volume': candle['v'],
                'funding_rate': funding_row['fundingRate'],
                'premium': funding_row['premium']
            })

daily_df = pd.DataFrame(daily_with_funding)
print(f"Daily candles with funding: {len(daily_df)}")

# Calculate returns
daily_df = daily_df.sort_values(['coin', 'date'])
daily_df['next_1d_return'] = daily_df.groupby('coin')['close'].pct_change().shift(-1) * 100
daily_df['next_5d_return'] = daily_df.groupby('coin')['close'].pct_change(-5).shift(-5) * 100

# Compute per-coin funding z-scores
daily_df['funding_z'] = daily_df.groupby('coin')['funding_rate'].transform(
    lambda x: (x - x.mean()) / x.std()
)

# Define funding buckets
daily_df['funding_bucket'] = pd.cut(
    daily_df['funding_z'],
    bins=[-np.inf, -1.5, 1.5, np.inf],
    labels=['extreme_negative', 'normal', 'extreme_positive']
)

# Split sample by time (50/50 per coin)
split_results = []
for coin in common_coins:
    coin_data = daily_df[daily_df['coin'] == coin].copy()
    n_obs = len(coin_data)
    mid_idx = n_obs // 2
    
    coin_data = coin_data.copy()
    coin_data.loc[coin_data.index[:mid_idx], 'split'] = 'first_half'
    coin_data.loc[coin_data.index[mid_idx:], 'split'] = 'second_half'
    
    split_results.append(coin_data)

daily_df = pd.concat(split_results)

print(f"\nFunding bucket counts:")
print(daily_df.groupby('funding_bucket').size())

# Question 1: Crowding -> reversal?
print("\n=== QUESTION 1: Crowding -> Reversal ===")
q1_results = []

for coin in common_coins:
    for split in ['first_half', 'second_half']:
        for bucket in ['extreme_negative', 'normal', 'extreme_positive']:
            subset = daily_df[(daily_df['coin'] == coin) & 
                             (daily_df['split'] == split) & 
                             (daily_df['funding_bucket'] == bucket)]
            
            if len(subset) >= 10:  # Minimum sample size
                q1_results.append({
                    'coin': coin,
                    'split': split,
                    'bucket': bucket,
                    'n': len(subset),
                    'mean_next_1d': subset['next_1d_return'].mean(),
                    'median_next_1d': subset['next_1d_return'].median(),
                    'mean_next_5d': subset['next_5d_return'].mean(),
                    'median_next_5d': subset['next_5d_return'].median()
                })

q1_df = pd.DataFrame(q1_results)
print(q1_df.groupby(['bucket', 'split']).agg({
    'n': 'sum',
    'mean_next_1d': 'mean',
    'median_next_1d': 'mean',
    'mean_next_5d': 'mean',
    'median_next_5d': 'mean'
}))

# Question 2: Weekday pattern
print("\n=== QUESTION 2: Weekday Funding Pattern ===")
daily_df['weekday'] = daily_df['date'].dt.dayofweek  # 0=Mon, 6=Sun

weekday_funding = daily_df.groupby(['coin', 'weekday']).agg({
    'funding_rate': 'mean',
    'next_1d_return': 'mean'
}).reset_index()

print(weekday_funding.groupby('weekday').agg({
    'funding_rate': 'mean',
    'next_1d_return': 'mean'
}))

# Question 3: Daily crashes
print("\n=== QUESTION 3: Funding Before Daily Crashes ===")
# Define 1d crash as next_1d_return <= -5% (or more extreme)
crash_threshold = -5.0
crashes = daily_df[daily_df['next_1d_return'] <= crash_threshold].copy()
print(f"Number of crashes (<= {crash_threshold}%): {len(crashes)}")

if len(crashes) > 0:
    crashes['pre_funding_bucket'] = crashes['funding_bucket']
    
    crash_funding_results = []
    for bucket in ['extreme_negative', 'normal', 'extreme_positive']:
        bucket_crashes = crashes[crashes['pre_funding_bucket'] == bucket]
        if len(bucket_crashes) >= 5:
            crash_funding_results.append({
                'bucket': bucket,
                'n_crashes': len(bucket_crashes),
                'mean_next_5d': bucket_crashes['next_5d_return'].mean(),
                'median_next_5d': bucket_crashes['next_5d_return'].median()
            })
    
    crash_funding_df = pd.DataFrame(crash_funding_results)
    print(crash_funding_df)

# Question 4: Funding mean reversion
print("\n=== QUESTION 4: Funding Mean Reversion ===")
# Calculate autocorrelation of funding rates
autocorr_results = []
for coin in common_coins:
    coin_funding = daily_df[daily_df['coin'] == coin]['funding_rate'].dropna()
    if len(coin_funding) > 10:
        autocorr_1d = coin_funding.autocorr(lag=1)
        autocorr_7d = coin_funding.autocorr(lag=7)
        autocorr_30d = coin_funding.autocorr(lag=30)
        
        autocorr_results.append({
            'coin': coin,
            'autocorr_1d': autocorr_1d,
            'autocorr_7d': autocorr_7d,
            'autocorr_30d': autocorr_30d
        })

autocorr_df = pd.DataFrame(autocorr_results)
print(autocorr_df)

# Calculate half-life of extreme funding spells
extreme_spells = []
for coin in common_coins:
    coin_data = daily_df[daily_df['coin'] == coin].copy()
    coin_data['is_extreme_pos'] = (coin_data['funding_z'] > 1.5).astype(int)
    coin_data['is_extreme_neg'] = (coin_data['funding_z'] < -1.5).astype(int)
    
    # Find consecutive extreme spells
    coin_data = coin_data.sort_values('date')
    
    # Positive extremes
    pos_spells = []
    current_spell = 0
    for is_extreme in coin_data['is_extreme_pos']:
        if is_extreme:
            current_spell += 1
        else:
            if current_spell > 0:
                pos_spells.append(current_spell)
                current_spell = 0
    
    # Negative extremes
    neg_spells = []
    current_spell = 0
    for is_extreme in coin_data['is_extreme_neg']:
        if is_extreme:
            current_spell += 1
        else:
            if current_spell > 0:
                neg_spells.append(current_spell)
                current_spell = 0
    
    if pos_spells:
        extreme_spells.append({
            'coin': coin,
            'extreme_type': 'positive',
            'n_spells': len(pos_spells),
            'avg_duration_days': np.mean(pos_spells),
            'median_duration_days': np.median(pos_spells),
            'max_duration_days': max(pos_spells)
        })
    
    if neg_spells:
        extreme_spells.append({
            'coin': coin,
            'extreme_type': 'negative',
            'n_spells': len(neg_spells),
            'avg_duration_days': np.mean(neg_spells),
            'median_duration_days': np.median(neg_spells),
            'max_duration_days': max(neg_spells)
        })

spells_df = pd.DataFrame(extreme_spells)
print("\nExtreme funding spell durations:")
print(spells_df.groupby('extreme_type').agg({
    'n_spells': 'sum',
    'avg_duration_days': 'mean',
    'median_duration_days': 'mean',
    'max_duration_days': 'max'
}))

# Save outputs
print("\nSaving outputs...")
os.makedirs('output', exist_ok=True)

# Funding patterns
q1_df.to_csv('output/funding_patterns.csv', index=False)

# Weekday funding
weekday_funding.to_csv('output/weekday_funding.csv', index=False)

# Crash funding
if len(crashes) > 0:
    crash_funding_df.to_csv('output/crash_funding.csv', index=False)

# Autocorrelation
autocorr_df.to_csv('output/funding_autocorr.csv', index=False)

# Spell durations
spells_df.to_csv('output/funding_spells.csv', index=False)

print("Analysis complete!")