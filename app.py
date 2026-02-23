import streamlit as st
import pandas as pd
import re
import os
from typing import List, Tuple

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

    /* Hide the trigger button that sits right after the search input */
    div[data-testid="stTextInput"] + div[data-testid="stButton"] > button {
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0,0,0,0);
        border: 0;
    }
    div[data-testid="stTextInput"] + div[data-testid="stButton"] {
        height: 0;
        overflow: hidden;
        margin: 0;
        padding: 0;
    }
</style>

<script>
(function() {
    var debounceTimer = null;

    function clickHiddenButton() {
        // Find the button container that immediately follows the text input container
        var textInput = document.querySelector('div[data-testid="stTextInput"]');
        if (!textInput) return;
        var sibling = textInput.nextElementSibling;
        while (sibling) {
            var btn = sibling.querySelector('button');
            if (btn) { btn.click(); return; }
            sibling = sibling.nextElementSibling;
        }
    }

    function attachDebounce() {
        var inputs = document.querySelectorAll('input[type="text"]');
        inputs.forEach(function(input) {
            if (input._searchAttached) return;
            input._searchAttached = true;
            input.addEventListener('input', function() {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(clickHiddenButton, 300);
            });
        });
    }

    var observer = new MutationObserver(attachDebounce);
    observer.observe(document.body, { childList: true, subtree: true });
    setTimeout(attachDebounce, 300);
})();
</script>
""", unsafe_allow_html=True)

# ============================================================================
# SESSION STATE
# ============================================================================
def init_session_state():
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1
    if 'last_search_query' not in st.session_state:
        st.session_state.last_search_query = ""

# ============================================================================
# DATA LOADING
# ============================================================================
@st.cache_data(show_spinner=False)
def load_parts_data():
    try:
        if not os.path.exists(PARTS_DATA_FILE):
            return None, f"File '{PARTS_DATA_FILE}' not found."

        df = pd.read_csv(PARTS_DATA_FILE, dtype=str, na_filter=False, sep='\t')
        df.columns = df.columns.str.strip().str.replace(':', '')

        column_mapping = {
            'inventory item id': 'part_number',
            'inv item name': 'description'
        }

        for old_name, new_name in column_mapping.items():
            for col in df.columns:
                if old_name in col.lower():
                    df = df.rename(columns={col: new_name})
                    break

        if 'part_number' not in df.columns or 'description' not in df.columns:
            if len(df.columns) >= 2:
                df = df.rename(columns={df.columns[0]: 'part_number', df.columns[1]: 'description'})
            else:
                return None, "Could not identify part number and description columns."

        df = df[['part_number', 'description']]
        df['part_number'] = df['part_number'].astype(str).str.strip()
        df['description'] = df['description'].astype(str).str.strip()

        df = df[df['part_number'] != '**NO INV PART']
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
# SEARCHBOX FUNCTION (called on every keystroke)
# ============================================================================
def search_parts(query: str, df: pd.DataFrame) -> List[Tuple]:
    if not query or not query.strip() or df is None or df.empty:
        return []

    query_lower = query.lower().strip()
    results = []

    for idx, row in df.iterrows():
        part_num = row['part_number'].lower()
        desc = row['description'].lower()
        score = 0

        if query_lower == part_num:
            score = 100
        elif query_lower in part_num:
            score = 80
        elif query_lower in desc:
            score = 60
        else:
            for word in query_lower.split():
                if len(word) > 2:
                    if word in part_num:
                        score += 40
                    elif word in desc:
                        score += 20

        if score > 0:
            results.append((idx, row['part_number'], row['description'], score))

    results.sort(key=lambda x: x[3], reverse=True)
    return results[:MAX_RESULTS]



# ============================================================================
# DISPLAY FUNCTIONS
# ============================================================================
def highlight_text(text: str, query: str) -> str:
    if not query or not query.strip():
        return text
    import html
    escaped_text = html.escape(text)
    for word in query.lower().split():
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

def show_pagination(current_page: int, total_pages: int, total_results: int, key_prefix: str = ""):
    if total_pages <= 1:
        return current_page
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if current_page > 1 and st.button("← Previous", key=f"{key_prefix}_prev"):
            return current_page - 1
    with col2:
        st.write(f"Page {current_page} of {total_pages} ({total_results} results)")
    with col3:
        if current_page < total_pages and st.button("Next →", key=f"{key_prefix}_next"):
            return current_page + 1
    return current_page

# ============================================================================
# MAIN APPLICATION
# ============================================================================
def main():
    init_session_state()

    st.markdown("<h1 style='text-align: center;'>Parts Finder</h1>", unsafe_allow_html=True)

    df, message = load_parts_data()
    if df is None:
        st.error(message)
        return
    else:
        st.success(message)

    # Native text_input — no iframe, no focus loss, works with any amount of backspace
    st.text_input(
        "Search parts:",
        placeholder="Type part number or description...",
        key="search_input",
    )

    # Hidden button — JS clicks this after 300ms debounce to trigger a rerun
    # The rerun then reads the current search_input value from session state
    st.button("\u200b", key="search_trigger")  # zero-width space label

    # Read value directly — always current after any rerun
    search_query = st.session_state.get("search_input", "").strip()

    if search_query != st.session_state.last_search_query:
        st.session_state.current_page = 1
        st.session_state.last_search_query = search_query

    if not search_query:
        pass  # Box is empty — stay here, keep focus, show nothing
    else:
        # Full results list
        results = search_parts(search_query, df)

        if not results:
            st.info("No results found. Try different keywords.")
        else:
            total_results = len(results)
            total_pages = (total_results + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE
            current_page = min(st.session_state.current_page, total_pages)

            new_page = show_pagination(current_page, total_pages, total_results, "top")
            if new_page != current_page:
                st.session_state.current_page = new_page
                st.rerun()

            start_idx = (current_page - 1) * RESULTS_PER_PAGE
            end_idx = min(start_idx + RESULTS_PER_PAGE, total_results)

            for _, part_number, description, _ in results[start_idx:end_idx]:
                show_search_result(part_number, description, search_query)

            if total_pages > 1:
                st.write("")
                new_page = show_pagination(current_page, total_pages, total_results, "bottom")
                if new_page != current_page:
                    st.session_state.current_page = new_page
                    st.rerun()

# ============================================================================
# CONTACT INFO
# ============================================================================
def show_contact():
    st.write("")
    st.write("---")
    st.markdown(
        "<p style='text-align: center;'>For support or feedback: "
        "<a href='mailto:Syed.naqvi@bgis.com'>Syed.naqvi@bgis.com</a></p>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
    show_contact()
