import pandas as pd
import numpy as np
import re
import os
import json
from typing import Dict, List, Any

def clean_text(text):
    """Clean and normalize text"""
    if pd.isna(text):
        return ""
    text = str(text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_project_references(text, project_keywords):
    """Extract project references from text"""
    if pd.isna(text):
        return []
    text = str(text)
    found_projects = [proj for proj in project_keywords if proj in text]
    return found_projects

def calculate_match_score(project, investor):
    """Calculate matching score between project and investor"""
    score = 0
    
    # Region matching
    project_region = project.get('Region', '')
    investor_region = investor.get('RegionFocus', '')
    
    if investor_region == 'Global':
        score += 0.3
    elif project_region in str(investor_region):
        score += 0.3
    
    # Sector matching
    project_type = project.get('ProjectType', '')
    investor_sector = investor.get('SectorFocus', '')
    
    if any(keyword in investor_sector for keyword in project_type.split()):
        score += 0.4
    
    # Ticket size matching
    project_scale = project.get('Hectares', 0) or 0
    project_scale_value = project_scale * 1000
    
    ticket_min = investor.get('TicketSizeMin', 0) or 0
    ticket_max = investor.get('TicketSizeMax', float('inf')) or float('inf')
    
    if ticket_min <= project_scale_value <= ticket_max:
        score += 0.3
    
    return round(score, 2)

class DataCleaner:
    def __init__(self):
        self.developers_df = None
        self.investors_df = None
        self.emails_df = None
        self.meetings_df = None
        self.unified_df = None
        
    def load_data(self):
        """Load all data sources from data/ directory"""
        print("Loading data files from data/ directory...")
        try:
            self.developers_df = pd.read_csv('data/Project_developer.csv', skiprows=1)
            print(f"✓ Loaded developers data: {len(self.developers_df)} records")
            
            self.investors_df = pd.read_csv('data/Investors.csv', skiprows=1)
            print(f"✓ Loaded investors data: {len(self.investors_df)} records")
            
            self.emails_df = pd.read_csv('data/Outlook_emails.csv', skiprows=1)
            print(f"✓ Loaded emails data: {len(self.emails_df)} records")
            
            self.meetings_df = pd.read_csv('data/Meeting_transcripts.csv', skiprows=1)
            print(f"✓ Loaded meetings data: {len(self.meetings_df)} records")
            
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            raise
    
    def clean_developers_data(self):
        """Clean and standardize developers data"""
        print("Cleaning developers data...")
        
        self.developers_df = self.developers_df.dropna(how='all').reset_index(drop=True)
        self.developers_df = self.developers_df.loc[:, ~self.developers_df.columns.str.contains('^Unnamed')]
        self.developers_df.columns = [col.strip() for col in self.developers_df.columns]
        
        text_columns = ['DeveloperName', 'AlternateNames', 'Country', 'ProjectType', 'Status', 
                       'LandTenure', 'FPICStatus', 'PrimaryContactName', 'PrimaryContactEmail',
                       'LastContactSnippet', 'DocumentsNotes']
        
        for col in text_columns:
            if col in self.developers_df.columns:
                self.developers_df[col] = self.developers_df[col].apply(clean_text)
        
        project_type_mapping = {
            'ARR': 'Afforestation/Reforestation',
            'AWD (rice)': 'Alternative Wetting&Drying',
            'Methane Leak Repair': 'Methane Reduction',
            'Biochar pilot': 'Biochar',
            'Mangrove Restoration': 'Blue Carbon',
            'Afforestation / ARR': 'Afforestation/Reforestation',
            'ARR + Timber': 'Afforestation/Reforestation',
            'ARR (smallholder)': 'Afforestation/Reforestation',
            'Afforestation / Agroforestry': 'Agroforestry',
            'Urban Afforestation': 'Urban Forestry'
        }
        
        self.developers_df['ProjectType'] = self.developers_df['ProjectType'].replace(project_type_mapping)
        
        if 'Hectares' in self.developers_df.columns:
            self.developers_df['Hectares'] = pd.to_numeric(
                self.developers_df['Hectares'].astype(str).str.replace(',', ''), 
                errors='coerce'
            )
        
        if 'EstimatedAnnualCredits' in self.developers_df.columns:
            self.developers_df['EstimatedAnnualCredits'] = pd.to_numeric(
                self.developers_df['EstimatedAnnualCredits'].astype(str).str.replace(',', ''), 
                errors='coerce'
            )
        
        region_mapping = {
            'Brazil': 'Latin America',
            'Peru': 'Latin America',
            'Colombia': 'Latin America',
            'Philippines': 'Asia',
            'Vietnam': 'Asia', 
            'India': 'Asia',
            'Indonesia': 'Asia',
            'Nepal': 'Asia',
            'Kazakhstan': 'Asia',
            'Mongolia': 'Asia',
            'Senegal': 'Africa'
        }
        
        self.developers_df['Region'] = self.developers_df['Country'].map(region_mapping)
        
        if 'Status' in self.developers_df.columns:
            self.developers_df['Status'] = self.developers_df['Status'].fillna('Unknown')
        
        print(f"✓ Cleaned developers data: {len(self.developers_df)} records")
        return self.developers_df
    
    def clean_investors_data(self):
        """Clean and standardize investors data"""
        print("Cleaning investors data...")
        
        self.investors_df = self.investors_df.dropna(how='all').reset_index(drop=True)
        self.investors_df = self.investors_df.loc[:, ~self.investors_df.columns.str.contains('^Unnamed')]
        self.investors_df.columns = [col.strip() for col in self.investors_df.columns]
        
        text_columns = ['FundName', 'RegionFocus', 'TicketSizeCurrency', 'SectorFocus',
                       'PreferredStructures', 'Restrictions', 'PrimaryContactName',
                       'PrimaryContactEmail', 'InvestmentMandateText', 'PriorInteractions', 'Notes']
        
        for col in text_columns:
            if col in self.investors_df.columns:
                self.investors_df[col] = self.investors_df[col].apply(clean_text)
        
        if 'TicketSizeMin' in self.investors_df.columns:
            self.investors_df['TicketSizeMin'] = pd.to_numeric(
                self.investors_df['TicketSizeMin'], errors='coerce'
            )
        
        if 'TicketSizeMax' in self.investors_df.columns:
            self.investors_df['TicketSizeMax'] = pd.to_numeric(
                self.investors_df['TicketSizeMax'], errors='coerce'
            )
        
        sector_mapping = {
            'NbS, ARR, REDD+': 'ARR/REDD+',
            'ARR, AWD': 'ARR/Agriculture',
            'Agriculture, Restoration, Agroforestry': 'Agriculture/Agroforestry',
            'ARR, Mangroves, Community projects': 'ARR/Blue Carbon',
            'ARR, REDD+, NbS': 'ARR/REDD+',
            'Large-scale NbS, Timber, Infrastructure': 'Large-scale NbS',
            'Early-stage ARR, Agroforestry': 'Early-stage ARR',
            'Methane mitigation, ARR, Tech pilots': 'Methane/Tech',
            'NbS, Biochar, Blended structures': 'Biochar/Blended Finance',
            'Rural development, AGRI, Smallholder': 'Agriculture/Smallholder',
            'Mangroves, Coastal NbS': 'Blue Carbon',
            'Timber, Large ARR, Carbon Removal': 'Timber/ARR'
        }
        
        if 'SectorFocus' in self.investors_df.columns:
            self.investors_df['SectorFocus'] = self.investors_df['SectorFocus'].map(sector_mapping)
        
        if 'RegionFocus' in self.investors_df.columns:
            self.investors_df['RegionFocus'] = self.investors_df['RegionFocus'].fillna('Global')
        
        print(f"✓ Cleaned investors data: {len(self.investors_df)} records")
        return self.investors_df
    
    def clean_emails_data(self):
        """Clean and standardize emails data"""
        print("Cleaning emails data...")
        
        self.emails_df = self.emails_df.dropna(how='all').reset_index(drop=True)
        self.emails_df = self.emails_df.loc[:, ~self.emails_df.columns.str.contains('^Unnamed')]
        self.emails_df.columns = [col.strip() for col in self.emails_df.columns]
        
        text_columns = ['From', 'To', 'Cc', 'Subject', 'Body']
        for col in text_columns:
            if col in self.emails_df.columns:
                self.emails_df[col] = self.emails_df[col].apply(clean_text)
        
        if 'Date' in self.emails_df.columns:
            self.emails_df['Date'] = pd.to_datetime(self.emails_df['Date'], errors='coerce')
        
        project_keywords = [f'P{i:03d}' for i in range(1, 16)]
        
        if 'Body' in self.emails_df.columns:
            self.emails_df['ReferencedProjects'] = self.emails_df['Body'].apply(
                lambda x: extract_project_references(x, project_keywords)
            )
        
        print(f"✓ Cleaned emails data: {len(self.emails_df)} records")
        return self.emails_df
    
    def clean_meetings_data(self):
        """Clean and standardize meetings data"""
        print("Cleaning meetings data...")
        
        self.meetings_df = self.meetings_df.dropna(how='all').reset_index(drop=True)
        self.meetings_df = self.meetings_df.loc[:, ~self.meetings_df.columns.str.contains('^Unnamed')]
        self.meetings_df.columns = [col.strip() for col in self.meetings_df.columns]
        
        if 'TranscriptText' in self.meetings_df.columns:
            self.meetings_df['TranscriptText'] = self.meetings_df['TranscriptText'].apply(clean_text)
        
        def extract_entities(text):
            if pd.isna(text):
                return {'projects': [], 'investors': [], 'actions': []}
            
            text = str(text)
            entities = {'projects': [], 'investors': [], 'actions': []}
            
            project_mapping = {
                'VerdeNova': 'P001', 'EquiForests': 'P002', 'BlueCanyon': 'P003',
                'SteppeRestore': 'P004', 'NorthernMethane': 'P005', 'CarbonRoots': 'P006',
                'AquaTerra': 'P007', 'DeltaBiochar': 'P008', 'SaharaGreen': 'P009',
                'SteppeGasFix': 'P010', 'ValleyAgro': 'P011', 'AndesReforest': 'P012',
                'SierraWaters': 'P013', 'HighlandAgro': 'P014', 'UrbanGreen': 'P015'
            }
            
            for dev, proj in project_mapping.items():
                if dev in text:
                    entities['projects'].append(proj)
            
            investor_mapping = {
                'NorthStar': 'I001', 'Triage': 'I002', 'Summit Green': 'I003',
                'Zenith Impact': 'I004', 'BlueOak': 'I005', 'Helios': 'I006',
                'VerdeVentures': 'I007', 'Atlas Carbon': 'I008', 'GreenBridge': 'I009',
                'LocalDev Bank': 'I010', 'Pacific Impact': 'I011', 'EuroGreen': 'I012'
            }
            
            for inv, inv_id in investor_mapping.items():
                if inv in text:
                    entities['investors'].append(inv_id)
            
            action_keywords = ['schedule', 'visit', 'share', 'prepare', 'review', 'assist', 'help', 'update', 'confirm']
            for action in action_keywords:
                if action in text.lower():
                    entities['actions'].append(action)
            
            return entities
        
        if 'TranscriptText' in self.meetings_df.columns:
            self.meetings_df['ExtractedEntities'] = self.meetings_df['TranscriptText'].apply(extract_entities)
            # Convert to JSON string for CSV storage
            self.meetings_df['ExtractedEntities_json'] = self.meetings_df['ExtractedEntities'].apply(json.dumps)
        
        print(f"✓ Cleaned meetings data: {len(self.meetings_df)} records")
        return self.meetings_df
    
    def create_unified_dataset(self):
        """Create a unified dataset linking all sources"""
        print("Creating unified dataset...")
        
        project_investor_matches = []
        
        for _, project in self.developers_df.iterrows():
            for _, investor in self.investors_df.iterrows():
                match_score = calculate_match_score(project, investor)
                if match_score > 0.3:
                    match_reasons = []
                    
                    project_region = project.get('Region', '')
                    investor_region = investor.get('RegionFocus', '')
                    
                    if investor_region == 'Global' or project_region in str(investor_region):
                        match_reasons.append(f"Region alignment: {project_region}")
                    
                    project_type = project.get('ProjectType', '')
                    investor_sector = investor.get('SectorFocus', '')
                    
                    if any(keyword in investor_sector for keyword in project_type.split()):
                        match_reasons.append(f"Sector alignment: {project_type}")
                    
                    project_investor_matches.append({
                        'ProjectID': project['ProjectID'],
                        'ProjectName': project['DeveloperName'],
                        'InvestorID': investor['InvestorID'],
                        'InvestorName': investor['FundName'],
                        'MatchScore': match_score,
                        'MatchReasons': '; '.join(match_reasons[:2])
                    })
        
        self.unified_df = pd.DataFrame(project_investor_matches)
        
        # Save cleaned datasets
        self.developers_df.to_csv('data/clean_developers.csv', index=False)
        self.investors_df.to_csv('data/clean_investors.csv', index=False)
        self.emails_df.to_csv('data/clean_emails.csv', index=False)
        
        # For meetings, save the JSON version for CSV and keep the dict version for processing
        meetings_save_df = self.meetings_df.copy()
        if 'ExtractedEntities_json' in meetings_save_df.columns:
            meetings_save_df = meetings_save_df.drop('ExtractedEntities', axis=1)
            meetings_save_df = meetings_save_df.rename(columns={'ExtractedEntities_json': 'ExtractedEntities'})
        meetings_save_df.to_csv('data/clean_meetings.csv', index=False)
        
        self.unified_df.to_csv('data/unified_matches.csv', index=False)
        
        print("✓ Data cleaning completed! Cleaned files saved in data/ directory")
        print(f"  - Developers: {len(self.developers_df)} records")
        print(f"  - Investors: {len(self.investors_df)} records")
        print(f"  - Emails: {len(self.emails_df)} records")
        print(f"  - Meetings: {len(self.meetings_df)} records")
        print(f"  - Project-Investor matches: {len(self.unified_df)} pairs")
        
        return self.unified_df

if __name__ == "__main__":
    cleaner = DataCleaner()
    cleaner.load_data()
    cleaner.clean_developers_data()
    cleaner.clean_investors_data()
    cleaner.clean_emails_data()
    cleaner.clean_meetings_data()
    unified_data = cleaner.create_unified_dataset()