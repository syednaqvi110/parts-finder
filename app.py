import streamlit as st
import pandas as pd
import requests
from rapidfuzz import fuzz, process
import re
import time
from typing import List, Tuple, Dict, Any
from datetime import datetime
from io import StringIO
import threading
import hashlib

# ============================================================================
# OPTIMIZED CONFIGURATION FOR CONCURRENT USERS
# ============================================================================
PARTS_DATABASE_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSc2GTX3jc2NjJlR_zWVqDyTGf6bhCVc4GGaN_WMQDDlXZ8ofJVh5cbCPAD0d0lHY0anWXreyMdon33/pub?output=csv"

# Optimized settings for concurrent usage
RESULTS_PER_PAGE = 15
SEARCH_DELAY = 0.1  # Reduced delay for better responsiveness
MAX_RESULTS = 50    # Reduced to improve performance
DATA_CACHE_TTL = 600  # 10 minutes cache (longer for better performance)
REQUEST_TIMEOUT = 10  # Shorter timeout to prevent hanging

# ============================================================================
# STREAMLIT PAGE SETUP - OPTIMIZED
# ============================================================================
st.set_page_config(
    page_title="Parts Finder",
    page_icon="🔍",
    layout="centered",
    initial_sidebar_state="collapsed"  # Hide sidebar for cleaner UI
)

