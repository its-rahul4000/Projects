# main.py
import sys
import os
import subprocess

def main():
    print("🌳 AI Assistant - Setup")
    print("=" * 50)
    
    # Check if data files exist
    data_files = [
        'data/Project_developer.csv',
        'data/Investors.csv', 
        'data/Outlook_emails.csv',
        'data/Meeting_transcripts.csv'
    ]
    
    print("Checking data files...")
    for file_path in data_files:
        if os.path.exists(file_path):
            print(f"✓ Found {file_path}")
        else:
            print(f"✗ Missing {file_path}")
            print("Please make sure all CSV files are in the data/ directory")
            return
    
    try:
        # Step 1: Install dependencies
        print("\nStep 1: Checking dependencies...")
        try:
            import streamlit
            import pandas
            import numpy
            import sentence_transformers
            print("✓ All dependencies are installed")
        except ImportError as e:
            print(f"✗ Missing dependency: {e}")
            print("Please install dependencies with: pip install -r requirements.txt")
            return
        
        # Step 2: Data Cleaning
        print("\nStep 2: Cleaning data...")
        sys.path.append('src')
        from data_clean import DataCleaner
        
        cleaner = DataCleaner()
        cleaner.load_data()
        cleaner.clean_developers_data()
        cleaner.clean_investors_data()
        cleaner.clean_emails_data()
        cleaner.clean_meetings_data()
        unified_data = cleaner.create_unified_dataset()
        print("✓ Data cleaning completed")
        
        # Step 3: Build Index
        print("\nStep 3: Building search index...")
        from build_index import VectorIndexBuilder
        builder = VectorIndexBuilder()
        builder.run()
        print("✓ Search index built")
        
        # Step 4: Launch App
        print("\nStep 4: Launching Streamlit app...")
        print("The app will open in your browser automatically.")
        print("If it doesn't, go to: http://localhost:8501")
        print("\nPress Ctrl+C to stop the server")
        
        # Launch Streamlit app
        subprocess.run(["streamlit", "run", "src/app_streamlit.py"])
        
    except Exception as e:
        print(f"Error during setup: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()