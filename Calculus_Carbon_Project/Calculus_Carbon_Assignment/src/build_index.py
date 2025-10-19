import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import pickle
import os
import json

class VectorIndexBuilder:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.embeddings = None
        self.documents = []
        
    def load_data(self):
        """Load all cleaned datasets from data/ directory"""
        print("Loading cleaned data for indexing...")
        self.developers = pd.read_csv('data/clean_developers.csv')
        self.investors = pd.read_csv('data/clean_investors.csv')
        self.emails = pd.read_csv('data/clean_emails.csv')
        self.meetings = pd.read_csv('data/clean_meetings.csv')
        self.unified = pd.read_csv('data/unified_matches.csv')
        
        print(f"Loaded {len(self.developers)} developers, {len(self.investors)} investors, "
              f"{len(self.emails)} emails, {len(self.meetings)} meetings")
    
    def prepare_documents(self):
        """Prepare documents for indexing"""
        print("Preparing documents for semantic search...")
        documents = []
        
        # Developer documents
        for _, row in self.developers.iterrows():
            doc_text = f"""
            Project Developer: {row['DeveloperName']} 
            Project ID: {row['ProjectID']}
            Project Type: {row['ProjectType']}
            Country: {row['Country']}
            Region: {row.get('Region', 'N/A')}
            Status: {row['Status']}
            Hectares: {row.get('Hectares', 'N/A')}
            Annual Credits: {row.get('EstimatedAnnualCredits', 'N/A')}
            Contact: {row.get('PrimaryContactName', 'N/A')}
            Notes: {row.get('LastContactSnippet', '')}
            """
            documents.append({
                'text': doc_text,
                'source': 'developers',
                'id': row['ProjectID'],
                'type': 'project',
                'metadata': {
                    'name': row['DeveloperName'],
                    'project_type': row['ProjectType'],
                    'region': row.get('Region', ''),
                    'country': row['Country'],
                    'status': row['Status']
                }
            })
        
        # Investor documents
        for _, row in self.investors.iterrows():
            doc_text = f"""
            Investor: {row['FundName']}
            Investor ID: {row['InvestorID']}
            Sector Focus: {row['SectorFocus']}
            Region Focus: {row['RegionFocus']}
            Ticket Size: {row['TicketSizeMin']}-{row['TicketSizeMax']} {row['TicketSizeCurrency']}
            Preferred Structures: {row['PreferredStructures']}
            Restrictions: {row['Restrictions']}
            Contact: {row['PrimaryContactName']}
            Mandate: {row['InvestmentMandateText']}
            Notes: {row.get('Notes', '')}
            """
            documents.append({
                'text': doc_text,
                'source': 'investors',
                'id': row['InvestorID'],
                'type': 'investor',
                'metadata': {
                    'name': row['FundName'],
                    'sector_focus': row['SectorFocus'],
                    'region_focus': row['RegionFocus'],
                    'ticket_size': f"{row['TicketSizeMin']}-{row['TicketSizeMax']} {row['TicketSizeCurrency']}",
                    'structures': row['PreferredStructures']
                }
            })
        
        # Email documents
        for _, row in self.emails.iterrows():
            # Handle ReferencedProjects which might be stored as string
            referenced_projects = row.get('ReferencedProjects', [])
            if isinstance(referenced_projects, str):
                try:
                    referenced_projects = json.loads(referenced_projects.replace("'", '"'))
                except:
                    referenced_projects = []
            
            doc_text = f"""
            Email: {row.get('Subject', 'No Subject')}
            Date: {row.get('Date', 'N/A')}
            From: {row.get('From', 'N/A')}
            To: {row.get('To', 'N/A')}
            Body: {row.get('Body', '')}
            Referenced Projects: {referenced_projects}
            """
            documents.append({
                'text': doc_text,
                'source': 'emails',
                'id': row.get('EmailID', ''),
                'type': 'communication',
                'metadata': {
                    'subject': row.get('Subject', ''),
                    'date': str(row.get('Date', '')),
                    'from': row.get('From', ''),
                    'referenced_projects': referenced_projects
                }
            })
        
        # Meeting documents
        for _, row in self.meetings.iterrows():
            # Handle ExtractedEntities which might be stored as JSON string
            entities_str = row.get('ExtractedEntities', '{}')
            entities = {}
            try:
                if isinstance(entities_str, str):
                    entities = json.loads(entities_str)
                else:
                    entities = entities_str
            except:
                entities = {'projects': [], 'investors': [], 'actions': []}
            
            doc_text = f"""
            Meeting Transcript: {row.get('TranscriptText', '')}
            Referenced Projects: {entities.get('projects', [])}
            Referenced Investors: {entities.get('investors', [])}
            Actions Mentioned: {entities.get('actions', [])}
            """
            documents.append({
                'text': doc_text,
                'source': 'meetings',
                'id': row.get('TranscriptID', ''),
                'type': 'communication',
                'metadata': {
                    'referenced_projects': entities.get('projects', []),
                    'referenced_investors': entities.get('investors', []),
                    'actions': entities.get('actions', [])
                }
            })
        
        # Unified matches documents
        for _, row in self.unified.iterrows():
            doc_text = f"""
            Project-Investor Match: {row['ProjectName']} with {row['InvestorName']}
            Match Score: {row['MatchScore']}
            Reasons: {row['MatchReasons']}
            Project ID: {row['ProjectID']}
            Investor ID: {row['InvestorID']}
            """
            documents.append({
                'text': doc_text,
                'source': 'matches',
                'id': f"{row['ProjectID']}_{row['InvestorID']}",
                'type': 'match',
                'metadata': {
                    'project_name': row['ProjectName'],
                    'investor_name': row['InvestorName'],
                    'match_score': row['MatchScore'],
                    'reasons': row['MatchReasons']
                }
            })
        
        print(f"Prepared {len(documents)} documents for indexing")
        return documents
    
    def build_index(self, documents):
        """Build semantic search index"""
        print("Building semantic search index...")
        texts = [doc['text'] for doc in documents]
        
        print("Generating embeddings...")
        self.embeddings = self.model.encode(texts, normalize_embeddings=True)
        
        self.documents = documents
        
        index_data = {
            'embeddings': self.embeddings,
            'documents': documents
        }
        
        with open('data/search_index.pkl', 'wb') as f:
            pickle.dump(index_data, f)
        
        print(f"✓ Index built with {len(documents)} documents")
        print(f"✓ Embeddings shape: {self.embeddings.shape}")
    
    def run(self):
        """Build complete index"""
        self.load_data()
        documents = self.prepare_documents()
        self.build_index(documents)
        print("✓ Semantic search index completed!")

if __name__ == "__main__":
    builder = VectorIndexBuilder()
    builder.run()