import streamlit as st
import pandas as pd
import requests
from rapidfuzz import fuzz, process
import re
from typing import List, Tuple
import time
from urllib.parse import urlparse

# Configure Streamlit page
st.set_page_config(
    page_title="🔧 Parts Finder",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(90deg, #1f4e79, #2e8b57);
        color: white;
        margin: -1rem -1rem 2rem -1rem;
        border-radius: 0 0 10px 10px;
    }
    
    .search-container {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        border: 1px solid #e9ecef;
    }
    
    .result-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #e9ecef;
        margin-bottom: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .part-number {
        font-family: 'Courier New', monospace;
        font-weight: bold;
        color: #1f4e79;
        font-size: 1.1em;
    }
    
    .description {
        color: #555;
        margin: 0.5rem 0;
    }
    
    .match-score {
        font-weight: bold;
    }
    
    .score-excellent { color: #28a745; }
    .score-good { color: #ffc107; }
    .score-fair { color: #dc3545; }
    
    .highlight {
        background-color: #fff3cd;
        padding: 2px 4px;
        border-radius: 3px;
        font-weight: bold;
    }
    
    .stats-container {
        display: flex;
        justify-content: space-around;
        margin: 1rem 0;
    }
    
    .stButton > button {
        background: #1f4e79;
        color: white;
        border: none;
        border-radius: 5px;
        padding: 0.5rem 1rem;
    }
    
    .stButton > button:hover {
        background: #2e8b57;
    }
</style>
""", unsafe_allow_html=True)

# Configuration
DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/export?format=csv"

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_google_sheet(url: str) -> pd.DataFrame:
    """Load data from Google Sheets CSV URL with caching."""
    try:
        if not url or not url.startswith('http'):
            st.error("Please provide a valid Google Sheets CSV URL")
            return pd.DataFrame()
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Parse CSV content
        from io import StringIO
        csv_content = StringIO(response.text)
        df = pd.read_csv(csv_content)
        
        # Validate required columns
        required_columns = ['part_number', 'description']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            st.error(f"Missing required columns: {', '.join(missing_columns)}")
            return pd.DataFrame()
        
        # Clean the data
        df['part_number'] = df['part_number'].astype(str).str.strip()
        df['description'] = df['description'].astype(str).str.strip()
        
        # Remove empty rows
        df = df.dropna(subset=['part_number', 'description'])
        df = df[df['part_number'].str.len() > 0]
        df = df[df['description'].str.len() > 0]
        
        return df.reset_index(drop=True)
        
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data: {str(e)}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error processing data: {str(e)}")
        return pd.DataFrame()

def create_searchable_text(row) -> str:
    """Combine part number and description for better searching."""
    return f"{row['part_number']} {row['description']}".lower()

def advanced_search(query: str, df: pd.DataFrame, max_results: int = 50, min_score: int = 40) -> List[Tuple]:
    """
    Perform advanced fuzzy search on parts database.
    Returns list of tuples: (index, part_number, description, score)
    """
    if not query.strip() or df.empty:
        return []
    
    query = query.lower().strip()
    results = []
    
    # Create searchable text for each part
    df['searchable'] = df.apply(create_searchable_text, axis=1)
    
    # Method 1: Fuzzy match on combined text
    choices = df['searchable'].tolist()
    fuzzy_results = process.extract(
        query, 
        choices, 
        scorer=fuzz.WRatio,
        limit=min(max_results * 2, len(choices))  # Get more results for filtering
    )
    
    # Convert to our format
    for match_text, score, index in fuzzy_results:
        if score >= min_score:
            results.append((
                index,
                df.iloc[index]['part_number'],
                df.iloc[index]['description'],
                score
            ))
    
    # Method 2: Boost exact part number matches
    for idx, row in df.iterrows():
        part_num = row['part_number'].lower()
        if query in part_num:
            existing = next((r for r in results if r[0] == idx), None)
            if existing:
                # Boost score for part number match
                results = [(i, pn, desc, min(100, score + 15)) if i == idx 
                          else (i, pn, desc, score) for i, pn, desc, score in results]
            else:
                results.append((idx, row['part_number'], row['description'], 95))
    
    # Method 3: Boost description keyword matches
    query_words = query.split()
    for word in query_words:
        if len(word) > 2:  # Only boost for meaningful words
            for idx, row in df.iterrows():
                desc_lower = row['description'].lower()
                if word in desc_lower:
                    existing = next((r for r in results if r[0] == idx), None)
                    if existing:
                        # Small boost for keyword match
                        results = [(i, pn, desc, min(100, score + 5)) if i == idx 
                                  else (i, pn, desc, score) for i, pn, desc, score in results]
    
    # Sort by score and remove duplicates
    seen = set()
    unique_results = []
    for result in sorted(results, key=lambda x: x[3], reverse=True):
        if result[0] not in seen:
            seen.add(result[0])
            unique_results.append(result)
    
    return unique_results[:max_results]

def highlight_matches(text: str, query: str) -> str:
    """Highlight matching terms in the text."""
    if not query.strip():
        return text
    
    query_words = [word for word in query.lower().split() if len(word) > 2]
    highlighted = text
    
    for word in query_words:
        pattern = re.compile(f'({re.escape(word)})', re.IGNORECASE)
        highlighted = pattern.sub(r'<span class="highlight">\1</span>', highlighted)
    
    return highlighted

def display_results(results: List[Tuple], query: str):
    """Display search results in a formatted way."""
    if not results:
        st.info("🔍 No parts found matching your search criteria. Try different keywords or check spelling.")
        return
    
    st.success(f"✅ Found {len(results)} matching parts")
    
    # Results container
    for idx, (_, part_num, description, score) in enumerate(results):
        score_class = "score-excellent" if score >= 80 else "score-good" if score >= 60 else "score-fair"
        
        with st.container():
            col1, col2, col3, col4 = st.columns([2, 5, 1, 1])
            
            with col1:
                highlighted_part = highlight_matches(part_num, query)
                st.markdown(f'<div class="part-number">{highlighted_part}</div>', unsafe_allow_html=True)
            
            with col2:
                highlighted_desc = highlight_matches(description, query)
                st.markdown(f'<div class="description">{highlighted_desc}</div>', unsafe_allow_html=True)
            
            with col3:
                st.markdown(f'<div class="match-score {score_class}">{score}%</div>', unsafe_allow_html=True)
            
            with col4:
                if st.button("📋 Copy", key=f"copy_{idx}", help="Copy part number"):
                    st.write(f"📋 **{part_num}**")
        
        if idx < len(results) - 1:
            st.markdown("---")

def main():
    """Main Streamlit application."""
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🔧 Parts Finder</h1>
        <p style="margin: 0; opacity: 0.9;">Search parts by number, description, or keywords</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Configuration in sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        sheet_url = st.text_input(
            "Google Sheets CSV URL:",
            value=st.session_state.get('sheet_url', ''),
            help="Paste your published Google Sheets CSV URL here",
            placeholder="https://docs.google.com/spreadsheets/d/.../export?format=csv"
        )
        
        if sheet_url != st.session_state.get('sheet_url', ''):
            st.session_state.sheet_url = sheet_url
            st.cache_data.clear()  # Clear cache when URL changes
        
        st.header("🔍 Search Options")
        max_results = st.selectbox("Max Results:", [20, 50, 100, 200], index=1)
        min_score = st.slider("Minimum Match %:", 20, 80, 40, 5)
        
        st.header("📊 Instructions")
        st.markdown("""
        **Setup Steps:**
        1. Create Google Sheet with `part_number` and `description` columns
        2. File → Share → Publish to web → CSV
        3. Paste CSV URL above
        4. Start searching!
        
        **Search Tips:**
        - Use part numbers: "BRK-001"
        - Use keywords: "brake pad"
        - Mix both: "BRK heavy duty"
        - Partial matches work great
        """)
    
    # Load data
    if not sheet_url:
        st.warning("⚠️ Please enter your Google Sheets CSV URL in the sidebar to get started.")
        st.markdown("""
        ### 🚀 Quick Setup Guide:
        1. **Create a Google Sheet** with columns: `part_number`, `description`
        2. **Add your parts data** to the sheet
        3. **Publish it**: File → Share → Publish to web → CSV format
        4. **Copy the CSV URL** and paste it in the sidebar
        5. **Start searching!**
        """)
        return
    
    # Load and validate data
    with st.spinner("Loading parts database..."):
        df = load_google_sheet(sheet_url)
    
    if df.empty:
        st.error("❌ Could not load parts data. Please check your CSV URL and try again.")
        return
    
    # Display database stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Parts", len(df))
    with col2:
        st.metric("Data Source", "Google Sheets")
    with col3:
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()
    
    # Main search interface
    st.markdown('<div class="search-container">', unsafe_allow_html=True)
    
    search_query = st.text_input(
        "",
        placeholder="🔍 Enter part number, description, or keywords...",
        help="Search by part number (e.g., BRK-001), description keywords (e.g., brake pad), or any combination",
        key="main_search"
    )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Perform search
    if search_query:
        start_time = time.time()
        
        with st.spinner("Searching parts database..."):
            results = advanced_search(search_query, df, max_results, min_score)
        
        search_time = time.time() - start_time
        
        if results:
            st.caption(f"Search completed in {search_time:.2f} seconds")
        
        display_results(results, search_query)
    
    # Show sample data when no search
    else:
        st.subheader("📋 Sample Parts (First 10)")
        if len(df) > 0:
            sample_df = df.head(10)[['part_number', 'description']]
            st.dataframe(
                sample_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "part_number": st.column_config.TextColumn("Part Number", width="medium"),
                    "description": st.column_config.TextColumn("Description", width="large")
                }
            )
        
        # Quick search suggestions
        st.subheader("💡 Try These Sample Searches")
        sample_searches = []
        if len(df) > 0:
            # Get some example part numbers and keywords
            sample_parts = df.head(5)['part_number'].tolist()
            sample_words = []
            for desc in df.head(10)['description'].tolist():
                words = [w for w in desc.lower().split() if len(w) > 3][:2]
                sample_words.extend(words)
            
            sample_searches = sample_parts[:3] + list(set(sample_words))[:3]
        
        if sample_searches:
            cols = st.columns(min(len(sample_searches), 3))
            for i, search_term in enumerate(sample_searches[:3]):
                with cols[i]:
                    if st.button(f"🔍 {search_term}", key=f"sample_{i}"):
                        st.session_state.main_search = search_term
                        st.rerun()

if __name__ == "__main__":
    main()
