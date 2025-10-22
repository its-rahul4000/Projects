Integrated_AI/
├── data/                           # Data directory
│   ├── Project_developer.csv       # Raw project developer data
│   ├── Investors.csv              # Raw investor data
│   ├── Outlook_emails.csv         # Raw email data
│   ├── Meeting_transcripts.csv    # Raw meeting transcripts
│   ├── clean_developers.csv       # Cleaned developer data
│   ├── clean_investors.csv        # Cleaned investor data
│   ├── clean_emails.csv           # Cleaned email data
│   ├── clean_meetings.csv         # Cleaned meeting data
│   ├── unified_matches.csv        # Project-investor matches
│   └── search_index.pkl           # Semantic search index
├── src/                          
│   ├── init.py                   # Package initialization
│   ├── data_clean.py             # Data cleaning and integration
│   ├── build_index.py            # Semantic search index builder
│   ├── query_layer.py            # Query processing system
│   └── app_streamlit.py          # Web interface
├── main.py                       # Main setup script
├── requirements.txt              # Python dependencies


**To Run this project:**

# Run the main setup script - it will handle everything automatically
python main.py

ignore below if Running above Command:-

**To Run the Project manually:-**
# 1. Install dependencies
pip install -r requirements.txt

# 2. Clean and integrate data
python src/data_clean.py

# 3. Build search index
python src/build_index.py

# 4. Launch the application
streamlit run src/app_streamlit.py


Imp:By changing the main folder name or Path change -> I have to reinstall the Virtual Environment by following steps:-

1.Delete the existing virtual environment:  Remove-Item -Recurse -Force .venv

2.Create a new virtual environment:   python -m venv .venv

3.Activate it:   .venv\Scripts\Activate

4.Reinstall dependencies:  pip install -r requirements.txt
