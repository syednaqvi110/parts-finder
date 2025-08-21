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
    
    /* Mobile responsiveness */
    @media (max-width: 768px) {
        .stats-container {
            flex-direction: column;
        }
        
        .stat-item {
            min-width: auto;
        }
        
        .pagination {
            flex-wrap: wrap;
        }
        
        /* Mobile-friendly title */
        h1 {
            font-size: 2.5em !important;
            line-height: 1.2 !important;
            margin-bottom: 20px !important;
        }
        
        /* Make search results more mobile-friendly */
        .search-result {
            padding: 10px;
            margin: 8px 0;
        }
        
        .part-number {
            font-size: 1.1em;
        }
        
        .part-description {
            font-size: 1em;
        }
        
        /* Mobile input fixes */
        .stTextInput > div > div > input {
            font-size: 16px;  /* Prevents zoom on iOS */
        }
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
    """Load parts data from Google Sheets with comprehensive error handling."""
    try:
        # Try to load the data
        response = requests.get(PARTS_DATABASE_URL, timeout=15)
        response.raise_for_status()
        
        if not response.text.strip():
            return None, "The data source appears to be empty."
        
        # Parse the CSV with multiple strategies
        try:
            df = pd.read_csv(StringIO(response.text), quotechar='"', skipinitialspace=True)
        except:
            # Try alternative parsing if the first method fails
            try:
                df = pd.read_csv(StringIO(response.text), on_bad_lines='skip', engine='python')
            except:
                df = pd.read_csv(StringIO(response.text), sep=None, engine='python', on_bad_lines='skip')
        
        # Check if we have the required columns
        if 'part_number' not in df.columns or 'description' not in df.columns:
            # Try to find similar column names (case insensitive)
            df.columns = df.columns.str.strip().str.lower()
            
            # Look for part_number column
            if 'part_number' not in df.columns:
                part_cols = [col for col in df.columns if 'part' in col or 'number' in col or 'item' in col]
                if part_cols:
                    df = df.rename(columns={part_cols[0]: 'part_number'})
                    
            # Look for description column
            if 'description' not in df.columns:
                desc_cols = [col for col in df.columns if 'desc' in col or 'name' in col or 'title' in col]
                if desc_cols:
                    df = df.rename(columns={desc_cols[0]: 'description'})
        
        # Final check for required columns
        if 'part_number' not in df.columns or 'description' not in df.columns:
            available_cols = ', '.join(df.columns.tolist())
            return None, f"The spreadsheet must have 'part_number' and 'description' columns. Found columns: {available_cols}"
        
        # Clean and validate the data
        original_count = len(df)
        
        # Convert to string and strip whitespace
        df['part_number'] = df['part_number'].astype(str).str.strip()
        df['description'] = df['description'].astype(str).str.strip()
        
        # Remove rows with missing or invalid data
        df = df.dropna(subset=['part_number', 'description'])
        df = df[df['part_number'].str.len() > 0]
        df = df[df['description'].str.len() > 0]
        df = df[df['part_number'] != 'nan']
        df = df[df['description'] != 'nan']
        df = df[df['part_number'] != 'None']
        df = df[df['description'] != 'None']
        
        # Remove duplicates based on part number
        df = df.drop_duplicates(subset=['part_number'], keep='first')
        
        if df.empty:
            return None, "No valid parts data found after cleaning."
        
        cleaned_count = len(df)
        removed_count = original_count - cleaned_count
        
        if removed_count > 0:
            print(f"Data cleaning: removed {removed_count} invalid rows from {original_count} total")
        
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
    """Advanced search algorithm that prioritizes relevance and completeness."""
    if not query.strip() or df.empty:
        return []
    
    query = query.lower().strip()
    results = []
    
    # Split query into individual words for keyword matching
    query_words = [word for word in re.split(r'[-_\s\.]+', query) if len(word) > 1]
    
    if not query_words:
        return []
    
    for idx, row in df.iterrows():
        part_num = row['part_number'].lower()
        desc_lower = row['description'].lower()
        
        # Calculate match score for this item
        total_score = 0
        matched_words = 0
        
        # Strategy 1: Exact matches (highest priority)
        if query == part_num:
            total_score = 300  # Perfect part number match
        elif query == desc_lower:
            total_score = 280  # Perfect description match
        else:
            # Strategy 2: Check each query word for matches
            for word in query_words:
                word_score = 0
                
                # Check part number for this word
                if word == part_num:
                    word_score = 200  # Exact part number match
                elif len(word) >= 3 and part_num.startswith(word):
                    word_score = 150  # Part number starts with word
                elif len(word) >= 3 and word in part_num:
                    # Word found somewhere in part number
                    position = part_num.index(word)
                    word_score = 140 - min(position * 3, 40)  # Earlier position = higher score
                
                # If not found in part number, check description
                if word_score == 0:
                    if word in desc_lower.split():
                        word_score = 100  # Exact word match in description
                    elif len(word) >= 3 and word in desc_lower:
                        word_score = 80   # Partial match in description
                    else:
                        # Check if word is part of any description word
                        for desc_word in desc_lower.split():
                            if len(word) >= 3 and word in desc_word:
                                word_score = 60
                                break
                
                # Add to total score
                if word_score > 0:
                    total_score += word_score
                    matched_words += 1
            
            # Boost score if we matched multiple words (keyword completeness)
            if matched_words > 1:
                completeness_bonus = (matched_words / len(query_words)) * 50
                total_score += completeness_bonus
            
            # Additional bonuses for common search patterns
            if query in part_num:
                total_score += 30  # Substring match in part number
            elif query in desc_lower:
                total_score += 20  # Substring match in description
        
        # Only include items that have meaningful matches
        if total_score > 0:
            results.append((idx, row['part_number'], row['description'], int(total_score)))
    
    # Sort by score (highest first) and return top results
    results.sort(key=lambda x: x[3], reverse=True)
    return results[:MAX_RESULTS]

def highlight_text(text: str, query: str) -> str:
    """Highlight search terms in text with protection against double-highlighting and proper word boundaries."""
    if not query.strip():
        return text
    
    # If text already contains highlight spans, don't process it again
    if '<span class="highlight">' in text:
        return text
    
    # Extract meaningful words from query
    query_words = [word for word in re.split(r'[-_\s\.]+', query.lower()) if len(word) > 1]
    highlighted = text
    
    # Sort words by length (longest first) to avoid partial matches inside other matches
    query_words.sort(key=len, reverse=True)
    
    for word in query_words:
        # Only highlight complete words or longer substrings to avoid issues like "ass" in "assembly"
        if len(word) >= 3:
            # Use word boundaries for complete words, or exact matches for shorter ones
            pattern = re.compile(rf'\b({re.escape(word)})\b', re.IGNORECASE)
            highlighted = pattern.sub(r'<span class="highlight">\1</span>', highlighted)
        elif len(word) == 2:
            # For 2-character words, be more careful - only match if it's a complete word
            pattern = re.compile(rf'\b({re.escape(word)})\b', re.IGNORECASE)
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
    """Add search to history (keep last 10 unique searches)."""
    if query and query.strip():
        query = query.strip()
        # Remove if already exists
        if query in st.session_state.search_history:
            st.session_state.search_history.remove(query)
        # Add to front
        st.session_state.search_history.insert(0, query)
        # Keep only last 10
        if len(st.session_state.search_history) > 10:
            st.session_state.search_history = st.session_state.search_history[:10]

def show_recent_searches():
    """Show recent searches as clickable buttons."""
    if st.session_state.search_history:
        st.markdown("**Recent searches:**")
        
        # Show up to 5 recent searches
        recent_count = min(len(st.session_state.search_history), 5)
        cols = st.columns(recent_count)
        
        for i, search in enumerate(st.session_state.search_history[:recent_count]):
            with cols[i]:
                if st.button(f"🕐 {search}", key=f"recent_{i}_{search}", help="Click to search again"):
                    st.session_state.search_input = search
                    st.rerun()

def show_search_result(part_number: str, description: str, query: str):
    """Display a single search result with highlighting."""
    highlighted_part = highlight_text(part_number, query)
    highlighted_desc = highlight_text(description, query)
    
    st.markdown(f"""
    <div class="search-result">
        <div class="part-number">{highlighted_part}</div>
        <div class="part-description">{highlighted_desc}</div>
    </div>
    """, unsafe_allow_html=True)

def show_pagination(current_page: int, total_pages: int, results_count: int, position: str = ""):
    """Show pagination controls with page information."""
    if total_pages <= 1:
        return current_page
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Show page info
        start_result = (current_page - 1) * RESULTS_PER_PAGE + 1
        end_result = min(current_page * RESULTS_PER_PAGE, results_count)
        
        st.markdown(f"""
        <div class='stats'>
            Page {current_page} of {total_pages} • Showing {start_result}-{end_result} of {results_count} results
        </div>
        """, unsafe_allow_html=True)
        
        # Navigation buttons
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

def show_search_tips():
    """Show helpful search tips."""
    with st.expander("💡 Search Tips", expanded=False):
        st.markdown("""
        **How to search effectively:**
        
        🔍 **Part Numbers:** Type the exact part number or just the beginning  
        📝 **Descriptions:** Use keywords like "valve", "pump", "filter"  
        🎯 **Multiple Words:** Search for "pump valve" to find items with both words  
        ⭐ **Partial Matches:** "M14" will find "M1433", "M1456", etc.  
        
        **Examples:**
        - `M1433` - Find exact part number
        - `pump` - Find all pumps
        - `valve assembly` - Find valve assemblies
        - `OPW` - Find all OPW brand parts
        """)

def show_footer():
    """Display footer with contact information and app info."""
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #6c757d; font-size: 0.9em; padding: 20px 0;'>
        <p><strong>Need Help or Have Feedback?</strong></p>
        <p>For any issues, suggestions, or feedback about this Parts Finder tool, please email:</p>
        <p><a href='mailto:Syed.naqvi@bgis.com' style='color: #1f77b4; text-decoration: none;'>✉️ Syed.naqvi@bgis.com</a></p>
        <p style='margin-top: 15px; font-size: 0.8em; color: #999;'>
            Parts Finder v2.1 • Built with Streamlit
        </p>
    </div>
    """, unsafe_allow_html=True)

# ============================================================================
# MAIN APPLICATION
# ============================================================================
def main():
    """Main application function."""
    
    # App title with improved styling
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <h1 style='text-align: center; font-size: 3.5em; margin-bottom: 30px; color: #1f77b4;'>
        🔧 Parts Finder
    </h1>
    """, unsafe_allow_html=True)
    
    # Load data with progress indicator
    with st.spinner("🔄 Loading parts database..."):
        df, error = load_parts_data()
    
    # Show data loading status
    if error:
        show_message(f"⚠️ {error}", "error")
        st.markdown("**Troubleshooting:**")
        st.markdown("1. Check your internet connection")
        st.markdown("2. Verify the Google Sheet is published as CSV")
        st.markdown("3. Ensure the sheet has 'part_number' and 'description' columns")
        st.markdown("4. Try refreshing the page")
        show_footer()
        return
    else:
        show_message(f"✅ Successfully loaded {len(df):,} parts from database", "success")
    
    # Search input with enhanced placeholder
    search_query = st.text_input(
        "🔍 Search for parts:",
        placeholder="Enter part number, description, or keywords...",
        key="search_input",
        help="Search by part number (e.g., M1433) or description keywords (e.g., pump valve)"
    )
    
    # Show search tips and recent searches when no active search
    if not search_query.strip():
        col1, col2 = st.columns([1, 1])
        
        with col1:
            show_search_tips()
        
        with col2:
            if st.session_state.search_history:
                st.markdown("**🕐 Recent Searches:**")
                for i, search in enumerate(st.session_state.search_history[:5]):
                    if st.button(f"🔍 {search}", key=f"recent_main_{i}"):
                        st.session_state.search_input = search
                        st.rerun()
        
        show_footer()
        return
    
    # Add slight delay to prevent excessive searching while typing
    if search_query != st.session_state.last_search:
        st.session_state.last_search = search_query
        time.sleep(SEARCH_DELAY)
    
    # Perform search
    with st.spinner("🔍 Searching..."):
        results = smart_search(search_query, df)
    
    # Add to search history
    add_to_search_history(search_query)
    
    # Handle no results
    if not results:
        show_message(f"❌ No results found for \"{search_query}\"", "info")
        
        st.markdown("**💡 Try these suggestions:**")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("• Check spelling")
            st.markdown("• Use fewer words")
        with col2:
            st.markdown("• Try partial part numbers")
            st.markdown("• Use different keywords")
        
        # Show recent searches as alternatives
        if st.session_state.search_history:
            st.markdown("**Or try a recent search:**")
            for search in st.session_state.search_history[:3]:
                if st.button(f"🔍 {search}", key=f"alt_search_{search}"):
                    st.session_state.search_input = search
                    st.rerun()
        
        show_footer()
        return
    
    # Calculate pagination
    total_results = len(results)
    total_pages = (total_results + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE
    current_page = st.session_state.current_page
    
    # Validate current page
    if current_page > total_pages:
        current_page = 1
        st.session_state.current_page = 1
    
    # Show search summary
    st.markdown(f"**🎯 Found {total_results} results for \"{search_query}\"**")
    
    # Show pagination controls (top)
    new_page = show_pagination(current_page, total_pages, total_results, "top")
    if new_page != current_page:
        st.session_state.current_page = new_page
        st.rerun()
    
    # Display results for current page
    start_idx = (current_page - 1) * RESULTS_PER_PAGE
    end_idx = start_idx + RESULTS_PER_PAGE
    page_results = results[start_idx:end_idx]
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Render each search result
    for _, part_number, description, score in page_results:
        show_search_result(part_number, description, search_query)
    
    # Show pagination controls (bottom) if there are multiple pages
    if total_pages > 1:
        st.markdown("<br>", unsafe_allow_html=True)
        new_page = show_pagination(current_page, total_pages, total_results, "bottom")
        if new_page != current_page:
            st.session_state.current_page = new_page
            st.rerun()
    
    # Always show footer
    show_footer()

# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    main()
