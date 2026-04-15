import subprocess
import sys
import os
import time
from datetime import datetime

def run_script(script_name, description):
    """Run a Python script and handle errors"""
    print("\n" + "="*80)
    print(f"RUNNING: {script_name}")
    print(f"Description: {description}")
    print("="*80)
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        if result.stdout:
            print(result.stdout)
        
        if result.returncode != 0:
            print(f"\n[ERROR] in {script_name}:")
            print(result.stderr)
            return False
        
        elapsed = time.time() - start_time
        print(f"\n[OK] {script_name} completed successfully in {elapsed:.1f} seconds")
        return True
        
    except FileNotFoundError:
        print(f"\n[ERROR] Script not found: {script_name}")
        return False
    except Exception as e:
        print(f"\n[ERROR] Unexpected error running {script_name}: {e}")
        return False

def main():
    """Run all project scripts in order"""
    
    print("="*80)
    print("EN639 OFFSHORE WIND POWER FORECASTING")
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    data_path = '../data/raw/Existing.csv'
    if not os.path.exists(data_path):
        print("\n[WARNING] Raw data file not found!")
        print(f"Expected location: {data_path}")
        response = input("\nContinue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Exiting...")
            return
    
    scripts = [
        ("01_data_prep.py", "Data Preprocessing and Cleaning"),
        ("02_persistence.py", "Persistence Baseline Model"),
        ("03_arima.py", "ARIMA Time Series Model"),
        ("04_weekly_analysis.py", "Weekly Pattern Analysis & Detailed Plots (UPDATED)"),
    ]
    
    results = {}
    total_start = time.time()
    
    for script_name, description in scripts:
        success = run_script(script_name, description)
        results[script_name] = success
        
        if not success:
            print(f"\n[ERROR] Stopping execution due to failure in {script_name}")
            break
    
    total_elapsed = time.time() - total_start
    
    print("\n" + "="*80)
    print("EXECUTION SUMMARY")
    print("="*80)
    
    for script_name, success in results.items():
        status = "[OK] SUCCESS" if success else "[ERROR] FAILED"
        print(f"{status}: {script_name}")
    
    print(f"\nTotal execution time: {total_elapsed:.1f} seconds")
    print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    print("\n" + "="*80)
    print("PROJECT EXECUTION COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()