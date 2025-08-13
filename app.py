import streamlit as st
import pandas as pd
import requests
from rapidfuzz import fuzz, process
import re
from typing import List, Tuple

# ============================================================================
# PARTS DATABASE CONFIGURATION - READY TO DEPLOY
# ============================================================================
PARTS_DATABASE_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSc2GTX3jc2NjJlR_zWVqDyTGf6bhCVc4GGaN_WMQDDlXZ8ofJVh5cbCPAD0d0lHY0anWXreyMdon33/pub?output=csv"

# Configure Streamlit page
st.set_page_config(
    page_title="Parts Finder",
    page_icon="🔧",
    layout="centered"
)

# Hide all Streamlit UI elements
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display:none;}
    .stDecoration {display:none;}
    
    .highlight {
        background-color: #fff3cd;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load_parts_database() -> pd.DataFrame:
    """Load parts data from Google Sheets."""
    try:
        response = requests.get(PARTS_DATABASE_URL, timeout=15)
        response.raise_for_status()
        
        from io import StringIO
        csv_content = StringIO(response.text)
        
        try:
            df = pd.read_csv(csv_content, quotechar='"', skipinitialspace=True)
        except:
            csv_content = StringIO(response.text)
            df = pd.read_csv(csv_content, quotechar='"', skipinitialspace=True, 
                           on_bad_lines='skip', engine='python')
        
        required_columns = ['part_number', 'description']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return pd.DataFrame()
        
        df['part_number'] = df['part_number'].astype(str).str.strip()
        df['description'] = df['description'].astype(str).str.strip()
        df = df.dropna(subset=['part_number', 'description'])
        df = df[df['part_number'].str.len() > 0]
        df = df[df['description'].str.len() > 0]
        
        return df.reset_index(drop=True)
        
    except:
        return pd.DataFrame()

def smart_search(query: str, df: pd.DataFrame, max_results: int = 50) -> List[Tuple]:
    """Search parts database."""
    if not query.strip() or df.empty:
        return []
    
    query = query.lower().strip()
    results = []
    
    # Exact matches first
    for idx, row in df.iterrows():
        part_num = row['part_number'].lower()
        desc_lower = row['description'].lower()
        
        if query == part_num:
            results.append((idx, row['part_number'], row['description'], 100))
        elif part_num.startswith(query):
            results.append((idx, row['part_number'], row['description'], 95))
        elif query in part_num:
            results.append((idx, row['part_number'], row['description'], 90))
    
    # Word matches
    query_words = query.split()
    for idx, row in df.iterrows():
        if any(r[0] == idx for r in results):
            continue
            
        part_words = re.split(r'[-_\s]+', row['part_number'].lower())
        desc_words = row['description'].lower().split()
        
        exact_matches = 0
        for query_word in query_words:
            if query_word in part_words:
                exact_matches += 2
            elif query_word in desc_words:
                exact_matches += 1
        
        if exact_matches > 0:
            score = min(85, 70 + (exact_matches * 5))
            results.append((idx, row['part_number'], row['description'], score))
    
    # Fuzzy matches
    remaining_indices = set(range(len(df))) - {r[0] for r in results}
    if remaining_indices and len(query) > 2:
        df['searchable'] = df['part_number'] + ' ' + df['description']
        remaining_texts = [df.iloc[i]['searchable'].lower() for i in remaining_indices]
        fuzzy_results = process.extract(query, remaining_texts, scorer=fuzz.WRatio, limit=20)
        
        for match_text, score, rel_index in fuzzy_results:
            if score >= 45:
                actual_index = list(remaining_indices)[rel_index]
                adjusted_score = min(70, 40 + (score - 45) * 30 / 55)
                results.append((actual_index, df.iloc[actual_index]['part_number'], 
                              df.iloc[actual_index]['description'], int(adjusted_score)))
    
    # Sort and return
    results.sort(key=lambda x: x[3], reverse=True)
    return results[:max_results]

def highlight_matches(text: str, query: str) -> str:
    """Highlight matching terms."""
    if not query.strip():
        return text
    
    query_words = [word for word in query.lower().split() if len(word) > 2]
    highlighted = text
    
    for word in query_words:
        pattern = re.compile(f'({re.escape(word)})', re.IGNORECASE)
        highlighted = pattern.sub(r'<span class="highlight">\1</span>', highlighted)
    
    return highlighted

def main():
    """Google-style minimal interface."""
    
    # Load data silently
    df = load_parts_database()
    
    # Center everything
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    
    # Title (Google style)
    st.markdown("<h1 style='text-align: center; font-size: 4em; margin-bottom: 30px;'>🔧 Parts Finder</h1>", unsafe_allow_html=True)
    
    # Search box (Google style)
    search_query = st.text_input(
        label="Search",
        placeholder="Search parts...",
        label_visibility="collapsed"
    )
    
    # Mobile keyboard handling
    st.markdown("""
    <script>
    setTimeout(function() {
        const inputs = window.parent.document.querySelectorAll('input[type="text"]');
        inputs.forEach(function(input) {
            input.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    this.blur();
                }
            });
        });
    }, 1000);
    </script>
    """, unsafe_allow_html=True)
    
    # Show results if searching
    if search_query and not df.empty:
        results = smart_search(search_query, df, max_results=50)
        
        if results:
            st.markdown("<br>", unsafe_allow_html=True)
            for _, part_num, description, _ in results:
                highlighted_part = highlight_matches(part_num, search_query)
                highlighted_desc = highlight_matches(description, search_query)
                
                st.markdown(f"**{highlighted_part}**", unsafe_allow_html=True)
                st.markdown(highlighted_desc, unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
