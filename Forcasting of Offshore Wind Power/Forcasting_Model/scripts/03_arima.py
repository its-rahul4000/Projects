"""
EN639 Project: Offshore Wind Power Forecasting
Script 03: ARIMA - Train: 2010-2020, Test: 2022
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.graphics.tsaplots import plot_acf
from statsmodels.stats.diagnostic import acorr_ljungbox
from sklearn.metrics import mean_squared_error, mean_absolute_error, mean_absolute_percentage_error
import warnings
from itertools import product
import os

warnings.filterwarnings("ignore")

def find_best_arima(train_data, max_p=3, max_d=2, max_q=3):
    """Find best ARIMA parameters using AIC"""
    print("\n" + "="*60)
    print("AUTOMATIC ARIMA PARAMETER SELECTION")
    print("="*60)
    
    best_aic = np.inf
    best_order = None
    results = []
    
    p_values = range(0, max_p+1)
    d_values = range(0, max_d+1)
    q_values = range(0, max_q+1)
    
    total_combinations = len(p_values) * len(d_values) * len(q_values)
    print(f"Testing {total_combinations} parameter combinations...")
    
    for p, d, q in product(p_values, d_values, q_values):
        if p == 0 and q == 0:
            continue
            
        try:
            model = ARIMA(train_data, order=(p, d, q))
            fitted = model.fit()
            aic = fitted.aic
            
            results.append({'order': f'({p},{d},{q})', 'AIC': aic})
            
            if aic < best_aic:
                best_aic = aic
                best_order = (p, d, q)
                
            print(f"  ARIMA{(p,d,q)}: AIC={aic:.1f}")
        except:
            continue
    
    results_df = pd.DataFrame(results).sort_values('AIC')
    
    print(f"\n[OK] Best model: ARIMA{best_order} with AIC={best_aic:.1f}")
    
    return best_order, results_df

def run_arima_model():
    """ARIMA model with training 2010-2020 and testing 2022"""
    
    print("="*70)
    print("ENHANCED ARIMA MODELING")
    print("="*70)
    print("Training Period: 2010-2020")
    print("Testing Period: 2022")
    print("="*70)
    
    file_path = '../data/processed/UK_OFF_hourly_2010_2022.csv'
    df = pd.read_csv(file_path, parse_dates=['time'], index_col='time')
    
    # Train: 2010-2020, Test: 2022
    train_data = df.loc['2010-01-01':'2020-12-31']['UK_OFF']
    test_data = df.loc['2022-01-01':'2022-12-31']['UK_OFF']
    
    print(f"\nTraining period: {train_data.index[0]} to {train_data.index[-1]}")
    print(f"Training samples: {len(train_data):,} hours")
    print(f"Test period: {test_data.index[0]} to {test_data.index[-1]}")
    print(f"Test samples: {len(test_data):,} hours")
    
    # Find best ARIMA parameters using daily data for speed
    print("\n[1/5] Finding optimal ARIMA parameters...")
    train_daily = train_data.resample('D').mean()
    best_order, param_results = find_best_arima(train_daily, max_p=5, max_d=2, max_q=5)
    
    os.makedirs('../outputs/metrics', exist_ok=True)
    param_results.to_csv('../outputs/metrics/arima_parameter_selection.csv', index=False)
    
    # Fit final model on hourly data
    print(f"\n[2/5] Fitting ARIMA{best_order} on hourly training data (2010-2020)...")
    print("  (This may take 1-2 minutes...)")
    
    model = ARIMA(train_data, order=best_order)
    fitted_model = model.fit()
    
    print(f"\nModel Summary:")
    print(f"  AIC: {fitted_model.aic:.1f}")
    print(f"  BIC: {fitted_model.bic:.1f}")
    print(f"  Log Likelihood: {fitted_model.llf:.1f}")
    
    # Diagnostic checks
    print("\n[3/5] Performing diagnostic checks...")
    
    residuals = fitted_model.resid
    lb_test = acorr_ljungbox(residuals, lags=[10, 20, 30], return_df=True)
    print(f"\nLjung-Box Test (H0: No autocorrelation):")
    for lag in [10, 20, 30]:
        p_value = lb_test.loc[lag, 'lb_pvalue']
        result = "[OK] Pass" if p_value > 0.05 else "[WARNING]"
        print(f"  Lag {lag}: p-value={p_value:.4f} ({result})")
    
    from scipy.stats import jarque_bera
    jb_stat, jb_pvalue = jarque_bera(residuals.dropna())
    print(f"\nJarque-Bera Normality Test: p-value={jb_pvalue:.4f}")
    
    # Rolling forecast on test data
    print(f"\n[4/5] Generating rolling forecasts for {len(test_data)} hours (2022)...")
    test_results = fitted_model.apply(test_data)
    forecast = test_results.fittedvalues[1:]
    actual = test_data[1:]
    
    # Calculate metrics
    mae = mean_absolute_error(actual, forecast)
    rmse = np.sqrt(mean_squared_error(actual, forecast))
    mape = mean_absolute_percentage_error(actual, forecast) * 100
    
    # Calculate metrics by season
    df_forecast = pd.DataFrame({'actual': actual, 'forecast': forecast}, index=actual.index)
    df_forecast['month'] = df_forecast.index.month
    
    seasons = {
        'Winter (Dec-Feb)': [12, 1, 2],
        'Spring (Mar-May)': [3, 4, 5],
        'Summer (Jun-Aug)': [6, 7, 8],
        'Fall (Sep-Nov)': [9, 10, 11]
    }
    
    seasonal_metrics = {}
    for season_name, months in seasons.items():
        season_data = df_forecast[df_forecast['month'].isin(months)]
        if len(season_data) > 0:
            season_mae = mean_absolute_error(season_data['actual'], season_data['forecast'])
            season_rmse = np.sqrt(mean_squared_error(season_data['actual'], season_data['forecast']))
            seasonal_metrics[season_name] = {'MAE': season_mae, 'RMSE': season_rmse}
    
    print("\n" + "="*60)
    print("ARIMA MODEL RESULTS (Train 2010-2020, Test 2022)")
    print("="*60)
    print(f"Model: ARIMA{best_order}")
    print(f"\nOverall Performance (Full Year 2022):")
    print(f"  MAE:  {mae:.4f}")
    print(f"  RMSE: {rmse:.4f}")
    print(f"  MAPE: {mape:.2f}%")
    
    print(f"\nSeasonal Performance:")
    for season, metrics in seasonal_metrics.items():
        print(f"  {season}: MAE={metrics['MAE']:.4f}, RMSE={metrics['RMSE']:.4f}")
    
    # Save metrics
    with open('../outputs/metrics/arima_metrics_full_2022.txt', 'w') as f:
        f.write(f"ARIMA MODEL RESULTS\n")
        f.write("="*50 + "\n\n")
        f.write(f"Training Period: 2010-2020 ({len(train_data):,} hours)\n")
        f.write(f"Testing Period: 2022 ({len(test_data):,} hours)\n")
        f.write(f"Model: ARIMA{best_order}\n\n")
        f.write(f"Overall Metrics:\n")
        f.write(f"  MAE: {mae:.4f}\n")
        f.write(f"  RMSE: {rmse:.4f}\n")
        f.write(f"  MAPE: {mape:.2f}%\n\n")
        f.write(f"Seasonal Metrics:\n")
        for season, metrics in seasonal_metrics.items():
            f.write(f"  {season}: MAE={metrics['MAE']:.4f}, RMSE={metrics['RMSE']:.4f}\n")
    
    # Visualization
    print("\n[5/5] Generating visualizations...")
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    
    # Plot 1: 10-day sample
    ax1 = axes[0, 0]
    plot_start = '2022-03-01'
    plot_end = '2022-03-10'
    plot_actual = actual.loc[plot_start:plot_end]
    plot_forecast = forecast.loc[plot_start:plot_end]
    ax1.plot(plot_actual.index, plot_actual, label='Actual', color='blue', linewidth=2)
    ax1.plot(plot_forecast.index, plot_forecast, label='ARIMA Forecast', 
             color='red', linestyle='--', linewidth=2)
    ax1.set_title(f'ARIMA{best_order} - 10-Day Sample (March 2022)')
    ax1.set_ylabel('Capacity Factor')
    ax1.set_xlabel('Date')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Residuals
    ax2 = axes[0, 1]
    residuals_plot = residuals[-1000:]
    ax2.plot(residuals_plot.index, residuals_plot.values, color='purple', alpha=0.7)
    ax2.axhline(y=0, color='red', linestyle='--', linewidth=2)
    ax2.set_title('Model Residuals (Last 1000 hours)')
    ax2.set_ylabel('Residual')
    ax2.set_xlabel('Time')
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: ACF of residuals
    ax3 = axes[1, 0]
    plot_acf(residuals.dropna(), lags=40, ax=ax3, alpha=0.05)
    ax3.set_title('Autocorrelation of Residuals')
    ax3.set_xlabel('Lag')
    
    # Plot 4: Actual vs Predicted scatter
    ax4 = axes[1, 1]
    sample_idx = np.random.choice(len(actual), min(5000, len(actual)), replace=False)
    ax4.scatter(actual.iloc[sample_idx], forecast.iloc[sample_idx], alpha=0.3, s=10)
    ax4.plot([0, 1], [0, 1], 'r--', linewidth=2, label='Perfect Prediction')
    ax4.set_xlabel('Actual Values')
    ax4.set_ylabel('Predicted Values')
    
    ss_res = np.sum((actual - forecast) ** 2)
    ss_tot = np.sum((actual - np.mean(actual)) ** 2)
    r2 = 1 - (ss_res / ss_tot)
    
    ax4.set_title(f'Actual vs Predicted (R² = {r2:.3f})')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    fig_path = '../outputs/figures/arima_enhanced_analysis.png'
    plt.savefig(fig_path, dpi=300)
    print(f"[OK] Saved enhanced ARIMA analysis to: {fig_path}")
    
    return fitted_model, mae, rmse, mape

if __name__ == "__main__":
    model, mae, rmse, mape = run_arima_model()