# Enhanced CSS with performance optimizations
st.markdown("""
<style>
    /* Hide all Streamlit branding */
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    header {visibility: hidden !important;}
    .stDeployButton {display: none !important;}
    .stDecoration {display: none !important;}
    
    /* Performance optimizations */
    .stApp {
        top: 0px;
    }
    
    /* Enhanced search highlighting */
    .highlight {
        background: linear-gradient(135deg, #fff3cd, #ffeaa7);
        font-weight: bold;
        padding: 2px 4px;
        border-radius: 3px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    /* Improved result styling */
    .search-result {
        border-left: 4px solid #1f77b4;
        padding: 15px 20px;
        margin: 12px 0;
        background: linear-gradient(135deg, #f8f9fa, #ffffff);
        border-radius: 0 10px 10px 0;
        box-shadow: 0 3px 6px rgba(0,0,0,0.1);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .search-result:hover {
        transform: translateX(5px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }
    
    .part-number {
        font-size: 1.25em;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 8px;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
    }
    
    .part-description {
        color: #2c3e50;
        line-height: 1.5;
        font-size: 1.05em;
    }
    
    /* Loading states */
    .loading-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(255, 255, 255, 0.9);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 9999;
    }
    
    /* Improved status messages */
    .status-message {
        padding: 15px 20px;
        border-radius: 10px;
        margin: 15px 0;
        font-weight: 600;
        box-shadow: 0 3px 10px rgba(0,0,0,0.1);
    }
    
    .success { 
        background: linear-gradient(135deg, #d4edda, #c3e6cb); 
        color: #155724; 
        border-left: 5px solid #28a745;
    }
    .error { 
        background: linear-gradient(135deg, #f8d7da, #f5c6cb); 
        color: #721c24; 
        border-left: 5px solid #dc3545;
    }
    .info { 
        background: linear-gradient(135deg, #d1ecf1, #bee5eb); 
        color: #0c5460; 
        border-left: 5px solid #17a2b8;
    }
    
    /* Mobile optimizations */
    @media (max-width: 768px) {
        .search-result {
            padding: 12px;
            margin: 8px 0;
        }
        
        .part-number {
            font-size: 1.1em;
        }
        
        h1 {
            font-size: 2.5em !important;
        }
    }
    
    /* Performance: Reduce animations on mobile */
    @media (max-width: 768px) {
        .search-result {
            transition: none;
        }
        
        .search-result:hover {
            transform: none;
        }
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# ENHANCED SESSION STATE MANAGEMENT FOR CONCURRENT USERS
# ============================================================================
def init_session_state():
    """Initialize session state with user-specific keys."""
    # Generate unique session ID for better concurrent handling
    if 'session_id' not in st.session_state:
        st.session_state.session_id = hashlib.md5(
            f"{datetime.now()}-{id(st.session_state)}".encode()
        ).hexdigest()[:8]
    
    defaults = {
        'search_history': [],
        'current_page': 1,
        'last_search': "",
        'search_results': [],
        'last_search_time': 0,
        'data_load_attempts': 0
    }
    
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

# ============================================================================
# OPTIMIZED DATA LOADING WITH BETTER CONCURRENT HANDLING
# ============================================================================
@st.cache_data(
    ttl=DATA_CACHE_TTL, 
    show_spinner=False,
    max_entries=1,  # Only cache one version to save memory
    persist=True    # Persist across sessions for better performance
)
def load_parts_data():
    """Load parts data with optimized concurrent access and better error handling."""
    
    # Enhanced request with better headers for concurrent access
    headers = {
        'User-Agent': 'PartsFinderApp/2.0 (Optimized for Concurrent Access)',
        'Accept': 'text/csv,text/plain',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Cache-Control': 'no-cache'
    }
    
    try:
        # Use session for connection pooling (better for concurrent requests)
        session = requests.Session()
        session.headers.update(headers)
        
        response = session.get(
            PARTS_DATABASE_URL, 
            timeout=REQUEST_TIMEOUT,
            stream=False  # Load all at once for better caching
        )
        response.raise_for_status()
        
        if not response.text.strip():
            return None, "The data source appears to be empty."
        
        # Optimized CSV parsing with better error handling
        csv_content = response.text
        
        try:
            # Try fast parsing first
            df = pd.read_csv(
                StringIO(csv_content), 
                quotechar='"', 
                skipinitialspace=True,
                dtype=str,  # Read as strings for consistent handling
                na_filter=False  # Prevent unwanted NaN conversions
            )
        except Exception:
            # Fallback to more robust parsing
            df = pd.read_csv(
                StringIO(csv_content), 
                on_bad_lines='skip', 
                engine='python',
                dtype=str,
                na_filter=False
            )
        
        # Enhanced column detection and cleaning
        df.columns = df.columns.str.strip().str.lower()
        
        # More flexible column mapping
        column_mapping = {
            'part_number': ['part_number', 'partnumber', 'part', 'number', 'pn', 'item'],
            'description': ['description', 'desc', 'name', 'title', 'details']
        }
        
        for target_col, possible_cols in column_mapping.items():
            if target_col not in df.columns:
                found_col = None
                for col in df.columns:
                    if any(possible in col for possible in possible_cols):
                        found_col = col
                        break
                if found_col:
                    df = df.rename(columns={found_col: target_col})
        
        # Validate required columns
        if 'part_number' not in df.columns or 'description' not in df.columns:
            available_cols = ', '.join(df.columns.tolist())
            return None, f"Required columns missing. Available: {available_cols}"
        
        # Optimized data cleaning
        original_count = len(df)
        
        # Vectorized cleaning operations for better performance
        df['part_number'] = df['part_number'].astype(str).str.strip()
        df['description'] = df['description'].astype(str).str.strip()
        
        # Remove invalid entries
        valid_mask = (
            (df['part_number'].str.len() > 0) & 
            (df['description'].str.len() > 0) &
            (df['part_number'] != 'nan') &
            (df['description'] != 'nan') &
            (df['part_number'] != '') &
            (df['description'] != '')
        )
        
        df = df[valid_mask]
        
        # Remove duplicates more efficiently
        df = df.drop_duplicates(subset=['part_number'], keep='first')
        
        cleaned_count = len(df)
        
        if df.empty:
            return None, "No valid parts data found after cleaning."
        
        # Pre-create search index for better performance
        df = df.reset_index(drop=True)
        
        # Add metadata for monitoring
        metadata = {
            'loaded_at': datetime.now(),
            'original_count': original_count,
            'cleaned_count': cleaned_count,
            'removed_count': original_count - cleaned_count
        }
        
        return df, metadata
        
    except requests.exceptions.Timeout:
        return None, "Connection timeout. The service may be experiencing high load. Please try again."
    except requests.exceptions.ConnectionError:
        return None, "Cannot connect to data source. Please check your connection and try again."
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response else 'Unknown'
        return None, f"Data source error (HTTP {status_code}). Please try again later."
    except Exception as e:
        return None, f"Unexpected error loading data: {str(e)}"

# ============================================================================
# OPTIMIZED SEARCH ENGINE FOR CONCURRENT USERS
# ============================================================================
def optimized_search(query: str, df: pd.DataFrame) -> List[Tuple]:
    """High-performance search optimized for concurrent users."""
    if not query.strip() or df.empty:
        return []
    
    query = query.lower().strip()
    results = []
    
    # Pre-compile regex for better performance
    word_pattern = re.compile(r'[-_\s\.]+')
    query_words = [word for word in word_pattern.split(query) if len(word) > 1]
    
    if not query_words:
        return []
    
    # Vectorized search for better performance with large datasets
    part_numbers_lower = df['part_number'].str.lower()
    descriptions_lower = df['description'].str.lower()
    
    for idx, (part_num, desc_lower) in enumerate(zip(part_numbers_lower, descriptions_lower)):
        total_score = 0
        matched_words = 0
        
        # Exact matches get highest priority
        if query == part_num:
            total_score = 300
        elif query == desc_lower:
            total_score = 290
        else:
            # Optimized word matching
            for word in query_words:
                word_score = 0
                
                # Part number matching (highest priority)
                if word == part_num:
                    word_score = 200
                elif part_num.startswith(word):
                    word_score = 180 - min(part_num.index(word) * 2, 30)
                elif word in part_num:
                    word_score = 160 - min(part_num.index(word) * 2, 40)
                
                # Description matching (secondary priority)
                if word_score == 0:
                    if word in desc_lower.split():
                        word_score = 120
                    elif word in desc_lower:
                        word_score = 100
                
                if word_score > 0:
                    total_score += word_score
                    matched_words += 1
            
            # Bonus for multiple word matches
            if matched_words > 1 and len(query_words) > 1:
                completeness_bonus = (matched_words / len(query_words)) * 60
                total_score += completeness_bonus
        
        if total_score > 0:
            results.append((idx, df.iloc[idx]['part_number'], df.iloc[idx]['description'], int(total_score)))
    
    # Efficient sorting and limiting
    results.sort(key=lambda x: x[3], reverse=True)
    return results[:MAX_RESULTS]

# ============================================================================
# ENHANCED UI HELPER FUNCTIONS
# ============================================================================
def show_message(message: str, message_type: str = "info"):
    """Show enhanced styled messages."""
    st.markdown(f'<div class="status-message {message_type}">{message}</div>', unsafe_allow_html=True)

def add_to_search_history(query: str):
    """Efficiently manage search history."""
    if query and query.strip():
        # Remove duplicates and maintain order
        history = st.session_state.search_history
        if query in history:
            history.remove(query)
        history.insert(0, query)
        # Keep only last 8 searches for better performance
        st.session_state.search_history = history[:8]

def show_search_result(part_number: str, description: str, query: str):
    """Display optimized search results with highlighting."""
    highlighted_part = highlight_text(part_number, query)
    highlighted_desc = highlight_text(description, query)
    
    st.markdown(f"""
    <div class="search-result">
        <div class="part-number">{highlighted_part}</div>
        <div class="part-description">{highlighted_desc}</div>
    </div>
    """, unsafe_allow_html=True)

def highlight_text(text: str, query: str) -> str:
    """Optimized text highlighting."""
    if not query.strip():
        return text
    
    import html
    escaped_text = html.escape(text)
    query_words = [word for word in query.lower().split() if len(word) > 1]
    
    if not query_words:
        return escaped_text
    
    # Efficient highlighting with regex
    for word in query_words:
        if len(word) > 2:  # Only highlight meaningful words
            pattern = re.compile(f'({re.escape(word)})', re.IGNORECASE)
            escaped_text = pattern.sub(r'<span class="highlight">\1</span>', escaped_text)
    
    return escaped_text

def show_pagination(current_page: int, total_pages: int, results_count: int, base_key: str):
    """Enhanced pagination with better UX."""
    if total_pages <= 1:
        return current_page
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown(f"""
        <div class="status-message info" style="text-align: center;">
            Page {current_page} of {total_pages} • {results_count:,} results found
        </div>
        """, unsafe_allow_html=True)
        
        prev_col, next_col = st.columns(2)
        
        with prev_col:
            if current_page > 1 and st.button("← Previous", key=f"prev_{base_key}"):
                return current_page - 1
        
        with next_col:
            if current_page < total_pages and st.button("Next →", key=f"next_{base_key}"):
                return current_page + 1
    
    return current_page

# ============================================================================
# MAIN APPLICATION - OPTIMIZED FOR CONCURRENT USERS
# ============================================================================
def main():
    """Main application with optimizations for concurrent usage."""
    
    # Initialize session state
    init_session_state()
    
    # Enhanced header
    st.markdown("""
    <div style='text-align: center; padding: 20px 0;'>
        <h1 style='font-size: 4em; background: linear-gradient(135deg, #1f77b4, #17a2b8); 
                   -webkit-background-clip: text; -webkit-text-fill-color: transparent; 
                   margin-bottom: 10px;'>Parts Finder</h1>
        <p style='color: #6c757d; font-size: 1.1em;'>Fast, reliable parts search for multiple users</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Load data with progress indicator
    with st.spinner("🔄 Loading parts database..."):
        df, error_or_metadata = load_parts_data()
    
    # Enhanced status display
    if isinstance(error_or_metadata, str):  # Error case
        show_message(f"⚠️ {error_or_metadata}", "error")
        st.markdown("### 🔧 Troubleshooting:")
        st.markdown("- The service might be experiencing high load")
        st.markdown("- Try refreshing the page in a few seconds")
        st.markdown("- Check your internet connection")
        return
    else:  # Success case
        metadata = error_or_metadata
        load_time = metadata['loaded_at'].strftime("%H:%M:%S")
        show_message(
            f"✅ Successfully loaded {metadata['cleaned_count']:,} parts at {load_time}", 
            "success"
        )
    
    # Enhanced search input with better UX
    st.markdown("### 🔍 Search Parts")
    search_query = st.text_input(
        "",
        placeholder="Enter part number or description... (e.g., M1433, motor, sensor)",
        key="search_input",
        help="💡 Tip: Try partial part numbers or key words from descriptions"
    )
    
    # Show recent searches if no current search
    if not search_query.strip():
        if st.session_state.search_history:
            st.markdown("**Recent searches:**")
            cols = st.columns(min(len(st.session_state.search_history), 4))
            for i, search in enumerate(st.session_state.search_history[:4]):
                col_idx = i % len(cols)
                with cols[col_idx]:
                    if st.button(f"🕐 {search}", key=f"recent_{i}"):
                        st.session_state.search_input = search
                        st.rerun()
        return
    
    # Debounce search for better performance under load
    current_time = time.time()
    if current_time - st.session_state.last_search_time < SEARCH_DELAY:
        time.sleep(SEARCH_DELAY)
    st.session_state.last_search_time = current_time
    
    # Perform optimized search
    with st.spinner("🔍 Searching..."):
        results = optimized_search(search_query, df)
    
    # Add to search history
    add_to_search_history(search_query)
    
    # Handle no results
    if not results:
        show_message(f"No results found for \"{search_query}\"", "info")
        
        # Enhanced suggestions
        st.markdown("### 💡 Search Tips:")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("- Try shorter keywords")
            st.markdown("- Use partial part numbers")
        with col2:
            st.markdown("- Check spelling")
            st.markdown("- Try different terms")
        return
    
    # Pagination logic
    total_results = len(results)
    total_pages = (total_results + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE
    current_page = min(st.session_state.current_page, total_pages)
    
    # Show pagination (top)
    new_page = show_pagination(current_page, total_pages, total_results, "top")
    if new_page != current_page:
        st.session_state.current_page = new_page
        st.rerun()
    
    # Show results for current page
    start_idx = (current_page - 1) * RESULTS_PER_PAGE
    end_idx = min(start_idx + RESULTS_PER_PAGE, total_results)
    page_results = results[start_idx:end_idx]
    
    # Display results
    for _, part_number, description, score in page_results:
        show_search_result(part_number, description, search_query)
    
    # Show pagination (bottom) if needed
    if total_pages > 1:
        st.markdown("<br>", unsafe_allow_html=True)
        new_page = show_pagination(current_page, total_pages, total_results, "bottom")
        if new_page != current_page:
            st.session_state.current_page = new_page
            st.rerun()
    
    # Performance info for monitoring
    if st.checkbox("Show performance info", key="perf_info"):
        st.markdown("### ⚡ Performance Metrics")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Results Found", f"{total_results:,}")
        with col2:
            st.metric("Current Page", f"{current_page}/{total_pages}")
        with col3:
            st.metric("Session ID", st.session_state.session_id)

# ============================================================================
# FOOTER WITH CONTACT INFO
# ============================================================================
def show_footer():
    """Enhanced footer."""
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #6c757d; padding: 20px 0;'>
        <p><strong>Parts Finder v2.0</strong> - Optimized for Multiple Users</p>
        <p>For support or feedback: 
        <a href='mailto:Syed.naqvi@bgis.com' style='color: #1f77b4; text-decoration: none;'>
        ✉️ Syed.naqvi@bgis.com</a></p>
    </div>
    """, unsafe_allow_html=True)

# ============================================================================
# RUN THE OPTIMIZED APP
# ============================================================================
if __name__ == "__main__":
    try:
        main()
        show_footer()
    except Exception as e:
        st.error(f"Application error: {str(e)}")
        st.info("Please refresh the page or contact support if the issue persists.")
