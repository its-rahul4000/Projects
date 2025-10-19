import pandas as pd
import numpy as np
import pickle
import json
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Any
import re

class QuerySystem:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.embeddings = None
        self.documents = []
        self.developers_df = None
        self.investors_df = None
        self.emails_df = None
        self.meetings_df = None
        self.unified_df = None
        
        self.load_data()
    
    def load_data(self):
        """Load index and data from data/ directory"""
        try:
            with open('data/search_index.pkl', 'rb') as f:
                index_data = pickle.load(f)
                self.embeddings = index_data['embeddings']
                self.documents = index_data['documents']
            
            self.developers_df = pd.read_csv('data/clean_developers.csv')
            self.investors_df = pd.read_csv('data/clean_investors.csv')
            self.emails_df = pd.read_csv('data/clean_emails.csv')
            self.meetings_df = pd.read_csv('data/clean_meetings.csv')
            self.unified_df = pd.read_csv('data/unified_matches.csv')
            
            print(f"Query system loaded: {len(self.documents)} documents")
            
        except FileNotFoundError as e:
            print(f"Error loading data: {e}")
            print("Please run data_clean.py and build_index.py first")
            raise
    
    def semantic_search(self, query: str, k: int = 5, source_filter: str = None):
        """Perform semantic search on all documents"""
        query_embedding = self.model.encode([query], normalize_embeddings=True)
        similarities = cosine_similarity(query_embedding, self.embeddings)[0]
        
        top_indices = np.argsort(similarities)[::-1][:k*2]
        
        results = []
        for idx in top_indices:
            result = self.documents[idx].copy()
            result['score'] = float(similarities[idx])
            
            if source_filter and result['source'] != source_filter:
                continue
                
            results.append(result)
            
            if len(results) >= k:
                break
        
        return results[:k]
    
    def query_developers_by_region_type(self, region: str, project_type: str = None):
        """Find developers by region and project type"""
        mask = self.developers_df['Region'] == region
        
        if project_type:
            # Handle different ways ARR might be mentioned
            arr_keywords = ['arr', 'afforestation', 'reforestation']
            if any(keyword in project_type.lower() for keyword in arr_keywords):
                mask = mask & (
                    self.developers_df['ProjectType'].str.contains('Afforestation/Reforestation', na=False) |
                    self.developers_df['ProjectType'].str.contains('ARR', na=False, case=False)
                )
            else:
                mask = mask & (self.developers_df['ProjectType'].str.contains(project_type, na=False, case=False))
        
        results = self.developers_df[mask].to_dict('records')
        return results
    
    def find_investor_matches_for_project(self, project_id: str):
        """Find investors that match the sector and ticket size of a specific project"""
        try:
            project = self.developers_df[self.developers_df['ProjectID'] == project_id].iloc[0]
        except IndexError:
            return f"Project {project_id} not found."
        
        # Calculate project scale for ticket size matching
        project_hectares = project.get('Hectares', 0) or 0
        project_credits = project.get('EstimatedAnnualCredits', 0) or 0
        project_scale = max(project_hectares * 1000, project_credits * 10)
        
        matches = []
        for _, investor in self.investors_df.iterrows():
            match_score = 0
            match_reasons = []
            
            # Sector matching
            project_type = project.get('ProjectType', '')
            investor_sector = investor.get('SectorFocus', '')
            
            sector_keywords = {
                'Afforestation/Reforestation': ['arr', 'afforestation', 'reforestation', 'forest'],
                'Methane Reduction': ['methane', 'emission', 'leak'],
                'Blue Carbon': ['mangrove', 'blue carbon', 'coastal'],
                'Biochar': ['biochar'],
                'Agriculture': ['agriculture', 'agroforestry', 'awd']
            }
            
            # Check sector compatibility
            for sector, keywords in sector_keywords.items():
                if any(keyword in project_type.lower() for keyword in keywords):
                    if any(keyword in investor_sector.lower() for keyword in keywords):
                        match_score += 0.5
                        match_reasons.append(f"Sector match: {sector}")
                        break
            
            # Ticket size matching
            ticket_min = investor.get('TicketSizeMin', 0) or 0
            ticket_max = investor.get('TicketSizeMax', float('inf')) or float('inf')
            
            if ticket_min <= project_scale <= ticket_max:
                match_score += 0.3
                match_reasons.append(f"Ticket size appropriate: ${ticket_min}M-${ticket_max}M")
            elif project_scale > 0:
                # Partial credit for being in the right order of magnitude
                if abs(project_scale - ticket_min) / project_scale < 2:  # Within 2x
                    match_score += 0.15
                    match_reasons.append(f"Ticket size approximately matches")
            
            # Region matching
            project_region = project.get('Region', '')
            investor_region = investor.get('RegionFocus', '')
            
            if investor_region == 'Global' or project_region in str(investor_region):
                match_score += 0.2
                match_reasons.append(f"Region match: {project_region}")
            
            if match_score > 0.3:
                matches.append({
                    'investor': investor.to_dict(),
                    'match_score': round(match_score, 2),
                    'reasons': match_reasons
                })
        
        # Sort by match score
        matches.sort(key=lambda x: x['match_score'], reverse=True)
        return matches
    
    def summarize_project_communications(self, project_id: str):
        """Summarize all communication related to a project"""
        # Get emails
        def email_contains_project(email_row):
            referenced = email_row.get('ReferencedProjects', [])
            if isinstance(referenced, str):
                try:
                    referenced = json.loads(referenced.replace("'", '"'))
                except:
                    referenced = []
            return project_id in str(referenced)
        
        email_mask = self.emails_df.apply(email_contains_project, axis=1)
        relevant_emails = self.emails_df[email_mask]
        
        # Get meetings
        def meeting_contains_project(meeting_row):
            entities_str = meeting_row.get('ExtractedEntities', '{}')
            entities = {}
            try:
                if isinstance(entities_str, str):
                    entities = json.loads(entities_str)
                else:
                    entities = entities_str
            except:
                entities = {'projects': [], 'investors': [], 'actions': []}
            return project_id in entities.get('projects', [])
        
        meeting_mask = self.meetings_df.apply(meeting_contains_project, axis=1)
        relevant_meetings = self.meetings_df[meeting_mask]
        
        # Create summary
        summary = {
            'project_id': project_id,
            'email_count': len(relevant_emails),
            'meeting_count': len(relevant_meetings),
            'recent_activities': [],
            'key_contacts': set(),
            'action_items': [],
            'emails': relevant_emails.to_dict('records'),
            'meetings': relevant_meetings.to_dict('records')
        }
        
        # Extract key contacts from emails
        for email in relevant_emails.to_dict('records'):
            if email.get('From'):
                summary['key_contacts'].add(email['From'])
            if email.get('Date'):
                summary['recent_activities'].append(f"Email on {email['Date']}: {email.get('Subject', 'No subject')}")
        
        # Extract action items and contacts from meetings
        for meeting in relevant_meetings.to_dict('records'):
            entities_str = meeting.get('ExtractedEntities', '{}')
            entities = {}
            try:
                if isinstance(entities_str, str):
                    entities = json.loads(entities_str)
                else:
                    entities = entities_str
            except:
                entities = {'projects': [], 'investors': [], 'actions': []}
            
            if entities.get('actions'):
                for action in entities['actions']:
                    summary['action_items'].append(f"Action from meeting {meeting.get('TranscriptID', '')}: {action}")
            
            if meeting.get('TranscriptText'):
                # Extract mentioned names (simplified)
                text = meeting['TranscriptText'].lower()
                if 'ana' in text:
                    summary['key_contacts'].add('Ana Ribeiro (VerdeNova)')
                if 'diego' in text:
                    summary['key_contacts'].add('Diego Flores (EquiForests)')
                if 'manan' in text:
                    summary['key_contacts'].add('Manan (Calculus Carbon)')
        
        summary['key_contacts'] = list(summary['key_contacts'])
        summary['recent_activities'] = summary['recent_activities'][-5:]  # Last 5 activities
        summary['action_items'] = summary['action_items'][-5:]  # Last 5 action items
        
        return summary
    
    def get_investor_meeting_actions(self, investor_identifier: str):
        """Get actionable items from meetings with a specific investor (by ID or name)"""
        # First, try to find investor by ID (I001, I002, etc.)
        investor_id = None
        investor_name = None
        
        # Check if it's an investor ID
        if re.match(r'^I\d+$', investor_identifier, re.IGNORECASE):
            investor_id = investor_identifier.upper()
            investor_match = self.investors_df[self.investors_df['InvestorID'] == investor_id]
            if not investor_match.empty:
                investor_name = investor_match.iloc[0]['FundName']
        
        # If not found by ID, try by name
        if not investor_id:
            investor_identifier_lower = investor_identifier.lower()
            investor_mapping = {
                'northstar': ('I001', 'NorthStar Climate Fund'),
                'triage': ('I002', 'Triage Capital'),
                'summit green': ('I003', 'Summit Green Partners'),
                'zenith impact': ('I004', 'Zenith Impact'),
                'blueoak': ('I005', 'BlueOak Investors'),
                'helios': ('I006', 'Helios Infrastructure'),
                'verdeventures': ('I007', 'VerdeVentures'),
                'atlas carbon': ('I008', 'Atlas Carbon Partners'),
                'greenbridge': ('I009', 'GreenBridge Capital'),
                'localdev bank': ('I010', 'LocalDev Bank'),
                'pacific impact': ('I011', 'Pacific Impact Fund'),
                'eurogreen': ('I012', 'EuroGreen Partners')
            }
            
            for name, (id, full_name) in investor_mapping.items():
                if name in investor_identifier_lower:
                    investor_id = id
                    investor_name = full_name
                    break
        
        # If still not found, try direct match in investor names
        if not investor_id:
            for _, investor in self.investors_df.iterrows():
                if investor_identifier.lower() in investor['FundName'].lower():
                    investor_id = investor['InvestorID']
                    investor_name = investor['FundName']
                    break
        
        if not investor_id:
            return f"Investor '{investor_identifier}' not found. Please use Investor ID (I001, I002, etc.) or investor name."
        
        # Find meetings with this investor
        def meeting_contains_investor(meeting_row):
            entities_str = meeting_row.get('ExtractedEntities', '{}')
            entities = {}
            try:
                if isinstance(entities_str, str):
                    entities = json.loads(entities_str)
                else:
                    entities = entities_str
            except:
                entities = {'projects': [], 'investors': [], 'actions': []}
            return investor_id in entities.get('investors', [])
        
        meeting_mask = self.meetings_df.apply(meeting_contains_investor, axis=1)
        relevant_meetings = self.meetings_df[meeting_mask]
        
        if relevant_meetings.empty:
            return f"No meetings found with investor {investor_name} ({investor_id})."
        
        # Get the most recent meeting
        relevant_meetings = relevant_meetings.sort_values('TranscriptID', ascending=False)
        latest_meeting = relevant_meetings.iloc[0]
        
        # Extract actions and create summary
        entities_str = latest_meeting.get('ExtractedEntities', '{}')
        entities = {}
        try:
            if isinstance(entities_str, str):
                entities = json.loads(entities_str)
            else:
                entities = entities_str
        except:
            entities = {'projects': [], 'investors': [], 'actions': []}
        
        # Extract actionable items from transcript text
        transcript_text = latest_meeting.get('TranscriptText', '')
        action_items = entities.get('actions', [])
        
        # Enhanced action extraction from text
        action_patterns = [
            r'(?:need to|will|should|must|going to)\s+(\w+\s+\w+)',
            r'(?:schedule|plan|prepare|review|share|follow up|send|provide)\s+\w+',
            r'(?:action item|next step|todo|task)[s]?\s*:?\s*([^\.]+)',
        ]
        
        for pattern in action_patterns:
            matches = re.findall(pattern, transcript_text.lower())
            for match in matches:
                if isinstance(match, tuple):
                    match = ' '.join(match)
                if match and len(match) > 3 and match not in action_items:
                    action_items.append(match.strip())
        
        # Get mentioned projects
        mentioned_projects = entities.get('projects', [])
        project_names = []
        for project_id in mentioned_projects:
            project_match = self.developers_df[self.developers_df['ProjectID'] == project_id]
            if not project_match.empty:
                project_names.append(f"{project_match.iloc[0]['DeveloperName']} ({project_id})")
        
        summary = {
            'investor_id': investor_id,
            'investor_name': investor_name,
            'meeting_id': latest_meeting.get('TranscriptID', 'Unknown'),
            'mentioned_projects': project_names,
            'action_items': list(set(action_items)),  # Remove duplicates
            'key_discussion_points': [],
            'next_steps': []
        }
        
        # Extract key discussion points (first 200 chars of transcript)
        if transcript_text:
            summary['key_discussion_points'] = [transcript_text[:200] + '...' if len(transcript_text) > 200 else transcript_text]
        
        # Convert actions to next steps
        for action in action_items:
            summary['next_steps'].append(f"- {action.capitalize()}")
        
        return summary
    
    def answer_question(self, question: str):
        """Answer natural language questions with improved parsing"""
        question_lower = question.lower().strip()
        
        # Pattern 1: Which developers have ARR projects in Latin America
        if any(pattern in question_lower for pattern in [
            'developers have arr projects in latin america',
            'arr projects latin america',
            'latin america arr developers'
        ]):
            results = self.query_developers_by_region_type('Latin America', 'ARR')
            return {
                'type': 'developers_region_type',
                'results': results,
                'query': 'ARR projects in Latin America'
            }
        
        # Pattern 2: Which investors match the sector and ticket size of Project X
        project_match = re.search(r'project\s+([pP]\d+)', question_lower)
        if project_match and any(keyword in question_lower for keyword in ['investor', 'match', 'sector', 'ticket']):
            project_id = project_match.group(1).upper()
            results = self.find_investor_matches_for_project(project_id)
            return {
                'type': 'investor_matches_detailed',
                'results': results,
                'query': f'Investor matches for {project_id} (sector & ticket size)'
            }
        
        # Pattern 3: Summarize all communication related to Project Y
        project_match = re.search(r'project\s+([pP]\d+)', question_lower)
        if project_match and any(keyword in question_lower for keyword in ['summarize', 'communication', 'communic']):
            project_id = project_match.group(1).upper()
            results = self.summarize_project_communications(project_id)
            return {
                'type': 'project_communications_summary',
                'results': results,
                'query': f'Communication summary for {project_id}'
            }
        
        # Pattern 4: What were the actionable from the last meeting with Investor Y
        investor_match = re.search(r'investor\s+([iI]\d+)', question_lower)  # Match Investor ID
        investor_match2 = re.search(r'with\s+([iI]\d+)', question_lower)     # Match "with I001"
        investor_match3 = re.search(r'investor\s+(\w+)', question_lower)     # Match investor name as fallback
        
        if (investor_match or investor_match2 or investor_match3) and any(keyword in question_lower for keyword in ['actionable', 'action', 'meeting', 'last meeting']):
            if investor_match:
                investor_identifier = investor_match.group(1).upper()
            elif investor_match2:
                investor_identifier = investor_match2.group(1).upper()
            else:
                investor_identifier = investor_match3.group(1)
            
            results = self.get_investor_meeting_actions(investor_identifier)
            return {
                'type': 'investor_meeting_actions',
                'results': results,
                'query': f'Action items from meetings with {investor_identifier}'
            }
        
        # Pattern 5: Generic project-investor matching
        project_match = re.search(r'([pP]\d+)', question_lower)
        if project_match and 'investor' in question_lower and 'match' in question_lower:
            project_id = project_match.group(1).upper()
            results = self.find_investor_matches_for_project(project_id)
            return {
                'type': 'investor_matches_detailed',
                'results': results,
                'query': f'Investor matches for {project_id}'
            }
        
        # Pattern 6: Methane projects in Asia
        if 'methane' in question_lower and 'asia' in question_lower:
            methane_projects = self.developers_df[
                (self.developers_df['ProjectType'] == 'Methane Reduction') & 
                (self.developers_df['Region'] == 'Asia')
            ]
            return {
                'type': 'specific_projects',
                'results': methane_projects.to_dict('records'),
                'query': 'Methane reduction projects in Asia'
            }
        
        # Fallback to semantic search
        results = self.semantic_search(question, k=8)
        return {
            'type': 'semantic_search',
            'results': results,
            'query': question
        }