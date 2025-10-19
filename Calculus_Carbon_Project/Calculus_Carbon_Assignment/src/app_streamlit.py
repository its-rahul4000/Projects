import streamlit as st
import pandas as pd
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_data_sources_used(response):
    """Helper function to determine which data sources were used"""
    sources = []
    result_type = response['type']
    
    if result_type in ['developers_region_type', 'specific_projects']:
        sources.append("Project Developers")
    if 'investor' in result_type:
        sources.append("Investors")
    if 'communication' in result_type or 'email' in result_type or 'meeting' in result_type:
        sources.extend(["Emails", "Meeting Transcripts"])
    if result_type == 'semantic_search':
        sources.extend(["All Sources"])
    
    return ", ".join(sources) if sources else "Multiple Sources"

def init_session_state():
    if 'query_system' not in st.session_state:
        st.session_state.query_system = None
    if 'data_loaded' not in st.session_state:
        st.session_state.data_loaded = False
    if 'user_question' not in st.session_state:
        st.session_state.user_question = ""
    if 'search_triggered' not in st.session_state:
        st.session_state.search_triggered = False

@st.cache_resource
def load_query_system():
    try:
        from query_layer import QuerySystem
        return QuerySystem()
    except Exception as e:
        st.error(f"Error loading query system: {e}")
        st.info("Please run data cleaning and indexing steps first.")
        return None

def display_search_results(results, result_type):
    """Display basic search results"""
    if not results:
        st.warning("No results found.")
        return
    
    if result_type == 'semantic_search':
        for i, result in enumerate(results, 1):
            with st.expander(f"🔍 {result['source'].title()} - {result['id']} (Score: {result['score']:.3f})", expanded=i==1):
                st.write(f"**Type:** {result['type'].title()}")
                if 'metadata' in result:
                    for key, value in result['metadata'].items():
                        if value and str(value) != 'nan':
                            st.write(f"**{key.replace('_', ' ').title()}:** {value}")
                st.write(f"**Content:**")
                st.text(result['text'][:500] + "..." if len(result['text']) > 500 else result['text'])
    
    elif result_type == 'developers_region_type':
        df = pd.DataFrame(results)
        if not df.empty:
            st.dataframe(df[['DeveloperName', 'ProjectID', 'ProjectType', 'Country', 'Status', 'Hectares']])
            
            # Simple bar chart using Streamlit
            st.subheader("Project Sizes by Developer")
            chart_data = df[['DeveloperName', 'Hectares']].set_index('DeveloperName')
            st.bar_chart(chart_data)
    
    elif result_type == 'investor_matches':
        for i, match in enumerate(results, 1):
            investor = match['investor']
            with st.expander(f"🤝 {investor['FundName']} (Match Score: {match['match_score']})", expanded=i==1):
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Investor Details:**")
                    st.write(f"**Focus:** {investor['SectorFocus']}")
                    st.write(f"**Region:** {investor['RegionFocus']}")
                    st.write(f"**Ticket Size:** {investor['TicketSizeMin']}-{investor['TicketSizeMax']} {investor['TicketSizeCurrency']}")
                    st.write(f"**Structures:** {investor['PreferredStructures']}")
                
                with col2:
                    st.write("**Match Reasons:**")
                    for reason in match.get('reasons', []):
                        st.write(f"✓ {reason}")
                
                if investor.get('InvestmentMandateText'):
                    st.write("**Mandate:**")
                    st.text(investor['InvestmentMandateText'][:300] + "..." if len(investor['InvestmentMandateText']) > 300 else investor['InvestmentMandateText'])

