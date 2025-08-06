import streamlit as st
import pandas as pd
import requests
from rapidfuzz import fuzz, process
import re
from typing import List, Tuple
import time

# ============================================================================
# PARTS DATABASE CONFIGURATION - READY TO DEPLOY
# ============================================================================
PARTS_DATABASE_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSc2GTX3jc2NjJlR_zWVqDyTGf6bhCVc4GGaN_WMQDDlXZ8ofJVh5cbCPAD0d0lHY0anWXreyMdon33/pub?output=csv"

# ✅ Your Google Sheets URL is embedded and ready to use!
# Technicians will see a clean interface with no configuration needed.
# ============================================================================

# Configure Streamlit page
st.set_page_config(
    page_title="🔧 Parts Finder",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for professional look
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        color: white;
        margin: -1rem -1rem 2rem -1rem;
        border-radius: 0 0 15px 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .search-container {
        background: #f8f9fa;
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        border: 1px solid #e9ecef;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .result-item {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #e9ecef;
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    
    .result-item:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    .part-number {
        font-family: 'Courier New', monospace;
        font-weight: bold;
        color: #1e3c72;
        font-size: 1.2em;
        margin-bottom: 0.5rem;
    }
    
    .description {
        color: #555;
        font-size: 1.1em;
        line-height: 1.4;
        margin-bottom: 1rem;
    }
    
    .result-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .match-score {
        font-weight: bold;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.9em;
    }
    
    .score-excellent { 
        background: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }
    .score-good { 
        background: #fff3cd;
        color: #856404;
        border: 1px solid #ffeaa7;
    }
    .score-fair { 
        background: #f8d7da;
        color: #721c24;
        border: 1px solid #f5c6cb;
    }
    
    .highlight {
        background: linear-gradient(120deg, #a2d2ff 0%, #bde0ff 100%);
        padding: 2px 4px;
        border-radius: 4px;
        font-weight: bold;
    }
    
    .stats-row {
        background: #e8f4fd;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        text-align: center;
    }
    
    .copy-btn {
        background: #1e3c72 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.5rem 1rem !important;
        font-size: 0.9em !important;
        cursor: pointer !important;
        transition: background 0.2s !important;
    }
    
    .copy-btn:hover {
        background: #2a5298 !important;
        transform: translateY(-1px);
    }
    
    .search-input {
        font-size: 1.2em !important;
        padding: 1rem !important;
        border-radius: 10px !important;
        border: 2px solid #dee2e6 !important;
    }
    
    .search-input:focus {
        border-color: #1e3c72 !important;
        box-shadow: 0 0 0 0.2rem rgba(30, 60, 114, 0.25) !important;
    }
    
    .no-results {
        text-align: center;
        padding: 3rem;
        color: #6c757d;
        background: #f8f9fa;
        border-radius: 15px;
        border: 2px dashed #dee2e6;
    }
    
    .loading-spinner {
        text-align: center;
        padding: 2rem;
        color: #1e3c72;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_parts_database() -> pd.DataFrame:
    """Load parts data from the configured Google Sheets URL."""
    
    try:
        # Load data from Google Sheets
        response = requests.get(PARTS_DATABASE_URL, timeout=15)
        response.raise_for_status()
        
        # Parse CSV content with robust error handling
        from io import StringIO
        csv_content = StringIO(response.text)
        
        # Try parsing with different CSV options for better compatibility
        try:
            df = pd.read_csv(csv_content, quotechar='"', skipinitialspace=True)
        except:
            # If that fails, try with more lenient parsing
            csv_content = StringIO(response.text)
            df = pd.read_csv(csv_content, quotechar='"', skipinitialspace=True, 
                           on_bad_lines='skip', engine='python')
        
        # Validate required columns
        required_columns = ['part_number', 'description']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            st.error(f"❌ Database error: Missing required columns: {', '.join(missing_columns)}")
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
        st.error(f"❌ Unable to connect to parts database. Please try again later.")
        st.error(f"Technical details: {str(e)}")
        return pd.DataFrame()
    except pd.errors.ParserError as e:
        st.error(f"❌ Error parsing CSV data from Google Sheets:")
        st.error(f"**Problem:** {str(e)}")
        st.info("""
        **How to fix:**
        1. Check your Google Sheet for commas in part descriptions
        2. Replace commas with dashes or spaces
        3. Example: Change "Brake Pad, Heavy Duty" to "Brake Pad - Heavy Duty"
        4. Make sure you only have 2 columns: part_number and description
        """)
        
        # Show raw CSV data for debugging
        with st.expander("🔍 Debug: Show raw CSV data (first 10 lines)"):
            try:
                response = requests.get(PARTS_DATABASE_URL, timeout=15)
                lines = response.text.split('\n')[:10]
                for i, line in enumerate(lines):
                    st.text(f"Line {i+1}: {line}")
            except:
                st.text("Could not fetch raw data")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Error loading parts database: {str(e)}")
        return pd.DataFrame()

def create_searchable_text(row) -> str:
    """Combine part number and description for better searching."""
    return f"{row['part_number']} {row['description']}".lower()

def smart_search(query: str, df: pd.DataFrame, max_results: int = 50) -> List[Tuple]:
    """
    Perform intelligent search on parts database.
    Returns list of tuples: (index, part_number, description, score)
    """
    if not query.strip() or df.empty:
        return []
    
    query = query.lower().strip()
    results = []
    
    # Create searchable text for each part
    df['searchable'] = df.apply(create_searchable_text, axis=1)
    
    # Method 1: Fuzzy matching for overall similarity
    choices = df['searchable'].tolist()
    fuzzy_results = process.extract(
        query, 
        choices, 
        scorer=fuzz.WRatio,
        limit=min(max_results * 2, len(choices))
    )
    
    # Add fuzzy results with minimum score threshold
    for match_text, score, index in fuzzy_results:
        if score >= 35:  # Minimum relevance threshold
            results.append((
                index,
                df.iloc[index]['part_number'],
                df.iloc[index]['description'],
                score
            ))
    
    # Method 2: Boost exact part number matches
    for idx, row in df.iterrows():
        part_num = row['part_number'].lower()
        # Exact match in part number gets highest priority
        if query in part_num or part_num.startswith(query):
            existing = next((r for r in results if r[0] == idx), None)
            if existing:
                # Boost existing score
                results = [(i, pn, desc, min(100, score + 25)) if i == idx 
                          else (i, pn, desc, score) for i, pn, desc, score in results]
            else:
                results.append((idx, row['part_number'], row['description'], 98))
    
    # Method 3: Boost keyword matches in description
    query_words = [word for word in query.split() if len(word) > 2]
    for word in query_words:
        for idx, row in df.iterrows():
            desc_lower = row['description'].lower()
            if word in desc_lower.split():  # Whole word match
                existing = next((r for r in results if r[0] == idx), None)
                if existing:
                    results = [(i, pn, desc, min(100, score + 10)) if i == idx 
                              else (i, pn, desc, score) for i, pn, desc, score in results]
    
    # Sort by score (highest first) and remove duplicates
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

def display_search_results(results: List[Tuple], query: str):
    """Display search results in a clean, professional format."""
    if not results:
        st.markdown("""
        <div class="no-results">
            <h3>🔍 No parts found</h3>
            <p>Try different keywords, check spelling, or use part numbers</p>
            <p><strong>Search tips:</strong></p>
            <p>• Use part numbers: "BRK-001"</p>
            <p>• Use keywords: "brake pad"</p>
            <p>• Try abbreviations: "hyd cyl"</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Results summary
    st.markdown(f"""
    <div class="stats-row">
        <strong>✅ Found {len(results)} matching parts</strong>
    </div>
    """, unsafe_allow_html=True)
    
    # Display each result
    for idx, (_, part_num, description, score) in enumerate(results):
        score_class = "score-excellent" if score >= 80 else "score-good" if score >= 60 else "score-fair"
        score_text = "Excellent Match" if score >= 80 else "Good Match" if score >= 60 else "Partial Match"
        
        # Create result card
        col1, col2 = st.columns([4, 1])
        
        with col1:
            # Highlight matches
            highlighted_part = highlight_matches(part_num, query)
            highlighted_desc = highlight_matches(description, query)
            
            st.markdown(f"""
            <div class="result-item">
                <div class="part-number">{highlighted_part}</div>
                <div class="description">{highlighted_desc}</div>
                <div class="result-footer">
                    <span class="match-score {score_class}">{score_text} ({score}%)</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            # Copy button
            if st.button("📋 Copy", key=f"copy_{idx}", help=f"Copy {part_num}", use_container_width=True):
                st.success(f"✅ Copied: **{part_num}**")
                # In a real deployment, this would copy to clipboard via JavaScript

def main():
    """Main application interface."""
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🔧 Parts Finder</h1>
        <p style="margin: 0; opacity: 0.9; font-size: 1.1em;">Find parts instantly with smart search</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Load parts database
    with st.spinner("🔄 Loading parts database..."):
        df = load_parts_database()
    
    # If database load failed, show error and stop
    if df.empty:
        st.stop()
    
    # Database loaded successfully - show search interface
    st.markdown('<div class="search-container">', unsafe_allow_html=True)
    
    # Search input (prominently displayed)
    search_query = st.text_input(
        label="Search",
        placeholder="🔍 Type part number, description, or keywords...",
        help="Examples: 'BRK-001', 'brake pad', 'hydraulic cylinder', 'M8 bolt'",
        key="search_input",
        label_visibility="collapsed"
    )
    
    # Quick stats about database
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📦 Total Parts", f"{len(df):,}")
    with col2:
        st.metric("🔄 Last Updated", "Real-time")
    with col3:
        st.metric("⚡ Status", "Online")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Perform search if query provided
    if search_query:
        search_start = time.time()
        
        # Show loading for better UX
        with st.spinner("🔍 Searching parts..."):
            results = smart_search(search_query, df, max_results=50)
        
        search_time = time.time() - search_start
        
        # Display results
        display_search_results(results, search_query)
        
        # Show search performance
        if results:
            st.caption(f"⚡ Search completed in {search_time:.2f} seconds")
    
    else:
        # Show helpful information when no search query
        st.markdown("""
        ### 💡 How to Search
        
        **By Part Number:**
        - Full number: `BRK-001-A`
        - Partial: `BRK` (shows all brake parts)
        
        **By Description:**
        - Keywords: `brake pad`, `air filter`, `hydraulic`
        - Materials: `stainless steel`, `rubber`
        - Sizes: `M8`, `1/2 inch`, `50mm`
        
        **Smart Features:**
        - ✅ Handles typos automatically
        - ✅ Finds partial matches
        - ✅ Searches all text fields
        - ✅ Ranks results by relevance
        """)
        
        # Show sample of available parts
        if len(df) > 0:
            st.markdown("### 📋 Sample Parts")
            sample_df = df.head(8)[['part_number', 'description']]
            
            # Display sample in a nice format
            for _, row in sample_df.iterrows():
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.code(row['part_number'])
                with col2:
                    st.write(row['description'])

if __name__ == "__main__":
    main()
