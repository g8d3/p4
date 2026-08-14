#!/usr/bin/env python3
"""
Simplified volatility modeling with reduced scope for faster results
Focus on top 6 coins, 1h timeframe only
"""

import pandas as pd
import numpy as np
from arch import arch_model
from scipy import stats
from scipy.optimize import minimize
import warnings
warnings.filterwarnings('ignore')

def load_data():
    """Load candles data and compute returns"""
    print("Loading candles data...")
    df = pd.read_csv('../ag-01-data/output/candles_raw.csv')
    
    # Filter out zero-volume candles
    df = df[df['v'] > 0].copy()
    
    # Sort by coin, tf, time
    df = df.sort_values(['coin', 'tf', 't_ms'])
    
    # Compute returns per (coin, tf) group
    df['ret'] = df.groupby(['coin', 'tf'])['c'].pct_change() * 100
    df = df.dropna(subset=['ret'])
    df['abs_ret'] = df['ret'].abs()
    
    return df

def simplified_garch_fit(returns, train_size=0.5):
    """
    Simplified GARCH fit - fit once on training, use same parameters for forecasting
    Much faster than rolling refit
    """
    if len(returns) < 100:
        return None, None, None
    
    # Split data
    split_idx = int(len(returns) * train_size)
    train_ret = returns.iloc[:split_idx]
    test_ret = returns.iloc[split_idx:]
    
    try:
        # Fit GARCH(1,1) once on training data
        model = arch_model(train_ret, vol='Garch', p=1, q=1, dist='normal')
        res = model.fit(disp='off')
        
        # Use conditional variance from fitted model for test period
        # Forecast using the last volatility from training
        last_vol = res.conditional_volatility.iloc[-1]
        
        # Simple forecast: use EWMA-like decay from last training vol
        forecasts = []
        current_vol = last_vol
        
        for ret in test_ret:
            # GARCH(1,1) update: σ² = ω + α·ε² + β·σ² 
            # Simplified: use some persistence and recent shock
            omega = res.params['omega']
            alpha = res.params['alpha[1]']
            beta = res.params['beta[1]']
            
            current_var = omega + alpha * ret**2 + beta * current_vol**2
            current_vol = np.sqrt(max(current_var, 0))
            forecasts.append(current_vol)
        
        forecasts = pd.Series(forecasts, index=test_ret.index)
        
        return forecasts, test_ret.abs(), res
        
    except Exception as e:
        print(f"GARCH fit failed: {e}")
        return None, None, None

def evaluate_forecast(forecast, realized):
    """Evaluate forecast quality"""
    if forecast is None or realized is None:
        return None
    
    common_idx = forecast.index.intersection(realized.index)
    if len(common_idx) == 0:
        return None
        
    forecast_aligned = forecast.loc[common_idx]
    realized_aligned = realized.loc[common_idx]
    
    correlation = forecast_aligned.corr(realized_aligned)
    rmse = np.sqrt(((forecast_aligned - realized_aligned) ** 2).mean())
    mae = (forecast_aligned - realized_aligned).abs().mean()
    
    return {
        'correlation': correlation,
        'rmse': rmse,
        'mae': mae,
        'n_observations': len(common_idx)
    }

