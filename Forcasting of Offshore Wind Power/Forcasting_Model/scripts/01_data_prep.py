"""
EN639 Project: Offshore Wind Power Forecasting
Script 01: Data Preprocessing and Interpolation (Enhanced - Pandas 2.0 Compatible)
"""
import pandas as pd
import numpy as np
import os
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

def prep_data():
    """Enhanced data preprocessing with comprehensive cleaning and validation"""
    
    print("="*70)
    print("ENHANCED DATA PREPROCESSING PIPELINE")
    print("="*70)
    
    # File paths
    raw_file_path = '../data/raw/Existing.csv'
    processed_file_path = '../data/processed/UK_OFF_hourly_2010_2022.csv'
    stats_file_path = '../outputs/metrics/data_statistics.txt'
    
    # Create output directories
    os.makedirs('../data/processed', exist_ok=True)
    os.makedirs('../outputs/metrics', exist_ok=True)
    
    # Step 1: Load raw data
    print("\n[1/6] Loading raw data...")
    try:
        df = pd.read_csv(raw_file_path, usecols=['time', 'UK_OFF'], 
                        parse_dates=['time'], index_col='time')
        print(f"[OK] Loaded {len(df):,} records from {df.index[0]} to {df.index[-1]}")
    except FileNotFoundError:
        print(f"[ERROR] Raw data file not found at {raw_file_path}")
        print("Please download the dataset from: https://doi.org/10.11583/DTU.29617955")
        return None
    except Exception as e:
        print(f"[ERROR] Error loading data: {e}")
        return None
    
    # Step 2: Check data quality
    print("\n[2/6] Checking data quality...")
    initial_missing = df['UK_OFF'].isna().sum()
    initial_zero = (df['UK_OFF'] == 0).sum()
    
    print(f"  Total records: {len(df):,}")
    print(f"  Missing values: {initial_missing} ({initial_missing/len(df)*100:.2f}%)")
    print(f"  Zero values: {initial_zero} ({initial_zero/len(df)*100:.2f}%)")
    print(f"  Value range: [{df['UK_OFF'].min():.4f}, {df['UK_OFF'].max():.4f}]")
    
    # Step 3: Filter to modern era (2010-2022)
    print("\n[3/6] Filtering data (2010-2022)...")
    df_modern = df.loc['2010-01-01':'2022-12-31']
    print(f"[OK] Filtered to {len(df_modern):,} records (2010-2022)")
    
    # Step 4: Handle missing data with multiple strategies
    print("\n[4/6] Handling missing data...")
    
    # Check for gaps in time series
    expected_hours = pd.date_range(start='2010-01-01', end='2022-12-31 23:00:00', freq='h')
    actual_hours = df_modern.index
    missing_hours = expected_hours.difference(actual_hours)
    
    if len(missing_hours) > 0:
        print(f"  Found {len(missing_hours)} missing hours in the time series")
        print(f"  First 5 missing timestamps: {missing_hours[:5].tolist()}")
    
    # Resample to hourly and use forward fill (updated for pandas 2.0)
    df_resampled = df_modern.resample('h').asfreq()
    df_clean = df_resampled.copy()
    
    # Forward fill for small gaps (updated method)
    df_clean['UK_OFF'] = df_clean['UK_OFF'].ffill()  # Changed from fillna(method='ffill')
    
    # Backward fill for any remaining gaps at the beginning (updated method)
    df_clean['UK_OFF'] = df_clean['UK_OFF'].bfill()  # Changed from fillna(method='bfill')
    
    # Interpolate any remaining NaN values (should be none now)
    if df_clean['UK_OFF'].isna().any():
        df_clean['UK_OFF'] = df_clean['UK_OFF'].interpolate(method='linear')
    
    final_missing = df_clean['UK_OFF'].isna().sum()
    print(f"[OK] Missing data handled: {final_missing} remaining NaN values")
    
    # Step 5: Additional quality checks
    print("\n[5/6] Performing quality checks...")
    
    # Check for outliers (values > 1.0 or < 0)
    outliers = ((df_clean['UK_OFF'] > 1.0) | (df_clean['UK_OFF'] < 0)).sum()
    if outliers > 0:
        print(f"  [WARNING] Found {outliers} outliers (values outside [0,1])")
        # Clip outliers to valid range
        df_clean['UK_OFF'] = df_clean['UK_OFF'].clip(0, 1)
        print(f"  [OK] Clipped outliers to valid range [0,1]")
    
    # Check for duplicates
    duplicates = df_clean.index.duplicated().sum()
    if duplicates > 0:
        print(f"  [WARNING] Found {duplicates} duplicate timestamps, removing...")
        df_clean = df_clean[~df_clean.index.duplicated(keep='first')]
    
    # Step 6: Save processed data and statistics
    print("\n[6/6] Saving processed data...")
    df_clean.to_csv(processed_file_path)
    print(f"[OK] Saved to: {processed_file_path}")
    
    # Save statistics
    with open(stats_file_path, 'w') as f:
        f.write("DATA STATISTICS\n")
        f.write("="*50 + "\n")
        f.write(f"Original records: {len(df):,}\n")
        f.write(f"Final records: {len(df_clean):,}\n")
        f.write(f"Time range: {df_clean.index[0]} to {df_clean.index[-1]}\n")
        f.write(f"Years covered: {df_clean.index.year.nunique()}\n")
        f.write(f"Mean capacity factor: {df_clean['UK_OFF'].mean():.4f}\n")
        f.write(f"Median capacity factor: {df_clean['UK_OFF'].median():.4f}\n")
        f.write(f"Std deviation: {df_clean['UK_OFF'].std():.4f}\n")
        f.write(f"Min value: {df_clean['UK_OFF'].min():.4f}\n")
        f.write(f"Max value: {df_clean['UK_OFF'].max():.4f}\n")
        f.write(f"25th percentile: {df_clean['UK_OFF'].quantile(0.25):.4f}\n")
        f.write(f"75th percentile: {df_clean['UK_OFF'].quantile(0.75):.4f}\n")
        f.write(f"Missing values handled: {initial_missing}\n")
        f.write(f"Outliers clipped: {outliers}\n")
    
    print(f"[OK] Statistics saved to: {stats_file_path}")
    
    # Summary
    print("\n" + "="*70)
    print("DATA PREPROCESSING COMPLETE")
    print("="*70)
    print(f"[OK] Ready for modeling with {len(df_clean):,} hourly records")
    print(f"[OK] Time period: {df_clean.index.year.min()} - {df_clean.index.year.max()}")
    print("="*70 + "\n")
    
    return df_clean

