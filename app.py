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

# ✅ Your actual Google Sheets CSV URL is embedded and ready to use!
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
    Perform optimized intelligent search on parts database.
    Returns list of tuples: (index, part_number, description, score)
    """
    if not query.strip() or df.empty:
        return []
    
    query = query.lower().strip()
    results = []
    
    # Create searchable text for each part
    df['searchable'] = df.apply(create_searchable_text, axis=1)
    
    # Method 1: EXACT MATCHES get highest priority (100 points)
    for idx, row in df.iterrows():
        part_num = row['part_number'].lower()
        desc_lower = row['description'].lower()
        
        # Exact part number match
        if query == part_num:
            results.append((idx, row['part_number'], row['description'], 100))
        # Part number starts with query
        elif part_num.startswith(query):
            results.append((idx, row['part_number'], row['description'], 95))
        # Query is contained in part number as whole segment
        elif query in part_num:
            # Check if it's a whole segment (not breaking up words)
            if query in part_num.split('-') or query in part_num.split('_'):
                results.append((idx, row['part_number'], row['description'], 90))
            else:
                results.append((idx, row['part_number'], row['description'], 85))
    
    # Method 2: WORD-BOUNDARY MATCHES (80-85 points)
    query_words = query.split()
    for idx, row in df.iterrows():
        if any(r[0] == idx for r in results):  # Skip if already found
            continue
            
        part_words = re.split(r'[-_\s]+', row['part_number'].lower())
        desc_words = row['description'].lower().split()
        
        # Check for exact word matches
        exact_word_matches = 0
        partial_word_matches = 0
        
        for query_word in query_words:
            # Exact word match in part number
            if query_word in part_words:
                exact_word_matches += 2
            # Exact word match in description
            elif query_word in desc_words:
                exact_word_matches += 1
            # Partial match (but be more strict)
            elif any(word.startswith(query_word) or query_word in word for word in part_words + desc_words):
                partial_word_matches += 1
        
        if exact_word_matches > 0:
            score = min(85, 70 + (exact_word_matches * 5))
            results.append((idx, row['part_number'], row['description'], score))
        elif partial_word_matches >= len(query_words):  # All query words found partially
            score = min(75, 60 + (partial_word_matches * 3))
            results.append((idx, row['part_number'], row['description'], score))
    
    # Method 3: FUZZY MATCHING for typos and similar words (40-70 points)
    remaining_indices = set(range(len(df))) - {r[0] for r in results}
    if remaining_indices and len(query) > 2:
        remaining_texts = [df.iloc[i]['searchable'] for i in remaining_indices]
        fuzzy_results = process.extract(
            query, 
            remaining_texts, 
            scorer=fuzz.WRatio,
            limit=min(max_results, len(remaining_texts))
        )
        
        for match_text, score, rel_index in fuzzy_results:
            if score >= 45:  # Higher threshold for fuzzy matching
                actual_index = list(remaining_indices)[rel_index]
                # Scale fuzzy scores to 40-70 range
                adjusted_score = min(70, 40 + (score - 45) * 30 / 55)
                results.append((
                    actual_index,
                    df.iloc[actual_index]['part_number'],
                    df.iloc[actual_index]['description'],
                    int(adjusted_score)
                ))
    
    # Method 4: BOOST for multiple query word matches
    if len(query_words) > 1:
        for i, (idx, part_num, desc, score) in enumerate(results):
            found_words = 0
            search_text = f"{part_num} {desc}".lower()
            
            for word in query_words:
                if word in search_text:
                    found_words += 1
            
            # Boost score based on how many query words were found
            if found_words > 1:
                boost = (found_words - 1) * 5
                results[i] = (idx, part_num, desc, min(100, score + boost))
    
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
            <p>• Use exact part numbers: "SPM-001" (not "SP M")</p>
            <p>• Use complete words: "brake" not "brk"</p>
            <p>• Try different abbreviations: "hyd" for hydraulic</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Results summary
    st.markdown(f"""
    <div class="stats-row">
        <strong>✅ Found {len(results)} matching parts</strong>
    </div>
    """, unsafe_allow_html=True)
    
    # JavaScript for clipboard functionality
    st.markdown("""
    <script>
    function copyToClipboard(text, buttonId) {
        // Try using the modern clipboard API
        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(text).then(function() {
                showCopySuccess(buttonId, text);
            }).catch(function() {
                fallbackCopyTextToClipboard(text, buttonId);
            });
        } else {
            // Fallback for older browsers or non-HTTPS
            fallbackCopyTextToClipboard(text, buttonId);
        }
    }
    
    function fallbackCopyTextToClipboard(text, buttonId) {
        var textArea = document.createElement("textarea");
        textArea.value = text;
        textArea.style.top = "0";
        textArea.style.left = "0";
        textArea.style.position = "fixed";
        textArea.style.opacity = "0";
        
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        
        try {
            var successful = document.execCommand('copy');
            if (successful) {
                showCopySuccess(buttonId, text);
            } else {
                showCopyError(buttonId);
            }
        } catch (err) {
            showCopyError(buttonId);
        }
        
        document.body.removeChild(textArea);
    }
    
    function showCopySuccess(buttonId, text) {
        var button = document.getElementById(buttonId);
        if (button) {
            var originalText = button.innerHTML;
            button.innerHTML = '✅ Copied!';
            button.style.background = '#28a745';
            
            // Show copied text in the app
            var event = new CustomEvent('streamlit:setComponentValue', {
                detail: { value: 'Copied: ' + text }
            });
            window.parent.document.dispatchEvent(event);
            
            setTimeout(function() {
                button.innerHTML = originalText;
                button.style.background = '#1e3c72';
            }, 2000);
        }
    }
    
    function showCopyError(buttonId) {
        var button = document.getElementById(buttonId);
        if (button) {
            var originalText = button.innerHTML;
            button.innerHTML = '❌ Failed';
            button.style.background = '#dc3545';
            
            setTimeout(function() {
                button.innerHTML = originalText;
                button.style.background = '#1e3c72';
            }, 2000);
        }
    }
    </script>
    """, unsafe_allow_html=True)
    
    # Display each result
    for idx, (_, part_num, description, score) in enumerate(results):
        score_class = "score-excellent" if score >= 80 else "score-good" if score >= 60 else "score-fair"
        score_text = "Excellent Match" if score >= 80 else "Good Match" if score >= 60 else "Partial Match"
        
        # Create result card with working copy button
        highlighted_part = highlight_matches(part_num, query)
        highlighted_desc = highlight_matches(description, query)
        
        button_id = f"copy_btn_{idx}"
        
        st.markdown(f"""
        <div class="result-item">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div style="flex: 1;">
                    <div class="part-number">{highlighted_part}</div>
                    <div class="description">{highlighted_desc}</div>
                    <div class="result-footer">
                        <span class="match-score {score_class}">{score_text} ({score}%)</span>
                    </div>
                </div>
                <div style="margin-left: 15px;">
                    <button 
                        id="{button_id}"
                        onclick="copyToClipboard('{part_num}', '{button_id}')"
                        class="copy-btn"
                        style="background: #1e3c72; color: white; border: none; border-radius: 8px; padding: 8px 16px; cursor: pointer; font-size: 14px;"
                    >
                        📋 Copy
                    </button>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Add spacing between results
        if idx < len(results) - 1:
            st.markdown("<br>", unsafe_allow_html=True)

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