def simplified_gpd_tail(abs_returns, threshold_percentile=90):
    """Simplified GPD fitting for tail analysis"""
    if len(abs_returns) < 50:
        return None
    
    try:
        threshold = np.percentile(abs_returns, threshold_percentile)
        exceedances = abs_returns[abs_returns > threshold] - threshold
        
        if len(exceedances) < 10:
            return None
        
        # Use method of moments for faster GPD parameter estimation
        mean_exc = exceedances.mean()
        var_exc = exceedances.var()
        
        if var_exc <= 0:
            return None
        
        # Method of moments estimators
        xi = -0.5 * ((mean_exc**2 / var_exc) - 1)
        beta = 0.5 * mean_exc * ((mean_exc**2 / var_exc) + 1)
        
        # Bound xi to reasonable range
        xi = max(-0.5, min(0.5, xi))
        beta = max(0.001, beta)
        
        # Calculate tail probabilities
        std = abs_returns.std()
        extreme_multipliers = [3, 4, 5, 6, 7, 8, 9, 10]
        tail_probs = []
        
        for mult in extreme_multipliers:
            x = mult * std
            if x <= threshold:
                prob = (abs_returns > x).mean()
            else:
                exceedance = x - threshold
                if xi == 0:
                    tail_prob = (1 - threshold_percentile/100) * np.exp(-exceedance / beta)
                else:
                    z = 1 + xi * exceedance / beta
                    if z > 0:
                        tail_prob = (1 - threshold_percentile/100) * z ** (-1/xi)
                    else:
                        tail_prob = 0
                tail_probs.append(max(0, min(1, tail_prob)))
        
        return {
            'threshold': threshold,
            'xi': xi,
            'beta': beta,
            'n_exceedances': len(exceedances),
            'exceedance_rate': len(exceedances) / len(abs_returns),
            'tail_probs': tail_probs,
            'extreme_multipliers': extreme_multipliers
        }
        
    except Exception as e:
        print(f"GPD fit failed: {e}")
        return None

def compute_empirical_benchmark(df):
    """Compute simple empirical volatility benchmarks"""
    results = []
    
    for (coin, tf), group in df.groupby(['coin', 'tf']):
        if tf != '1h':
            continue
            
        group = group.sort_values('t_ms')
        group['next_abs_ret'] = group['abs_ret'].shift(-1)
        group['rolling_std'] = group['abs_ret'].rolling(20).std()
        group['lag_rolling_std'] = group['rolling_std'].shift(1)
        
        group = group.dropna()
        
        if len(group) > 50:
            corr = group['lag_rolling_std'].corr(group['next_abs_ret'])
            results.append({
                'coin': coin,
                'tf': tf,
                'feature': 'rolling_vol_20',
                'correlation': corr,
                'n_observations': len(group)
            })
    
    return pd.DataFrame(results)

def create_sizing_recommendations(forecast_volatility):
    """Create sizing recommendations based on vol percentiles"""
    if forecast_volatility is None or len(forecast_volatility) == 0:
        return None
    
    percentiles = [10, 25, 50, 75, 90, 95, 99]
    sizing_table = []
    
    for pct in percentiles:
        vol_threshold = np.percentile(forecast_volatility, pct)
        
        # Risk scaling: higher vol = smaller position
        # Base risk of 1% scaled inversely by vol
        base_risk = 1.0
        if vol_threshold > 0:
            position_risk = base_risk / vol_threshold
        else:
            position_risk = base_risk
        
        # Normalize so median = 1.0
        median_vol = np.percentile(forecast_volatility, 50)
        if median_vol > 0:
            normalized_risk = position_risk * median_vol / base_risk
        else:
            normalized_risk = 1.0
        
        sizing_table.append({
            'vol_percentile': pct,
            'vol_threshold': round(vol_threshold, 4),
            'risk_multiplier': round(normalized_risk, 3),
            'position_hint': f"{normalized_risk:.2f}x base size"
        })
    
    return pd.DataFrame(sizing_table)