def generate_data_report(df):
    """Generate a comprehensive data quality report"""
    
    print("\n" + "="*70)
    print("DATA QUALITY REPORT")
    print("="*70)
    
    # Basic statistics
    print("\nDescriptive Statistics:")
    print(df['UK_OFF'].describe())
    
    # Yearly statistics
    print("\nYearly Averages:")
    df_copy = df.copy()
    df_copy['year'] = df_copy.index.year
    yearly_avg = df_copy.groupby('year')['UK_OFF'].mean()
    for year, avg in yearly_avg.items():
        print(f"  {year}: {avg:.4f}")
    
    # Monthly patterns
    print("\nMonthly Averages:")
    df_copy['month'] = df_copy.index.month
    monthly_avg = df_copy.groupby('month')['UK_OFF'].mean()
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    for month, avg in monthly_avg.items():
        print(f"  {month_names[month-1]}: {avg:.4f}")
    
    # Hourly patterns
    print("\nHourly Averages (Peak hours):")
    df_copy['hour'] = df_copy.index.hour
    hourly_avg = df_copy.groupby('hour')['UK_OFF'].mean()
    top_hours = hourly_avg.nlargest(5)
    for hour, avg in top_hours.items():
        print(f"  Hour {hour:02d}:00: {avg:.4f}")
    
    return yearly_avg, monthly_avg, hourly_avg

if __name__ == "__main__":
    df = prep_data()
    if df is not None:
        generate_data_report(df)