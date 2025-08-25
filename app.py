import streamlit as st
import pandas as pd
from rapidfuzz import fuzz, process
import re
import time
from typing import List, Tuple, Dict, Any
from datetime import datetime
import threading
import hashlib
import os

# ============================================================================
# LOCAL FILE CONFIGURATION - NO MORE HTTP REQUESTS!
# ============================================================================
PARTS_DATA_FILE = "parts_data.csv"  # Local CSV file
RESULTS_PER_PAGE = 15
SEARCH_DELAY = 0.1
MAX_RESULTS = 50

# ============================================================================
# STREAMLIT PAGE SETUP - OPTIMIZED
# ============================================================================
st.set_page_config(
    page_title="Parts Finder",
    page_icon="🔍",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Enhanced CSS (same as before)
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
    
    /* Status messages */
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
# SESSION STATE MANAGEMENT
# ============================================================================
def init_session_state():
    """Initialize session state."""
    if 'session_id' not in st.session_state:
        st.session_state.session_id = hashlib.md5(
            f"{datetime.now()}-{id(st.session_state)}".encode()
        ).hexdigest()[:8]
    
    defaults = {
        'search_history': [],
        'current_page': 1,
        'last_search': "",
        'search_results': [],
        'last_search_time': 0
    }
    
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

# ============================================================================
# LOCAL FILE DATA LOADING - SUPER FAST & RELIABLE!
# ============================================================================
@st.cache_data(show_spinner=False, persist=True)
def load_parts_data():
    """Load parts data from local CSV file - much faster and more reliable!"""
    
    try:
        # Check if file exists
        if not os.path.exists(PARTS_DATA_FILE):
            return None, f"Parts data file '{PARTS_DATA_FILE}' not found. Please ensure the file is in the same directory as app.py"
        
        # Load CSV file with robust settings to handle Google Sheets copy-paste issues
        try:
            # First attempt: Standard CSV reading
            df = pd.read_csv(
                PARTS_DATA_FILE,
                dtype=str,
                na_filter=False,
                encoding='utf-8'
            )
        except Exception:
            try:
                # Second attempt: More robust parsing for problematic data
                df = pd.read_csv(
                    PARTS_DATA_FILE,
                    dtype=str,
                    na_filter=False,
                    encoding='utf-8',
                    quotechar='"',
                    skipinitialspace=True,
                    on_bad_lines='skip'  # Skip problematic lines
                )
            except Exception:
                # Third attempt: Use Python engine with maximum flexibility
                df = pd.read_csv(
                    PARTS_DATA_FILE,
                    dtype=str,
                    na_filter=False,
                    encoding='utf-8',
                    engine='python',
                    quotechar='"',
                    skipinitialspace=True,
                    on_bad_lines='skip',
                    sep=','
                )
        
        # Clean column names
        df.columns = df.columns.str.strip().str.lower()
        
        # Validate required columns
        if 'part_number' not in df.columns or 'description' not in df.columns:
            available_cols = ', '.join(df.columns.tolist())
            return None, f"Required columns missing. Expected: part_number, description. Found: {available_cols}"
        
        # Clean data
        original_count = len(df)
        
        # Clean and validate entries
        df['part_number'] = df['part_number'].astype(str).str.strip()
        df['description'] = df['description'].astype(str).str.strip()
        
        # Remove invalid entries
        valid_mask = (
            (df['part_number'].str.len() > 0) & 
            (df['description'].str.len() > 0) &
            (df['part_number'] != 'nan') &
            (df['description'] != 'nan')
        )
        
        df = df[valid_mask]
        
        # Remove duplicates
        df = df.drop_duplicates(subset=['part_number'], keep='first')
        df = df.reset_index(drop=True)
        
        cleaned_count = len(df)
        
        if df.empty:
            return None, "No valid parts data found after cleaning."
        
        # Create metadata
        metadata = {
            'loaded_at': datetime.now(),
            'original_count': original_count,
            'cleaned_count': cleaned_count,
            'removed_count': original_count - cleaned_count,
            'file_size_kb': round(os.path.getsize(PARTS_DATA_FILE) / 1024, 2)
        }
        
        return df, metadata
        
    except Exception as e:
        return None, f"Error loading data file: {str(e)}"

# ============================================================================
# OPTIMIZED SEARCH ENGINE
# ============================================================================
def optimized_search(query: str, df: pd.DataFrame) -> List[Tuple]:
    """High-performance search optimized for local data."""
    if not query.strip() or df.empty:
        return []
    
    query = query.lower().strip()
    results = []
    
    # Pre-compile regex for better performance
    word_pattern = re.compile(r'[-_\s\.]+')
    query_words = [word for word in word_pattern.split(query) if len(word) > 1]
    
    if not query_words:
        return []
    
    # Vectorized search for better performance
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
# UI HELPER FUNCTIONS
# ============================================================================
def show_message(message: str, message_type: str = "info"):
    """Show enhanced styled messages."""
    st.markdown(f'<div class="status-message {message_type}">{message}</div>', unsafe_allow_html=True)

def add_to_search_history(query: str):
    """Efficiently manage search history."""
    if query and query.strip():
        history = st.session_state.search_history
        if query in history:
            history.remove(query)
        history.insert(0, query)
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
        if len(word) > 2:
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
# MAIN APPLICATION - LIGHTNING FAST LOCAL VERSION!
# ============================================================================
def main():
    """Main application - now using local file for ultimate speed and reliability!"""
    
    # Initialize session state
    init_session_state()
    
    # Enhanced header
    st.markdown("""
    <div style='text-align: center; padding: 20px 0;'>
        <h1 style='font-size: 4em; background: linear-gradient(135deg, #1f77b4, #17a2b8); 
                   -webkit-background-clip: text; -webkit-text-fill-color: transparent; 
                   margin-bottom: 10px;'>Parts Finder</h1>
        <p style='color: #6c757d; font-size: 1.1em;'>⚡ Lightning fast local search - no network required!</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Load data from local file - SUPER FAST!
    df, error_or_metadata = load_parts_data()
    
    # Enhanced status display
    if isinstance(error_or_metadata, str):  # Error case
        show_message(f"⚠️ {error_or_metadata}", "error")
        st.markdown("### 🔧 How to fix:")
        st.markdown(f"1. Make sure `{PARTS_DATA_FILE}` is in the same directory as `app.py`")
        st.markdown("2. Check that the file has columns: `part_number` and `description`")
        st.markdown("3. Verify the CSV file is properly formatted")
        return
    else:  # Success case
        metadata = error_or_metadata
        load_time = metadata['loaded_at'].strftime("%H:%M:%S")
        file_size = metadata['file_size_kb']
        show_message(
            f"✅ Loaded {metadata['cleaned_count']:,} parts from local file ({file_size}KB) at {load_time}", 
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
    
    # Debounce search for better performance
    current_time = time.time()
    if current_time - st.session_state.last_search_time < SEARCH_DELAY:
        time.sleep(SEARCH_DELAY)
    st.session_state.last_search_time = current_time
    
    # Perform optimized search - BLAZING FAST with local data!
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
    
    # Performance info
    if st.checkbox("Show performance info", key="perf_info"):
        st.markdown("### ⚡ Performance Metrics")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Results Found", f"{total_results:,}")
        with col2:
            st.metric("Data Source", "Local File ⚡")
        with col3:
            st.metric("File Size", f"{metadata['file_size_kb']}KB")

# ============================================================================
# FOOTER
# ============================================================================
def show_footer():
    """Enhanced footer."""
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #6c757d; padding: 20px 0;'>
        <p><strong>Parts Finder v3.0</strong> - ⚡ Lightning Fast Local Version</p>
        <p>For support or feedback: 
        <a href='mailto:Syed.naqvi@bgis.com' style='color: #1f77b4; text-decoration: none;'>
        ✉️ Syed.naqvi@bgis.com</a></p>
    </div>
    """, unsafe_allow_html=True)

# ============================================================================
# RUN THE APP
# ============================================================================
if __name__ == "__main__":
    try:
        main()
        show_footer()
    except Exception as e:
        st.error(f"Application error: {str(e)}")
        st.info("Please refresh the page or contact support if the issue persists.")