def main():
    """Simplified main analysis"""
    print("Starting simplified volatility analysis...")
    
    # Load data
    df = load_data()
    
    # Focus on 1h timeframe only, top 6 coins by average volume
    coin_volumes = df.groupby('coin')['v'].mean().sort_values(ascending=False)
    top_coins = coin_volumes.head(6).index.tolist()
    print(f"Top coins by volume: {top_coins}")
    
    df = df[df['coin'].isin(top_coins) & (df['tf'] == '1h')].copy()
    print(f"Analyzing {len(df)} 1h candles for top {len(top_coins)} coins")
    
    all_results = []
    all_tail_results = []
    all_sizing = []
    
    for coin, group in df.groupby('coin'):
        print(f"\nProcessing {coin}...")
        group = group.sort_values('t_ms')
        returns = group['ret']
        abs_returns = group['abs_ret']
        
        if len(returns) < 200:
            print(f"  Skipping {coin} - insufficient data")
            continue
        
        # GARCH analysis
        garch_forecast, garch_realized, garch_model = simplified_garch_fit(returns)
        garch_metrics = evaluate_forecast(garch_forecast, garch_realized)
        
        if garch_metrics:
            garch_metrics.update({'coin': coin, 'tf': '1h', 'model': 'GARCH'})
            all_results.append(garch_metrics)
            print(f"  GARCH correlation: {garch_metrics['correlation']:.3f}")
        
        # EVT tail analysis
        gpd_result = simplified_gpd_tail(abs_returns)
        if gpd_result:
            tail_row = {
                'coin': coin,
                'tf': '1h',
                'threshold': round(gpd_result['threshold'], 4),
                'xi': round(gpd_result['xi'], 4),
                'beta': round(gpd_result['beta'], 4),
                'n_exceedances': gpd_result['n_exceedances'],
                'exceedance_rate': round(gpd_result['exceedance_rate'], 4)
            }
            
            for mult, prob in zip(gpd_result['extreme_multipliers'], gpd_result['tail_probs']):
                tail_row[f'p_gt_{mult}sigma'] = round(prob, 6)
            
            all_tail_results.append(tail_row)
            print(f"  GPD tail: ξ={gpd_result['xi']:.3f}, {gpd_result['n_exceedances']} exceedances")
        
        # Sizing table
        if garch_forecast is not None and len(garch_forecast) > 0:
            sizing = create_sizing_recommendations(garch_forecast)
            if sizing is not None:
                sizing['coin'] = coin
                all_sizing.append(sizing)
    
    # Save results
    print("\nSaving results...")
    
    vol_df = None
    
    if all_results:
        vol_df = pd.DataFrame(all_results)
        vol_df.to_csv('output/vol_forecast.csv', index=False)
        print(f"Saved {len(vol_df)} forecast results")
    
    if all_tail_results:
        tail_df = pd.DataFrame(all_tail_results)
        tail_df.to_csv('output/evt_tails.csv', index=False)
        print(f"Saved {len(tail_df)} tail results")
    
    if all_sizing:
        sizing_df = pd.concat(all_sizing, ignore_index=True)
        sizing_df.to_csv('output/sizing_tables.csv', index=False)
        print(f"Saved sizing tables")
    
    # Compare with empirical benchmarks
    empirical = compute_empirical_benchmark(df)
    if not empirical.empty:
        empirical.to_csv('output/empirical_benchmark.csv', index=False)
        print(f"Saved empirical benchmarks")
        
        # Head-to-head comparison
        if vol_df is not None and not vol_df.empty:
            comparison = []
            for _, garch_row in vol_df.iterrows():
                coin = garch_row['coin']
                emp_row = empirical[empirical['coin'] == coin]
                
                if not emp_row.empty:
                    emp_corr = emp_row.iloc[0]['correlation']
                    comparison.append({
                        'coin': coin,
                        'garch_correlation': garch_row['correlation'],
                        'empirical_correlation': emp_corr,
                        'garch_wins': abs(garch_row['correlation']) > abs(emp_corr),
                        'improvement': abs(garch_row['correlation']) - abs(emp_corr)
                    })
        
        if comparison:
            comp_df = pd.DataFrame(comparison)
            comp_df.to_csv('output/head_to_head.csv', index=False)
            print(f"Saved head-to-head comparison")
            print(f"\nGARCH wins in {comp_df['garch_wins'].sum()}/{len(comp_df)} cases")
            print(f"Average improvement: {comp_df['improvement'].mean():.4f}")
    
    print("\nSimplified analysis complete!")
    return True

if __name__ == "__main__":
    main()