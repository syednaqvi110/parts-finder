import streamlit as st
import pandas as pd
from rapidfuzz import fuzz, process
import re
import time
from typing import List, Tuple, Dict, Any
from datetime import datetime
import hashlib
import os

# ============================================================================
# CONFIGURATION
# ============================================================================
PARTS_DATA_FILE = "parts_data.csv"
RESULTS_PER_PAGE = 20
MAX_RESULTS = 100

# ============================================================================
# STREAMLIT SETUP
# ============================================================================
st.set_page_config(
    page_title="Parts Finder",
    page_icon="🔍",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Simple CSS - no fancy styling
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}
    .stDecoration {display: none;}
    
    .highlight {
        background-color: #ffff99;
        font-weight: bold;
    }
    
    .search-result {
        border: 1px solid #ddd;
        padding: 10px;
        margin: 8px 0;
        background-color: #f9f9f9;
    }
    
    .part-number {
        font-weight: bold;
        color: #0066cc;
        margin-bottom: 5px;
    }
    
    .part-description {
        color: #333;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# SESSION STATE
# ============================================================================
def init_session_state():
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1

# ============================================================================
# DATA LOADING
# ============================================================================
@st.cache_data(show_spinner=False)
def load_parts_data():
    try:
        if not os.path.exists(PARTS_DATA_FILE):
            return None, f"File '{PARTS_DATA_FILE}' not found."
        
        # Handle your existing tab-separated CSV format
        df = pd.read_csv(PARTS_DATA_FILE, dtype=str, na_filter=False, sep='\t')
        
        # Clean up column names - handle your existing headers
        df.columns = df.columns.str.strip().str.replace(':', '')
        
        # Map your existing column names to standard names
        column_mapping = {
            'inventory item id': 'part_number',
            'inv item name': 'description'
        }
        
        # Rename columns to standard names
        for old_name, new_name in column_mapping.items():
            for col in df.columns:
                if old_name in col.lower():
                    df = df.rename(columns={col: new_name})
                    break
        
        # If we still don't have the right columns, try the first two columns
        if 'part_number' not in df.columns or 'description' not in df.columns:
            if len(df.columns) >= 2:
                df = df.rename(columns={df.columns[0]: 'part_number', df.columns[1]: 'description'})
            else:
                return None, "Could not identify part number and description columns."
        
        # Keep only the two columns we need
        df = df[['part_number', 'description']]
        
        # Clean data
        df['part_number'] = df['part_number'].astype(str).str.strip()
        df['description'] = df['description'].astype(str).str.strip()
        
        # Remove invalid entries (your existing format has some)
        df = df[df['part_number'] != '**NO INV PART']  # Remove your placeholder entry
        df = df[(df['part_number'].str.len() > 0) & (df['description'].str.len() > 0)]
        df = df[df['part_number'] != 'nan']
        df = df[df['description'] != 'nan']
        df = df[~df['part_number'].str.contains('NO INVENTORY', na=False)]
        df = df.drop_duplicates(subset=['part_number'], keep='first')
        df = df.reset_index(drop=True)
        
        return df, f"Loaded {len(df)} parts"
        
    except Exception as e:
        return None, f"Error: {str(e)}"

# ============================================================================
# SEARCH ENGINE
# ============================================================================
def search_parts(query: str, df: pd.DataFrame) -> List[Tuple]:
    if not query.strip() or df.empty:
        return []
    
    query = query.lower().strip()
    results = []
    
    # Search through all parts
    for idx, row in df.iterrows():
        part_num = row['part_number'].lower()
        desc = row['description'].lower()
        score = 0
        
        # Exact matches get highest score
        if query == part_num:
            score = 100
        elif query in part_num:
            score = 80
        elif query in desc:
            score = 60
        else:
            # Word matching
            query_words = query.split()
            for word in query_words:
                if len(word) > 2:
                    if word in part_num:
                        score += 40
                    elif word in desc:
                        score += 20
        
        if score > 0:
            results.append((idx, row['part_number'], row['description'], score))
    
    # Sort by score and limit results
    results.sort(key=lambda x: x[3], reverse=True)
    return results[:MAX_RESULTS]

# ============================================================================
# DISPLAY FUNCTIONS
# ============================================================================
def highlight_text(text: str, query: str) -> str:
    if not query.strip():
        return text
    
    import html
    escaped_text = html.escape(text)
    query_words = [word for word in query.lower().split() if len(word) > 1]
    
    for word in query_words:
        if len(word) > 2:
            pattern = re.compile(f'({re.escape(word)})', re.IGNORECASE)
            escaped_text = pattern.sub(r'<span class="highlight">\1</span>', escaped_text)
    
    return escaped_text

def show_search_result(part_number: str, description: str, query: str):
    highlighted_part = highlight_text(part_number, query)
    highlighted_desc = highlight_text(description, query)
    
    st.markdown(f"""
    <div class="search-result">
        <div class="part-number">{highlighted_part}</div>
        <div class="part-description">{highlighted_desc}</div>
    </div>
    """, unsafe_allow_html=True)

def show_pagination(current_page: int, total_pages: int, total_results: int):
    if total_pages <= 1:
        return current_page
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if current_page > 1 and st.button("← Previous"):
            return current_page - 1
    
    with col2:
        st.write(f"Page {current_page} of {total_pages} ({total_results} results)")
    
    with col3:
        if current_page < total_pages and st.button("Next →"):
            return current_page + 1
    
    return current_page

# ============================================================================
# MAIN APPLICATION
# ============================================================================
def main():
    init_session_state()
    
    # Centered header
    st.markdown("<h1 style='text-align: center;'>Parts Finder</h1>", unsafe_allow_html=True)
    
    # Load data
    df, message = load_parts_data()
    
    if df is None:
        st.error(message)
        return
    else:
        st.success(message)
    
    # Search input
    search_query = st.text_input("Search parts:", placeholder="Enter part number or description...")
    
    if not search_query.strip():
        return
    
    # Search
    results = search_parts(search_query, df)
    
    if not results:
        st.info("No results found.")
        return
    
    # Pagination
    total_results = len(results)
    total_pages = (total_results + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE
    current_page = min(st.session_state.current_page, total_pages)
    
    # Show pagination (top)
    new_page = show_pagination(current_page, total_pages, total_results)
    if new_page != current_page:
        st.session_state.current_page = new_page
        st.rerun()
    
    # Show results for current page
    start_idx = (current_page - 1) * RESULTS_PER_PAGE
    end_idx = min(start_idx + RESULTS_PER_PAGE, total_results)
    page_results = results[start_idx:end_idx]
    
    for _, part_number, description, score in page_results:
        show_search_result(part_number, description, search_query)
    
    # Show pagination (bottom)
    if total_pages > 1:
        st.write("")  # Spacing
        new_page = show_pagination(current_page, total_pages, total_results)
        if new_page != current_page:
            st.session_state.current_page = new_page
            st.rerun()

# ============================================================================
# CONTACT INFO
# ============================================================================
def show_contact():
    st.write("")
    st.write("---")
    st.markdown("<p style='text-align: center;'>For support or feedback: Syed.naqvi@bgis.com</p>", unsafe_allow_html=True)

# ============================================================================
# RUN APP
# ============================================================================
if __name__ == "__main__":
    main()
    show_contact()
