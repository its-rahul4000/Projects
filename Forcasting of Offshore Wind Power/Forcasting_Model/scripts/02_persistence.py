"""
EN639 Project: Offshore Wind Power Forecasting
Script 02: The Persistence Model (Train: 2010-2020, Test: 2022)
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import mean_squared_error, mean_absolute_error, mean_absolute_percentage_error
import os
import warnings
warnings.filterwarnings("ignore")

def run_persistence_model():
    """Enhanced persistence model with train (2010-2020) and test (2022) split"""
    
    print("="*70)
    print("ENHANCED PERSISTENCE MODEL ANALYSIS")
    print("="*70)
    print("Training Period: 2010-2020")
    print("Testing Period: 2022")
    print("="*70)
    
    os.makedirs('../outputs/figures', exist_ok=True)
    os.makedirs('../outputs/metrics', exist_ok=True)

    # Load data
    file_path = '../data/processed/UK_OFF_hourly_2010_2022.csv'
    df = pd.read_csv(file_path, parse_dates=['time'], index_col='time')
    
    print(f"\nData loaded: {len(df)} hours from {df.index[0]} to {df.index[-1]}")
    
    # Define test periods for 2022 only
    test_periods = {
        'Full Year 2022': ('2022-01-01', '2022-12-31'),
        'Q1 2022 (Winter)': ('2022-01-01', '2022-03-31'),
        'Q2 2022 (Spring)': ('2022-04-01', '2022-06-30'),
        'Q3 2022 (Summer)': ('2022-07-01', '2022-09-30'),
        'Q4 2022 (Fall)': ('2022-10-01', '2022-12-31'),
    }
    
    # Test different persistence horizons
    horizons = [1, 3, 6, 12, 24]  # hours
    
    all_results = {}
    
    for period_name, (start_date, end_date) in test_periods.items():
        print(f"\n{'='*60}")
        print(f"Testing: {period_name}")
        print(f"{'='*60}")
        
        test_data = df.loc[start_date:end_date].copy()
        
        period_results = {}
        
        for horizon in horizons:
            test_data[f'Forecast_{horizon}h'] = test_data['UK_OFF'].shift(horizon)
            test_data_clean = test_data.dropna()
            
            actual = test_data_clean['UK_OFF']
            predicted = test_data_clean[f'Forecast_{horizon}h']
            
            mae = mean_absolute_error(actual, predicted)
            rmse = np.sqrt(mean_squared_error(actual, predicted))
            mape = mean_absolute_percentage_error(actual, predicted) * 100
            
            period_results[horizon] = {
                'MAE': mae,
                'RMSE': rmse,
                'MAPE': mape,
                'samples': len(actual)
            }
            
            print(f"\nHorizon: {horizon} hour{'s' if horizon > 1 else ''}")
            print(f"  MAE:  {mae:.4f}")
            print(f"  RMSE: {rmse:.4f}")
            print(f"  MAPE: {mape:.2f}%")
            print(f"  Samples: {len(actual):,}")
        
        all_results[period_name] = period_results
    
    # Standard persistence (1-hour) for full year
    print("\n" + "="*70)
    print("STANDARD PERSISTENCE MODEL (1-HOUR HORIZON) - TEST 2022")
    print("="*70)
    
    test_data_full = df.loc['2022-01-01':'2022-12-31'].copy()
    test_data_full['Forecast_1hr'] = test_data_full['UK_OFF'].shift(1)
    test_data_full = test_data_full.dropna()
    
    actual_full = test_data_full['UK_OFF']
    predicted_full = test_data_full['Forecast_1hr']
    
    mae_full = mean_absolute_error(actual_full, predicted_full)
    rmse_full = np.sqrt(mean_squared_error(actual_full, predicted_full))
    mape_full = mean_absolute_percentage_error(actual_full, predicted_full) * 100
    
    print(f"\nFull Year 2022 Results:")
    print(f"  MAE:  {mae_full:.4f}")
    print(f"  RMSE: {rmse_full:.4f}")
    print(f"  MAPE: {mape_full:.2f}%")
    
    # Save results
    with open('../outputs/metrics/persistence_metrics_2022.txt', 'w') as f:
        f.write("PERSISTENCE MODEL RESULTS\n")
        f.write("="*50 + "\n\n")
        f.write(f"Training Period: 2010-2020\n")
        f.write(f"Testing Period: 2022\n\n")
        f.write(f"Full Year 2022 (1-hour horizon):\n")
        f.write(f"  MAE: {mae_full:.4f}\n")
        f.write(f"  RMSE: {rmse_full:.4f}\n")
        f.write(f"  MAPE: {mape_full:.2f}%\n\n")
        
        f.write("Horizon-wise Performance (Full Year 2022):\n")
        for h in horizons:
            res = all_results['Full Year 2022'][h]
            f.write(f"  {h}h: MAE={res['MAE']:.4f}, RMSE={res['RMSE']:.4f}, MAPE={res['MAPE']:.2f}%\n")
    
    # Visualization
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    
    # Plot 1: 10-day sample
    ax1 = axes[0, 0]
    plot_window = test_data_full.loc['2022-03-01':'2022-03-10']
    ax1.plot(plot_window.index, plot_window['UK_OFF'], label='Actual', color='blue', linewidth=2)
    ax1.plot(plot_window.index, plot_window['Forecast_1hr'], label='Persistence (1h)', 
             color='orange', linestyle='--', linewidth=2)
    ax1.set_title('Persistence Model - 10-Day Sample (March 2022)')
    ax1.set_ylabel('Capacity Factor')
    ax1.set_xlabel('Date')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Error by hour of day
    ax2 = axes[0, 1]
    test_data_full_copy = test_data_full.copy()
    test_data_full_copy['hour'] = test_data_full_copy.index.hour
    test_data_full_copy['error'] = np.abs(test_data_full_copy['UK_OFF'] - test_data_full_copy['Forecast_1hr'])
    hourly_error = test_data_full_copy.groupby('hour')['error'].mean()
    ax2.bar(hourly_error.index, hourly_error.values, color='steelblue', alpha=0.7)
    ax2.set_title('Prediction Error by Hour of Day')
    ax2.set_xlabel('Hour')
    ax2.set_ylabel('Mean Absolute Error')
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Horizon comparison
    ax3 = axes[1, 0]
    horizons_list = list(all_results['Full Year 2022'].keys())
    rmse_values = [all_results['Full Year 2022'][h]['RMSE'] for h in horizons_list]
    ax3.plot(horizons_list, rmse_values, 'bo-', linewidth=2, markersize=8)
    ax3.set_title('RMSE vs Prediction Horizon (Test 2022)')
    ax3.set_xlabel('Prediction Horizon (hours)')
    ax3.set_ylabel('RMSE')
    ax3.grid(True, alpha=0.3)
    
    # Plot 4: Seasonal comparison
    ax4 = axes[1, 1]
    seasons = ['Winter', 'Spring', 'Summer', 'Fall']
    seasonal_rmse = [all_results[f'Q{i+1} 2022 ({seasons[i]})'][1]['RMSE'] for i in range(4)]
    colors = ['lightblue', 'lightgreen', 'lightcoral', 'orange']
    ax4.bar(seasons, seasonal_rmse, color=colors, alpha=0.7)
    ax4.set_title('Seasonal RMSE Performance (Test 2022)')
    ax4.set_ylabel('RMSE')
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    fig_path = '../outputs/figures/persistence_enhanced_analysis.png'
    plt.savefig(fig_path, dpi=300)
    print(f"\n[OK] Saved enhanced persistence analysis to: {fig_path}")
    
    return all_results, mae_full, rmse_full

if __name__ == "__main__":
    results, mae, rmse = run_persistence_model()