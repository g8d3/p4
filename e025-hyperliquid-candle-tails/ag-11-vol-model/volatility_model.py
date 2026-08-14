#!/usr/bin/env python3
"""
Volatility modeling with GARCH/EGARCH and EVT for position sizing
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from arch import arch_model
from scipy import stats
from scipy.optimize import minimize
import warnings
warnings.filterwarnings('ignore')

# Set up matplotlib for better plots
plt.style.use('seaborn-v0_8')
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.size'] = 10

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
    
    # Drop first candle of each group (no return)
    df = df.dropna(subset=['ret'])
    
    # Also compute absolute returns
    df['abs_ret'] = df['ret'].abs()
    
    print(f"Loaded {len(df)} candles across {df['coin'].nunique()} coins and {df['tf'].nunique()} timeframes")
    return df

def fit_garch_forecast(returns, train_size=0.5):
    """
    Fit GARCH(1,1) model on first half, forecast on second half
    Returns forecasts and realized values
    """
    if len(returns) < 100:
        return None, None, None
    
    # Split data
    split_idx = int(len(returns) * train_size)
    train_ret = returns.iloc[:split_idx]
    test_ret = returns.iloc[split_idx:]
    
    try:
        # Fit GARCH(1,1) on training data
        model = arch_model(train_ret, vol='Garch', p=1, q=1, dist='normal')
        res = model.fit(disp='off', update_freq=5)
        
        # Generate forecasts for test period (rolling 1-step ahead)
        forecasts = []
        for i in range(len(test_ret)):
            # Use all data up to test point i
            train_plus_test = pd.concat([train_ret, test_ret.iloc[:i]])
            
            # Refit model (simplified - in production would use rolling fit)
            if len(train_plus_test) > 100:
                temp_model = arch_model(train_plus_test, vol='Garch', p=1, q=1, dist='normal')
                temp_res = temp_model.fit(disp='off')
                forecast = temp_res.forecast(horizon=1)
                forecasts.append(np.sqrt(forecast.variance.values[-1, 0]))
            else:
                # Use constant volatility if not enough data
                forecasts.append(train_ret.std())
        
        forecasts = pd.Series(forecasts, index=test_ret.index)
        
        return forecasts, test_ret.abs(), res
        
    except Exception as e:
        print(f"GARCH fit failed: {e}")
        return None, None, None

def fit_egarch_forecast(returns, train_size=0.5):
    """
    Fit EGARCH(1,1) model on first half, forecast on second half
    Returns forecasts and realized values
    """
    if len(returns) < 100:
        return None, None, None
    
    # Split data
    split_idx = int(len(returns) * train_size)
    train_ret = returns.iloc[:split_idx]
    test_ret = returns.iloc[split_idx:]
    
    try:
        # Fit EGARCH(1,1) on training data
        model = arch_model(train_ret, vol='EGARCH', p=1, q=1, dist='normal')
        res = model.fit(disp='off', update_freq=5)
        
        # Generate forecasts for test period (rolling 1-step ahead)
        forecasts = []
        for i in range(len(test_ret)):
            # Use all data up to test point i
            train_plus_test = pd.concat([train_ret, test_ret.iloc[:i]])
            
            # Refit model (simplified)
            if len(train_plus_test) > 100:
                temp_model = arch_model(train_plus_test, vol='EGARCH', p=1, q=1, dist='normal')
                temp_res = temp_model.fit(disp='off')
                forecast = temp_res.forecast(horizon=1)
                forecasts.append(np.sqrt(forecast.variance.values[-1, 0]))
            else:
                forecasts.append(train_ret.std())
        
        forecasts = pd.Series(forecasts, index=test_ret.index)
        
        return forecasts, test_ret.abs(), res
        
    except Exception as e:
        print(f"EGARCH fit failed: {e}")
        return None, None, None

def evaluate_forecast(forecast, realized):
    """Evaluate forecast quality"""
    if forecast is None or realized is None:
        return None
    
    # Align the series
    common_idx = forecast.index.intersection(realized.index)
    forecast = forecast.loc[common_idx]
    realized = realized.loc[common_idx]
    
    # Calculate metrics
    correlation = forecast.corr(realized)
    rmse = np.sqrt(((forecast - realized) ** 2).mean())
    mae = (forecast - realized).abs().mean()
    
    # Direction accuracy
    forecast_change = forecast.diff().dropna()
    realized_change = realized.diff().dropna()
    common_change_idx = forecast_change.index.intersection(realized_change.index)
    
    if len(common_change_idx) > 0:
        forecast_dir = np.sign(forecast_change.loc[common_change_idx])
        realized_dir = np.sign(realized_change.loc[common_change_idx])
        direction_accuracy = (forecast_dir == realized_dir).mean()
    else:
        direction_accuracy = np.nan
    
    return {
        'correlation': correlation,
        'rmse': rmse,
        'mae': mae,
        'direction_accuracy': direction_accuracy,
        'n_observations': len(common_idx)
    }

def fit_gpd_tail(abs_returns, threshold_percentile=90):
    """
    Fit Generalized Pareto Distribution to tails using Peaks-Over-Threshold
    Returns GPD parameters and tail quantiles
    """
    if len(abs_returns) < 50:
        return None
    
    try:
        # Select tail observations (exceedances above threshold)
        threshold = np.percentile(abs_returns, threshold_percentile)
        exceedances = abs_returns[abs_returns > threshold] - threshold
        
        if len(exceedances) < 10:  # Need enough tail samples
            return None
        
        # Fit GPD using MLE
        def neg_log_likelihood(params, data):
            xi, beta = params
            if beta <= 0:
                return np.inf
            
            n = len(data)
            
            # Handle different xi cases
            if xi == 0:
                # Exponential case
                log_lik = -n * np.log(beta) - np.sum(data) / beta
            else:
                # General case
                z = 1 + xi * data / beta
                if np.any(z <= 0):
                    return np.inf
                log_lik = -n * np.log(beta) - (1 + 1/xi) * np.sum(np.log(z))
            
            return -log_lik
        
        # Optimize parameters (xi, beta)
        result = minimize(
            neg_log_likelihood,
            x0=[0.1, np.std(exceedances)],
            args=(exceedances,),
            method='L-BFGS-B',
            bounds=[(-0.5, 0.5), (0.001, None)]
        )
        
        if not result.success:
            return None
        
        xi, beta = result.x
        
        # Calculate tail quantiles that empirical data can't reach
        # P(|ret| > x) for various x values in terms of sigma
        std = abs_returns.std()
        extreme_multipliers = [3, 4, 5, 6, 7, 8, 9, 10]
        tail_probs = []
        
        for mult in extreme_multipliers:
            x = mult * std
            if x <= threshold:
                # Below threshold, use empirical
                prob = (abs_returns > x).mean()
            else:
                # Above threshold, use GPD
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
            'xi': xi,  # Shape parameter
            'beta': beta,  # Scale parameter
            'n_exceedances': len(exceedances),
            'exceedance_rate': len(exceedances) / len(abs_returns),
            'tail_probs': tail_probs,
            'extreme_multipliers': extreme_multipliers,
            'threshold_percentile': threshold_percentile
        }
        
    except Exception as e:
        print(f"GPD fit failed: {e}")
        return None

def compute_empirical_features(df):
    """Compute simple empirical volatility features for comparison"""
    features = []
    
    for (coin, tf), group in df.groupby(['coin', 'tf']):
        group = group.sort_values('t_ms').copy()
        
        # Volume percentile (rolling)
        group['vol_pct'] = group['v'].rolling(window=20).rank(pct=True)
        
        # Cooloff (time since last large move)
        large_move_threshold = group['abs_ret'].quantile(0.9)
        group['large_move'] = (group['abs_ret'] > large_move_threshold).astype(int)
        group['cooloff'] = group['large_move'].replace(0, np.nan).ffill().fillna(0)
        
        # Hour of day (for intraday)
        if tf in ['5m', '15m', '1h']:
            group['hour'] = (pd.to_datetime(group['t_ms'], unit='ms').dt.hour)
        else:
            group['hour'] = 0
        
        features.append(group)
    
    return pd.concat(features)

def evaluate_empirical_predictions(df):
    """Evaluate how well empirical features predict next-candle volatility"""
    results = []
    
    for (coin, tf), group in df.groupby(['coin', 'tf']):
        group = group.sort_values('t_ms').copy()
        
        # Create lagged features
        group['next_abs_ret'] = group['abs_ret'].shift(-1)
        group['lag_vol_pct'] = group['vol_pct'].shift(1)
        group['lag_cooloff'] = group['cooloff'].shift(1)
        group['lag_hour'] = group['hour'].shift(1)
        
        group = group.dropna()
        
        if len(group) < 50:
            continue
        
        # Evaluate each feature
        features_to_test = ['lag_vol_pct', 'lag_cooloff', 'lag_hour']
        
        for feature in features_to_test:
            corr = group[feature].corr(group['next_abs_ret'])
            results.append({
                'coin': coin,
                'tf': tf,
                'feature': feature,
                'correlation': corr,
                'n_observations': len(group)
            })
    
    return pd.DataFrame(results)

def create_sizing_table(forecast_volatility, base_risk_pct=1.0):
    """
    Create position sizing table based on forecast volatility percentiles
    Returns table showing risk multiplier for different vol percentiles
    """
    if forecast_volatility is None or len(forecast_volatility) == 0:
        return None
    
    # Calculate percentiles of forecast volatility
    percentiles = [10, 25, 50, 75, 90, 95, 99]
    sizing_table = []
    
    for pct in percentiles:
        vol_threshold = np.percentile(forecast_volatility, pct)
        
        # Risk multiplier scales inversely with volatility (fixed-fractional)
        # Higher vol -> smaller position -> lower risk multiplier
        if vol_threshold > 0:
            risk_multiplier = base_risk_pct / vol_threshold
        else:
            risk_multiplier = base_risk_pct
        
        # Normalize so median = 1.0
        median_vol = np.percentile(forecast_volatility, 50)
        if median_vol > 0:
            normalized_multiplier = risk_multiplier * median_vol / base_risk_pct
        else:
            normalized_multiplier = 1.0
        
        sizing_table.append({
            'vol_percentile': pct,
            'vol_threshold': vol_threshold,
            'risk_multiplier': risk_multiplier,
            'normalized_multiplier': normalized_multiplier,
            'position_size_hint': f"{normalized_multiplier:.2f}x base"
        })
    
    return pd.DataFrame(sizing_table)

def main():
    """Main analysis pipeline"""
    print("Starting volatility modeling analysis...")
    
    # Load data
    df = load_data()
    
    # Focus on 1h timeframe primarily, as specified
    target_timeframes = ['1h', '1d']
    
    all_results = []
    all_tail_results = []
    all_head_to_head = []
    
    for (coin, tf), group in df.groupby(['coin', 'tf']):
        if tf not in target_timeframes:
            continue
            
        print(f"\nProcessing {coin} {tf}...")
        group = group.sort_values('t_ms')
        returns = group['ret'].dropna()
        abs_returns = group['abs_ret'].dropna()
        
        if len(returns) < 200:
            print(f"  Skipping {coin} {tf} - insufficient data ({len(returns)} obs)")
            continue
        
        # 1. GARCH forecasting
        garch_forecast, garch_realized, garch_model = fit_garch_forecast(returns)
        garch_metrics = evaluate_forecast(garch_forecast, garch_realized)
        
        # 2. EGARCH forecasting
        egarch_forecast, egarch_realized, egarch_model = fit_egarch_forecast(returns)
        egarch_metrics = evaluate_forecast(egarch_forecast, egarch_realized)
        
        # Store results
        if garch_metrics:
            garch_metrics.update({'coin': coin, 'tf': tf, 'model': 'GARCH'})
            all_results.append(garch_metrics)
        
        if egarch_metrics:
            egarch_metrics.update({'coin': coin, 'tf': tf, 'model': 'EGARCH'})
            all_results.append(egarch_metrics)
        
        # 3. EVT tail analysis
        gpd_result = fit_gpd_tail(abs_returns, threshold_percentile=90)
        if gpd_result:
            tail_row = {
                'coin': coin,
                'tf': tf,
                'threshold': gpd_result['threshold'],
                'xi': gpd_result['xi'],
                'beta': gpd_result['beta'],
                'n_exceedances': gpd_result['n_exceedances'],
                'exceedance_rate': gpd_result['exceedance_rate']
            }
            
            # Add extreme quantiles
            for mult, prob in zip(gpd_result['extreme_multipliers'], gpd_result['tail_probs']):
                tail_row[f'p_gt_{mult}sigma'] = prob
            
            all_tail_results.append(tail_row)
        
        # 4. Generate sizing table for best model
        best_forecast = garch_forecast if garch_metrics and garch_metrics['correlation'] > 0 else egarch_forecast
        if best_forecast is not None and len(best_forecast) > 0:
            sizing_table = create_sizing_table(best_forecast)
            if sizing_table is not None:
                sizing_table['coin'] = coin
                sizing_table['tf'] = tf
                all_head_to_head.append(sizing_table)
    
    # Save results
    print("\nSaving results...")
    
    # Volatility forecast results
    if all_results:
        vol_results_df = pd.DataFrame(all_results)
        vol_results_df.to_csv('output/vol_forecast.csv', index=False)
        print(f"Saved {len(vol_results_df)} forecast results to output/vol_forecast.csv")
    
    # EVT tail results
    if all_tail_results:
        tail_results_df = pd.DataFrame(all_tail_results)
        tail_results_df.to_csv('output/evt_tails.csv', index=False)
        print(f"Saved {len(tail_results_df)} tail results to output/evt_tails.csv")
    
    # Combine all sizing tables
    if all_head_to_head:
        combined_sizing = pd.concat(all_head_to_head, ignore_index=True)
        combined_sizing.to_csv('output/sizing_tables.csv', index=False)
        print(f"Saved sizing tables to output/sizing_tables.csv")
    
    # 5. Head-to-head comparison with empirical features
    print("\nComputing empirical feature comparison...")
    df_with_features = compute_empirical_features(df)
    empirical_results = evaluate_empirical_predictions(df_with_features)
    
    if not empirical_results.empty:
        empirical_results.to_csv('output/empirical_features.csv', index=False)
        print(f"Saved empirical feature results to output/empirical_features.csv")
        
        # Compare best model vs empirical features
        if all_results:
            comparison_results = []
            for model_result in all_results:
                coin = model_result['coin']
                tf = model_result['tf']
                
                # Get best empirical feature for this coin/tf
                emp_subset = empirical_results[
                    (empirical_results['coin'] == coin) & 
                    (empirical_results['tf'] == tf)
                ]
                
                if not emp_subset.empty:
                    best_emp = emp_subset.loc[emp_subset['correlation'].abs().idxmax()]
                    comparison_results.append({
                        'coin': coin,
                        'tf': tf,
                        'model': model_result['model'],
                        'model_correlation': model_result['correlation'],
                        'best_feature': best_emp['feature'],
                        'feature_correlation': best_emp['correlation'],
                        'model_wins': abs(model_result['correlation']) > abs(best_emp['correlation'])
                    })
            
            if comparison_results:
                comparison_df = pd.DataFrame(comparison_results)
                comparison_df.to_csv('output/head_to_head.csv', index=False)
                print(f"Saved head-to-head comparison to output/head_to_head.csv")
    
    # 6. Generate charts
    print("\nGenerating charts...")
    generate_charts(df, all_results, all_tail_results)
    
    print("\nAnalysis complete!")
    return True

def generate_charts(df, forecast_results, tail_results):
    """Generate visualization charts"""
    
    # Chart 1: Volatility forecast vs realized scatter plot
    if forecast_results:
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        axes = axes.flatten()
        
        plot_idx = 0
        for (coin, tf), group in df.groupby(['coin', 'tf']):
            if tf not in ['1h', '1d']:
                continue
            if plot_idx >= 4:
                break
                
            group = group.sort_values('t_ms')
            returns = group['ret'].dropna()
            
            if len(returns) < 200:
                continue
                
            garch_forecast, garch_realized, _ = fit_garch_forecast(returns)
            
            if garch_forecast is not None and garch_realized is not None:
                common_idx = garch_forecast.index.intersection(garch_realized.index)
                if len(common_idx) > 10:
                    axes[plot_idx].scatter(
                        garch_forecast.loc[common_idx], 
                        garch_realized.loc[common_idx],
                        alpha=0.5, s=20
                    )
                    axes[plot_idx].plot([0, garch_forecast.max()], [0, garch_forecast.max()], 
                                      'r--', label='Perfect forecast')
                    axes[plot_idx].set_xlabel('Forecast Volatility (%)')
                    axes[plot_idx].set_ylabel('Realized |Return| (%)')
                    axes[plot_idx].set_title(f'{coin} {tf}: GARCH Forecast vs Realized')
                    axes[plot_idx].legend()
                    axes[plot_idx].grid(True, alpha=0.3)
                    
                    # Add correlation
                    corr = garch_forecast.loc[common_idx].corr(garch_realized.loc[common_idx])
                    axes[plot_idx].text(0.05, 0.95, f'corr = {corr:.3f}', 
                                      transform=axes[plot_idx].transAxes,
                                      verticalalignment='top',
                                      bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
                    
                    plot_idx += 1
        
        plt.tight_layout()
        plt.savefig('output/charts/vol_forecast_scatter.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("Saved vol_forecast_scatter.png")
    
    # Chart 2: Tail fit plots
    if tail_results:
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        axes = axes.flatten()
        
        plot_idx = 0
        for (coin, tf), group in df.groupby(['coin', 'tf']):
            if tf not in ['1h', '1d']:
                continue
            if plot_idx >= 4:
                break
                
            abs_returns = group['abs_ret'].dropna()
            
            if len(abs_returns) < 200:
                continue
                
            gpd_result = fit_gpd_tail(abs_returns, threshold_percentile=90)
            
            if gpd_result:
                # Plot empirical tail vs GPD fit
                sorted_abs = np.sort(abs_returns)
                threshold = gpd_result['threshold']
                exceedances = sorted_abs[sorted_abs > threshold] - threshold
                
                # Empirical exceedances
                empirical_sorted = np.sort(exceedances)
                n = len(empirical_sorted)
                empirical_cdf = np.arange(1, n+1) / n
                
                # GPD CDF
                xi, beta = gpd_result['xi'], gpd_result['beta']
                x_range = np.linspace(0, empirical_sorted.max() * 1.2, 100)
                
                if xi == 0:
                    gpd_cdf = 1 - np.exp(-x_range / beta)
                else:
                    z = 1 + xi * x_range / beta
                    gpd_cdf = 1 - z ** (-1/xi)
                    gpd_cdf = np.clip(gpd_cdf, 0, 1)
                
                axes[plot_idx].plot(empirical_sorted, empirical_cdf, 'bo', 
                                  label='Empirical exceedances', alpha=0.6, markersize=4)
                axes[plot_idx].plot(x_range, gpd_cdf, 'r-', label=f'GPD fit (ξ={xi:.3f}, β={beta:.3f})', linewidth=2)
                axes[plot_idx].set_xlabel('Exceedance above threshold (%)')
                axes[plot_idx].set_ylabel('CDF')
                axes[plot_idx].set_title(f'{coin} {tf}: GPD Tail Fit')
                axes[plot_idx].legend()
                axes[plot_idx].grid(True, alpha=0.3)
                
                plot_idx += 1
        
        plt.tight_layout()
        plt.savefig('output/charts/tail_fit_plot.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("Saved tail_fit_plot.png")
    
    # Chart 3: Sizing curve
    sizing_df = pd.read_csv('output/sizing_tables.csv')
    if not sizing_df.empty:
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        axes = axes.flatten()
        
        plot_idx = 0
        for (coin, tf), group in sizing_df.groupby(['coin', 'tf']):
            if plot_idx >= 4:
                break
                
            axes[plot_idx].plot(group['vol_percentile'], group['normalized_multiplier'], 
                              'o-', linewidth=2, markersize=8)
            axes[plot_idx].set_xlabel('Forecast Volatility Percentile')
            axes[plot_idx].set_ylabel('Risk Multiplier (normalized)')
            axes[plot_idx].set_title(f'{coin} {tf}: Position Sizing Curve')
            axes[plot_idx].grid(True, alpha=0.3)
            axes[plot_idx].axhline(y=1.0, color='r', linestyle='--', alpha=0.5, label='Baseline (median vol)')
            axes[plot_idx].legend()
            
            # Add percentile labels
            for _, row in group.iterrows():
                axes[plot_idx].text(row['vol_percentile'], row['normalized_multiplier'], 
                                   f"{row['normalized_multiplier']:.2f}x", 
                                   ha='center', va='bottom', fontsize=8)
            
            plot_idx += 1
        
        plt.tight_layout()
        plt.savefig('output/charts/sizing_curve.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("Saved sizing_curve.png")
    
    # Chart 4: Model comparison summary
    if forecast_results:
        forecast_df = pd.DataFrame(forecast_results)
        
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        
        # Correlation comparison
        garch_corr = forecast_df[forecast_df['model'] == 'GARCH']['correlation']
        egarch_corr = forecast_df[forecast_df['model'] == 'EGARCH']['correlation']
        
        axes[0].hist([garch_corr.dropna(), egarch_corr.dropna()], 
                    bins=10, alpha=0.7, label=['GARCH', 'EGARCH'])
        axes[0].set_xlabel('Correlation (forecast vs realized)')
        axes[0].set_ylabel('Frequency')
        axes[0].set_title('Model Correlation Distribution')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # RMSE comparison
        garch_rmse = forecast_df[forecast_df['model'] == 'GARCH']['rmse']
        egarch_rmse = forecast_df[forecast_df['model'] == 'EGARCH']['rmse']
        
        axes[1].hist([garch_rmse.dropna(), egarch_rmse.dropna()], 
                    bins=10, alpha=0.7, label=['GARCH', 'EGARCH'])
        axes[1].set_xlabel('RMSE (forecast vs realized)')
        axes[1].set_ylabel('Frequency')
        axes[1].set_title('Model RMSE Distribution')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('output/charts/model_comparison.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("Saved model_comparison.png")

if __name__ == "__main__":
    main()