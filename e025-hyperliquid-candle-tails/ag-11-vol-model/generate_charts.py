#!/usr/bin/env python3
"""
Generate visualization charts for volatility model analysis
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

# Set up matplotlib for better plots
plt.style.use('seaborn-v0_8')
plt.rcParams['figure.figsize'] = (14, 10)
plt.rcParams['font.size'] = 10

def generate_charts():
    """Generate all required charts"""
    
    # Load data
    try:
        vol_df = pd.read_csv('output/vol_forecast.csv')
        tail_df = pd.read_csv('output/evt_tails.csv')
        comparison_df = pd.read_csv('output/head_to_head.csv')
        sizing_df = pd.read_csv('output/sizing_tables.csv')
    except Exception as e:
        print(f"Error loading data: {e}")
        return
    
    # Chart 1: GARCH vs Empirical Correlation Comparison
    fig, ax = plt.subplots(figsize=(12, 6))
    
    coins = comparison_df['coin']
    garch_corr = comparison_df['garch_correlation']
    emp_corr = comparison_df['empirical_correlation']
    
    x = np.arange(len(coins))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, garch_corr, width, label='GARCH(1,1)', color='steelblue', alpha=0.8)
    bars2 = ax.bar(x + width/2, emp_corr, width, label='Rolling 20-period Vol', color='coral', alpha=0.8)
    
    ax.set_ylabel('Correlation with Realized |Return|')
    ax.set_title('GARCH vs Empirical Volatility Forecasting: Head-to-Head Comparison')
    ax.set_xticks(x)
    ax.set_xticklabels(coins, rotation=45, ha='right')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_ylim([0, 0.8])
    
    # Add improvement labels
    for i, (g, e) in enumerate(zip(garch_corr, emp_corr)):
        improvement = g - e
        ax.annotate(f'+{improvement:.3f}', xy=(i, max(g, e) + 0.02), 
                   ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('output/charts/model_comparison.png', dpi=150, bbox_inches='tight')
    print("✓ Saved model_comparison.png")
    plt.close()
    
    # Chart 2: EVT Tail Shape Parameters
    fig, ax = plt.subplots(figsize=(12, 6))
    
    coins = tail_df['coin']
    xi_values = tail_df['xi']
    
    colors = ['red' if xi > 0.1 else 'orange' if xi > 0 else 'green' for xi in xi_values]
    bars = ax.bar(coins, xi_values, color=colors, alpha=0.7, edgecolor='black')
    
    ax.set_ylabel('ξ (Shape Parameter)')
    ax.set_title('EVT Tail Shape Parameter by Coin\nξ > 0 = Fat Tails (More Extreme Moves Than Normal)')
    ax.set_xlabel('Coin')
    ax.axhline(y=0, color='black', linestyle='--', linewidth=1, alpha=0.5)
    ax.axhline(y=0.1, color='red', linestyle=':', linewidth=1, alpha=0.5, label='ξ = 0.1 (Very Fat Tails)')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    # Add value labels
    for bar, xi in zip(bars, xi_values):
        height = bar.get_height()
        ax.annotate(f'{xi:.3f}', xy=(bar.get_x() + bar.get_width()/2, height),
                   xytext=(0, 3), textcoords='offset points',
                   ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('output/charts/tail_shape_parameters.png', dpi=150, bbox_inches='tight')
    print("✓ Saved tail_shape_parameters.png")
    plt.close()
    
    # Chart 3: Extreme Move Probabilities
    fig, ax = plt.subplots(figsize=(12, 6))
    
    multipliers = [3, 4, 5, 6, 7, 8, 9, 10]
    
    for coin in tail_df['coin']:
        coin_data = tail_df[tail_df['coin'] == coin].iloc[0]
        probs = [coin_data[f'p_gt_{m}sigma'] for m in multipliers]
        
        ax.plot(multipliers, probs, marker='o', linewidth=2, markersize=8, label=coin)
    
    ax.set_xlabel('Extreme Move Threshold (σ)')
    ax.set_ylabel('Probability P(|Return| > xσ)')
    ax.set_title('EVT: Probability of Extreme Moves by Threshold\n(Warning: 5σ+ events are much more likely than normal distribution)')
    ax.set_yscale('log')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Add normal distribution reference line
    normal_probs = [2 * (1 - stats.norm.cdf(m)) for m in multipliers]
    ax.plot(multipliers, normal_probs, 'k--', linewidth=1.5, alpha=0.5, label='Normal Distribution')
    
    plt.tight_layout()
    plt.savefig('output/charts/extreme_probabilities.png', dpi=150, bbox_inches='tight')
    print("✓ Saved extreme_probabilities.png")
    plt.close()
    
    # Chart 4: Position Sizing Curves
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    axes = axes.flatten()
    
    for idx, coin in enumerate(sizing_df['coin'].unique()):
        coin_sizing = sizing_df[sizing_df['coin'] == coin]
        
        ax = axes[idx]
        ax.plot(coin_sizing['vol_percentile'], coin_sizing['risk_multiplier'], 
               'o-', linewidth=2, markersize=8, color='steelblue')
        ax.fill_between(coin_sizing['vol_percentile'], coin_sizing['risk_multiplier'], 
                       alpha=0.3, color='steelblue')
        
        ax.set_xlabel('Forecast Volatility Percentile')
        ax.set_ylabel('Risk Multiplier (normalized)')
        ax.set_title(f'{coin}: Position Sizing by Volatility')
        ax.grid(True, alpha=0.3)
        ax.axhline(y=1.0, color='red', linestyle='--', alpha=0.5, label='Baseline (median)')
        ax.legend()
        
        # Add percentile labels
        for _, row in coin_sizing.iterrows():
            ax.annotate(f"{row['risk_multiplier']:.2f}x", 
                       xy=(row['vol_percentile'], row['risk_multiplier']),
                       xytext=(0, 5), textcoords='offset points',
                       ha='center', va='bottom', fontsize=7)
    
    plt.tight_layout()
    plt.savefig('output/charts/sizing_curves.png', dpi=150, bbox_inches='tight')
    print("✓ Saved sizing_curves.png")
    plt.close()
    
    # Chart 5: Combined Volatility Forecast Performance
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Left: Correlation distribution
    ax1 = axes[0]
    ax1.hist([garch_corr, emp_corr], bins=8, alpha=0.7, 
            label=['GARCH', 'Empirical'], color=['steelblue', 'coral'])
    ax1.set_xlabel('Correlation (forecast vs realized)')
    ax1.set_ylabel('Frequency')
    ax1.set_title('Distribution of Forecast Correlations')
    ax1.legend()
    ax1.grid(True, alpha=0.3, axis='y')
    
    # Right: Improvement scatter
    ax2 = axes[1]
    ax2.scatter(emp_corr, garch_corr, s=100, alpha=0.7, c='steelblue', edgecolors='black')
    
    # Add diagonal line (equal performance)
    max_corr = max(max(emp_corr), max(garch_corr))
    ax2.plot([0, max_corr], [0, max_corr], 'r--', linewidth=1, alpha=0.5, label='Equal Performance')
    
    # Add coin labels
    for i, coin in enumerate(coins):
        ax2.annotate(coin, (emp_corr.iloc[i], garch_corr.iloc[i]),
                    xytext=(5, 5), textcoords='offset points', fontsize=9)
    
    ax2.set_xlabel('Empirical Correlation')
    ax2.set_ylabel('GARCH Correlation')
    ax2.set_title('GARCH vs Empirical: Performance Scatter')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('output/charts/performance_summary.png', dpi=150, bbox_inches='tight')
    print("✓ Saved performance_summary.png")
    plt.close()

if __name__ == "__main__":
    print("Generating visualization charts...")
    generate_charts()
    print("All charts generated successfully!")