def display_enhanced_results(results, result_type):
    """Display enhanced results for the specific question types"""
    
    if result_type == 'investor_matches_detailed':
        if not results:
            st.warning("No investor matches found.")
            return
            
        st.subheader("🤝 Investor Matches (Sector & Ticket Size Analysis)")
        
        for i, match in enumerate(results, 1):
            investor = match['investor']
            with st.expander(f"🏦 {investor['FundName']} ({investor['InvestorID']}) - Match Score: {match['match_score']}/1.0", expanded=i==1):
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Investor Profile:**")
                    st.write(f"**ID:** {investor['InvestorID']}")
                    st.write(f"**Fund:** {investor['FundName']}")
                    st.write(f"**Focus:** {investor['SectorFocus']}")
                    st.write(f"**Region:** {investor['RegionFocus']}")
                    st.write(f"**Ticket:** ${investor['TicketSizeMin']}M-${investor['TicketSizeMax']}M {investor['TicketSizeCurrency']}")
                    st.write(f"**Structures:** {investor['PreferredStructures']}")
                
                with col2:
                    st.write("**Match Analysis:**")
                    for reason in match.get('reasons', []):
                        st.write(f"✅ {reason}")
                
                if investor.get('InvestmentMandateText'):
                    st.write("**Investment Mandate:**")
                    st.info(investor['InvestmentMandateText'])
    
    elif result_type == 'project_communications_summary':
        st.subheader("📋 Communication Summary")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📧 Total Emails", results['email_count'])
        with col2:
            st.metric("🎯 Total Meetings", results['meeting_count'])
        
        st.write("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**👥 Key Contacts:**")
            for contact in results.get('key_contacts', [])[:5]:
                st.write(f"• {contact}")
            
            if results.get('action_items'):
                st.write("**🎯 Action Items:**")
                for action in results['action_items']:
                    st.write(f"• {action}")
        
        with col2:
            st.write("**📅 Recent Activities:**")
            for activity in results.get('recent_activities', [])[:3]:
                st.write(f"• {activity}")
        
        # Show detailed communications
        with st.expander("🔍 View Detailed Communications"):
            if results['emails']:
                st.subheader("📧 Related Emails")
                for i, email in enumerate(results['emails'][:3]):
                    with st.expander(f"Email {i+1}: {email.get('Subject', 'No Subject')}"):
                        st.write(f"**From:** {email.get('From', 'N/A')}")
                        st.write(f"**Date:** {email.get('Date', 'N/A')}")
                        st.write(f"**To:** {email.get('To', 'N/A')}")
                        st.write("**Body:**")
                        st.text(email.get('Body', '')[:500] + "..." if len(email.get('Body', '')) > 500 else email.get('Body', ''))
            
            if results['meetings']:
                st.subheader("🎯 Related Meetings")
                for i, meeting in enumerate(results['meetings'][:3]):
                    with st.expander(f"Meeting {i+1}: {meeting.get('TranscriptID', 'N/A')}"):
                        import json
                        entities_str = meeting.get('ExtractedEntities', '{}')
                        entities = {}
                        try:
                            if isinstance(entities_str, str):
                                entities = json.loads(entities_str)
                            else:
                                entities = entities_str
                        except:
                            entities = {'projects': [], 'investors': [], 'actions': []}
                        
                        st.write(f"**Referenced Projects:** {', '.join(entities.get('projects', []))}")
                        st.write(f"**Referenced Investors:** {', '.join(entities.get('investors', []))}")
                        st.write(f"**Actions:** {', '.join(entities.get('actions', []))}")
                        st.write("**Transcript:**")
                        st.text(meeting.get('TranscriptText', '')[:500] + "..." if len(meeting.get('TranscriptText', '')) > 500 else meeting.get('TranscriptText', ''))
    
    elif result_type == 'investor_meeting_actions':
        if isinstance(results, str):  # Error message
            st.error(results)
            return
            
        st.subheader(f"📅 Meeting Actions with {results['investor_name']} ({results['investor_id']})")
        st.write(f"**Latest Meeting ID:** {results['meeting_id']}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if results['mentioned_projects']:
                st.write("**📋 Projects Discussed:**")
                for project in results['mentioned_projects']:
                    st.write(f"• {project}")
            
            if results['action_items']:
                st.write("**✅ Action Items Identified:**")
                for action in results['action_items']:
                    st.write(f"• {action.capitalize()}")
        
        with col2:
            if results['next_steps']:
                st.write("**🚀 Recommended Next Steps:**")
                for step in results['next_steps']:
                    st.write(step)
        
        if results['key_discussion_points']:
            st.write("**💬 Key Discussion Points:**")
            for point in results['key_discussion_points']:
                st.info(point)
    
    elif result_type == 'specific_projects':
        df = pd.DataFrame(results)
        if not df.empty:
            st.dataframe(df[['DeveloperName', 'ProjectID', 'ProjectType', 'Country', 'Status', 'Hectares']])
    
    else:
        # Fallback to original display
        display_search_results(results, result_type)

def main():
    st.set_page_config(
        page_title="Calculus Carbon AI Assistant",
        page_icon="🌳",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    init_session_state()
    
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        color: #2E8B57;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #228B22;
        margin-bottom: 1rem;
    }
    .success-box {
        background-color: #f0f8f0;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #2E8B57;
        margin-bottom: 1rem;
    }
    .info-box {
        background-color: #e6f3ff;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #0066cc;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="main-header">🌳 Calculus Carbon AI Assistant</div>', unsafe_allow_html=True)
    st.markdown("### Integrated Query System for Nature-based Solutions Investments")
    
    query_system = load_query_system()
    
    with st.sidebar:
        st.header("📊 Data Overview")
        
        if query_system:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Projects", len(query_system.developers_df))
                st.metric("Investors", len(query_system.investors_df))
            with col2:
                st.metric("Emails", len(query_system.emails_df))
                st.metric("Meetings", len(query_system.meetings_df))
            
            st.markdown("---")
            st.header("💡 Quick Access")
            
            st.write("**Project IDs:**")
            project_ids = [f"P{i:03d}" for i in range(1, 16)]
            st.write(", ".join(project_ids[:8]))
            st.write(", ".join(project_ids[8:]))
            
            st.write("**Investor IDs:**")
            investor_ids = [f"I{i:03d}" for i in range(1, 13)]
            st.write(", ".join(investor_ids[:6]))
            st.write(", ".join(investor_ids[6:]))
            
            st.markdown("---")
            st.header("🎯 System Capabilities")
            st.markdown("""
            This AI assistant can answer questions about:
            
            • **Project Information**
            - ARR projects in specific regions
            - Project types and status
            - Developer contacts and details
            
            • **Investor Matching**  
            - Sector and ticket size compatibility
            - Regional investment focus
            - Investment structures
            
            • **Communication Analysis**
            - Email and meeting summaries
            - Action items extraction
            - Key contact identification
            
            • **Multi-source Queries**
            - Cross-referencing across all data sources
            - Semantic search capabilities
            - Intelligent entity matching
            """)
    
    if not query_system:
        st.error("🚫 Query system not loaded")
        st.info("""
        Please complete the setup:
        1. Run `python main.py` to clean data and build index
        2. Or run manually:
           - `python src/data_clean.py`
           - `python src/build_index.py`
        """)
        return
    
    # Main query interface
    st.header("Ask a Question")
    
    user_question = st.text_input(
        "Enter your question about projects, investors, or communications:",
        value=st.session_state.user_question,
        placeholder="e.g., Which developers have ARR projects in Latin America?",
        key="question_input"
    )
    
    col1, col2, col3 = st.columns([1, 1, 3])
    with col1:
        search_button = st.button("🔍 Search", type="primary", use_container_width=True)
    with col2:
        clear_button = st.button("🗑️ Clear", use_container_width=True)
    
    # Handle button clicks
    if clear_button:
        st.session_state.user_question = ""
        st.session_state.search_triggered = False
        st.rerun()
    
    if search_button or st.session_state.search_triggered:
        question_to_search = user_question if search_button else st.session_state.user_question
        
        if question_to_search:
            with st.spinner("🔍 Searching across all data sources..."):
                try:
                    response = query_system.answer_question(question_to_search)
                    
                    st.success("✅ Found relevant information!")
                    st.markdown(f"### 📝 Results for: *{response['query']}*")
                    
                    # Use enhanced display for specific question types
                    display_enhanced_results(response['results'], response['type'])
                    
                    # Show query analysis
                    with st.expander("🔍 Query Analysis"):
                        st.write(f"**Question Type:** {response['type'].replace('_', ' ').title()}")
                        st.write(f"**Original Question:** {question_to_search}")
                        st.write(f"**Processed Query:** {response['query']}")
                        st.write(f"**Data Sources Used:** {get_data_sources_used(response)}")
                    
                    # Reset the search triggered flag
                    st.session_state.search_triggered = False
                    
                except Exception as e:
                    st.error(f"❌ Error processing query: {str(e)}")
                    st.session_state.search_triggered = False
        else:
            st.warning("⚠️ Please enter a question to search.")
            st.session_state.search_triggered = False
    
    # Data overview section
    st.markdown("---")
    st.markdown("### 📈 Data Overview")
    
    if query_system:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("#### 🌍 Projects by Region")
            region_counts = query_system.developers_df['Region'].value_counts()
            st.dataframe(region_counts)
        
        with col2:
            st.markdown("#### 🏢 Projects by Type")
            type_counts = query_system.developers_df['ProjectType'].value_counts()
            st.dataframe(type_counts)
        
        with col3:
            st.markdown("#### 💼 Investor Focus Areas")
            sector_counts = query_system.investors_df['SectorFocus']. value_counts()
            st.dataframe(sector_counts)
        
        # Quick facts
        st.markdown("---")
        st.markdown("### 💡 Quick Facts")
        
        fact_col1, fact_col2, fact_col3, fact_col4 = st.columns(4)
        
        with fact_col1:
            total_hectares = query_system.developers_df['Hectares'].sum()
            st.metric("Total Project Area", f"{total_hectares:,.0f} hectares")
        
        with fact_col2:
            total_credits = query_system.developers_df['EstimatedAnnualCredits'].sum()
            st.metric("Estimated Annual Credits", f"{total_credits:,.0f}")
        
        with fact_col3:
            avg_ticket = query_system.investors_df['TicketSizeMin'].mean()
            st.metric("Avg Min Ticket Size", f"${avg_ticket:,.0f}M")
        
        with fact_col4:
            global_investors = len(query_system.investors_df[query_system.investors_df['RegionFocus'] == 'Global'])
            st.metric("Global Investors", global_investors)
        
        # Project-Investor matches overview
        st.markdown("---")
        st.markdown("### 🤝 Project-Investor Matches Overview")
        if hasattr(query_system, 'unified_df') and query_system.unified_df is not None:
            match_summary = query_system.unified_df.groupby('ProjectID').size().reset_index(name='MatchCount')
            st.dataframe(match_summary)
        else:
            st.info("Run a search to see project-investor matches")
        
        # Investor reference table
        st.markdown("---")
        st.markdown("### 🏦 Investor Reference")
        if query_system.investors_df is not None:
            investor_ref = query_system.investors_df[['InvestorID', 'FundName', 'SectorFocus', 'RegionFocus']]
            st.dataframe(investor_ref)

if __name__ == "__main__":
    main()