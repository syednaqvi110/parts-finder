import streamlit as st
import pandas as pd
import requests
from rapidfuzz import fuzz, process
import re
import time
from typing import List, Tuple, Dict, Any
from datetime import datetime
from io import StringIO

# ============================================================================
# SIMPLE CONFIGURATION - JUST CHANGE THE URL BELOW
# ============================================================================
PARTS_DATABASE_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSc2GTX3jc2NjJlR_zWVqDyTGf6bhCVc4GGaN_WMQDDlXZ8ofJVh5cbCPAD0d0lHY0anWXreyMdon33/pub?output=csv"

# Basic settings (you can adjust these if needed)
RESULTS_PER_PAGE = 15           # How many results to show per page
SEARCH_DELAY = 0.3              # Seconds to wait before searching (prevents lag)
MAX_RESULTS = 100               # Maximum results to find

# ============================================================================
# STREAMLIT PAGE SETUP
# ============================================================================
st.set_page_config(
    page_title="Parts Finder",
    page_icon="🔧",
    layout="centered"
)

# Custom CSS for better appearance
st.markdown("""
<style>
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display:none;}
    .stDecoration {display:none;}
    
    /* Search result highlighting */
    .highlight {
        background-color: #fff3cd;
        font-weight: bold;
        padding: 1px 2px;
        border-radius: 2px;
    }
    
    /* Result styling */
    .search-result {
        border-left: 4px solid #1f77b4;
        padding: 15px;
        margin: 10px 0;
        background-color: #f8f9fa;
        border-radius: 0 8px 8px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .part-number {
        font-size: 1.2em;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 8px;
    }
    
    .part-description {
        color: #333;
        line-height: 1.4;
        font-size: 1.05em;
    }
    
    /* Error and info messages */
    .error-box {
        background-color: #f8d7da;
        color: #721c24;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #f5c6cb;
        margin: 15px 0;
    }
    
    .info-box {
        background-color: #d1ecf1;
        color: #0c5460;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #bee5eb;
        margin: 15px 0;
    }
    
    .success-box {
        background-color: #d4edda;
        color: #155724;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #c3e6cb;
        margin: 15px 0;
    }
    
    /* Loading spinner */
    .loading {
        text-align: center;
        padding: 20px;
        color: #6c757d;
    }
    
    /* Recent searches */
    .recent-search {
        display: inline-block;
        background-color: #e9ecef;
        color: #495057;
        padding: 6px 12px;
        margin: 4px;
        border-radius: 15px;
        font-size: 0.9em;
        cursor: pointer;
        border: 1px solid #dee2e6;
    }
    
    /* Statistics */
    .stats {
        background-color: #f8f9fa;
        padding: 10px 15px;
        border-radius: 8px;
        margin: 10px 0;
        border: 1px solid #dee2e6;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# SESSION STATE SETUP
# ============================================================================
if 'search_history' not in st.session_state:
    st.session_state.search_history = []
if 'current_page' not in st.session_state:
    st.session_state.current_page = 1
if 'last_search' not in st.session_state:
    st.session_state.last_search = ""

# ============================================================================
# DATA LOADING FUNCTIONS
# ============================================================================
@st.cache_data(ttl=300, show_spinner=False)  # Cache for 5 minutes
def load_parts_data():
    """Load parts data from Google Sheets with good error handling."""
    try:
        # Try to load the data
        response = requests.get(PARTS_DATABASE_URL, timeout=15)
        response.raise_for_status()
        
        if not response.text.strip():
            return None, "The data source appears to be empty."
        
        # Parse the CSV
        try:
            df = pd.read_csv(StringIO(response.text), quotechar='"', skipinitialspace=True)
        except:
            # Try alternative parsing if the first method fails
            df = pd.read_csv(StringIO(response.text), on_bad_lines='skip', engine='python')
        
        # Check if we have the required columns
        if 'part_number' not in df.columns or 'description' not in df.columns:
            # Try to find similar column names
            df.columns = df.columns.str.strip().str.lower()
            if 'part_number' not in df.columns:
                part_cols = [col for col in df.columns if 'part' in col or 'number' in col]
                if part_cols:
                    df = df.rename(columns={part_cols[0]: 'part_number'})
            if 'description' not in df.columns:
                desc_cols = [col for col in df.columns if 'desc' in col or 'name' in col]
                if desc_cols:
                    df = df.rename(columns={desc_cols[0]: 'description'})
        
        # Final check for required columns
        if 'part_number' not in df.columns or 'description' not in df.columns:
            return None, "The spreadsheet must have 'part_number' and 'description' columns."
        
        # Clean the data
        df['part_number'] = df['part_number'].astype(str).str.strip()
        df['description'] = df['description'].astype(str).str.strip()
        df = df.dropna(subset=['part_number', 'description'])
        df = df[df['part_number'].str.len() > 0]
        df = df[df['description'].str.len() > 0]
        df = df[df['part_number'] != 'nan']
        df = df[df['description'] != 'nan']
        
        if df.empty:
            return None, "No valid parts data found after cleaning."
        
        return df.reset_index(drop=True), None
        
    except requests.exceptions.Timeout:
        return None, "Connection timeout. Please check your internet connection and try again."
    except requests.exceptions.ConnectionError:
        return None, "Cannot connect to the data source. Please check your internet connection."
    except requests.exceptions.HTTPError as e:
        return None, f"Data source error (HTTP {e.response.status_code}). Please check the spreadsheet URL."
    except Exception as e:
        return None, f"Error loading data: {str(e)}"

# ============================================================================
# SEARCH FUNCTIONS
# ============================================================================
def smart_search(query: str, df: pd.DataFrame) -> List[Tuple]:
    """Smart search that prioritizes keyword completeness - UPDATED VERSION."""
    if not query.strip() or df.empty:
        return []
    
    query = query.lower().strip()
    results = []
    
    # Split query into keywords (filter out very short words)
    query_words = set([word for word in re.split(r'[-_\s\.]+', query) if len(word) > 1])
    
    if not query_words:
        return []
    
    for idx, row in df.iterrows():
        part_num = row['part_number'].lower()
        desc_lower = row['description'].lower()
        
        # Get all words from part number and description
        part_words = set(re.split(r'[-_\s\.]+', part_num))
        desc_words = set(desc_lower.split())
        all_item_words = part_words.union(desc_words)
        
        # Count keyword matches
        matched_keywords = query_words.intersection(all_item_words)
        
        if not matched_keywords:
            continue  # No matches, skip this item
        
        # KEYWORD COMPLETENESS SCORE (most important factor)
        match_ratio = len(matched_keywords) / len(query_words)
        base_score = int(match_ratio * 100)  # 0-100 based on % of keywords matched
        
        # Bonus for part number matches (part numbers are more important than descriptions)
        part_matches = len(query_words.intersection(part_words))
        if part_matches > 0:
            base_score += 25
        
        # Additional bonuses for exact/prefix matches
        if query == part_num:
            base_score += 50  # Exact part number match
        elif query == desc_lower:
            base_score += 40  # Exact description match
        elif part_num.startswith(query):
            base_score += 30  # Part number starts with query
        elif desc_lower.startswith(query):
            base_score += 25  # Description starts with query
        elif query in part_num:
            # Substring bonus based on position (earlier = better)
            position = part_num.index(query)
            position_bonus = max(0, 20 - position)
            base_score += position_bonus
        elif query in desc_lower:
            position = desc_lower.index(query)
            position_bonus = max(0, 15 - position)
            base_score += position_bonus
        
        results.append((idx, row['part_number'], row['description'], base_score))
    
    # Sort by score (highest first) and return top results
    results.sort(key=lambda x: x[3], reverse=True)
    return results[:MAX_RESULTS]

def highlight_text(text: str, query: str) -> str:
    """Highlight search terms in text."""
    if not query.strip():
        return text
    
    query_words = [word for word in query.lower().split() if len(word) > 1]
    highlighted = text
    
    for word in query_words:
        pattern = re.compile(f'({re.escape(word)})', re.IGNORECASE)
        highlighted = pattern.sub(r'<span class="highlight">\1</span>', highlighted)
    
    return highlighted

# ============================================================================
# UI HELPER FUNCTIONS
# ============================================================================
def show_message(message: str, message_type: str = "info"):
    """Show a styled message to the user."""
    css_class = f"{message_type}-box"
    st.markdown(f'<div class="{css_class}">{message}</div>', unsafe_allow_html=True)

def add_to_search_history(query: str):
    """Add search to history (keep last 10)."""
    if query and query not in st.session_state.search_history:
        st.session_state.search_history.insert(0, query)
        if len(st.session_state.search_history) > 10:
            st.session_state.search_history.pop()

def show_recent_searches():
    """Show recent searches as clickable buttons."""
    if st.session_state.search_history:
        st.markdown("**Recent searches:**")
        cols = st.columns(min(len(st.session_state.search_history), 5))
        for i, search in enumerate(st.session_state.search_history[:5]):
            col_idx = i % len(cols)
            with cols[col_idx]:
                if st.button(f"🕒 {search}", key=f"recent_{i}"):
                    st.session_state.search_input = search
                    st.rerun()

def show_search_result(part_number: str, description: str, query: str):
    """Display a single search result."""
    highlighted_part = highlight_text(part_number, query)
    highlighted_desc = highlight_text(description, query)
    
    st.markdown(f"""
    <div class="search-result">
        <div class="part-number">{highlighted_part}</div>
        <div class="part-description">{highlighted_desc}</div>
    </div>
    """, unsafe_allow_html=True)

def show_pagination(current_page: int, total_pages: int, results_count: int, position: str = ""):
    """Show pagination controls."""
    if total_pages <= 1:
        return current_page
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown(f"<div class='stats'>Page {current_page} of {total_pages} • {results_count} total results</div>", 
                   unsafe_allow_html=True)
        
        prev_col, next_col = st.columns(2)
        
        with prev_col:
            if current_page > 1:
                if st.button("← Previous", key=f"prev_page_{position}"):
                    return current_page - 1
        
        with next_col:
            if current_page < total_pages:
                if st.button("Next →", key=f"next_page_{position}"):
                    return current_page + 1
    
    return current_page

# ============================================================================
# MAIN APPLICATION
# ============================================================================
def main():
    """Main application function."""
    
    # App title
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; font-size: 4em; margin-bottom: 30px;'>🔧 Parts Finder</h1>", 
               unsafe_allow_html=True)
    
    # Load data
    with st.spinner("Loading parts database..."):
        df, error = load_parts_data()
    
    # Show data status
    if error:
        show_message(f"⚠️ {error}", "error")
        st.markdown("**Troubleshooting tips:**")
        st.markdown("1. Check your internet connection")
        st.markdown("2. Make sure the Google Sheet is published as CSV")
        st.markdown("3. Verify the sheet has 'part_number' and 'description' columns")
        return
    else:
        show_message(f"✅ Successfully loaded {len(df):,} parts", "success")
    
    # Search input
    search_query = st.text_input(
        "Search for parts:",
        placeholder="Enter part number or description...",
        key="search_input",
        help="Try typing a part number, description, or even partial matches. The search is smart and handles typos!"
    )
    
    # Show recent searches if no current search
    if not search_query.strip():
        show_recent_searches()
        return
    
    # Add delay to prevent too many searches while typing
    if search_query != st.session_state.last_search:
        st.session_state.last_search = search_query
        time.sleep(SEARCH_DELAY)
    
    # Perform search
    results = smart_search(search_query, df)
    
    # Add to search history
    add_to_search_history(search_query)
    
    # Handle no results
    if not results:
        show_message(f"No results found for \"{search_query}\"", "info")
        st.markdown("**Try:**")
        st.markdown("• Check spelling")
        st.markdown("• Use fewer words")
        st.markdown("• Try partial part numbers")
        st.markdown("• Use different keywords")
        return
    
    # Calculate pagination
    total_results = len(results)
    total_pages = (total_results + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE
    current_page = st.session_state.current_page
    
    # Make sure current page is valid
    if current_page > total_pages:
        current_page = 1
        st.session_state.current_page = 1
    
    # Show pagination controls (top)
    new_page = show_pagination(current_page, total_pages, total_results, "top")
    if new_page != current_page:
        st.session_state.current_page = new_page
        st.rerun()
    
    # Show results for current page
    start_idx = (current_page - 1) * RESULTS_PER_PAGE
    end_idx = start_idx + RESULTS_PER_PAGE
    page_results = results[start_idx:end_idx]
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    for _, part_number, description, score in page_results:
        show_search_result(part_number, description, search_query)
    
    # Show pagination controls (bottom)
    if total_pages > 1:
        st.markdown("<br>", unsafe_allow_html=True)
        new_page = show_pagination(current_page, total_pages, total_results, "bottom")
        if new_page != current_page:
            st.session_state.current_page = new_page
            st.rerun()

# ============================================================================
# RUN THE APP
# ============================================================================
if __name__ == "__main__":
    main()
