import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
import json
import re

PARTS_DATA_FILE = "parts_data.csv"
PER_PAGE = 15
MAX_RESULTS = 100

# Height per card in px (sized for mobile — fine on desktop too)
CARD_HEIGHT_PX = 88
TOPBAR_PX      = 36   # result count line
PAGINATION_PX  = 60   # prev/next bar height
EMPTY_MSG_PX   = 50
BUFFER_PX      = 20

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
</style>
""", unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def load_parts_data():
    try:
        if not os.path.exists(PARTS_DATA_FILE):
            return None, f"File '{PARTS_DATA_FILE}' not found."
        df = pd.read_csv(PARTS_DATA_FILE, dtype=str, na_filter=False, sep='\t')
        df.columns = df.columns.str.strip().str.replace(':', '')
        for old_name, new_name in [('inventory item id', 'part_number'), ('inv item name', 'description')]:
            for col in df.columns:
                if old_name in col.lower():
                    df = df.rename(columns={col: new_name})
                    break
        if 'part_number' not in df.columns or 'description' not in df.columns:
            if len(df.columns) >= 2:
                df = df.rename(columns={df.columns[0]: 'part_number', df.columns[1]: 'description'})
            else:
                return None, "Could not identify columns."
        df = df[['part_number', 'description']]
        df['part_number'] = df['part_number'].astype(str).str.strip()
        df['description'] = df['description'].astype(str).str.strip()
        df = df[df['part_number'] != '**NO INV PART']
        df = df[(df['part_number'].str.len() > 0) & (df['description'].str.len() > 0)]
        df = df[df['part_number'] != 'nan']
        df = df[df['description'] != 'nan']
        df = df[~df['part_number'].str.contains('NO INVENTORY', na=False)]
        df = df.drop_duplicates(subset=['part_number'], keep='first').reset_index(drop=True)
        return df[['part_number', 'description']].to_dict(orient='records'), f"Loaded {len(df)} parts"
    except Exception as e:
        return None, f"Error: {str(e)}"

def score_result(part, query):
    q    = query.lower().strip()
    pn   = part['part_number'].lower()
    desc = part['description'].lower()
    pn_norm = pn.replace('-', ' ')
    q_norm  = q.replace('-', ' ')

    if q == pn:                    return 1000
    if pn.startswith(q):           return 950
    if q in pn:                    return 900
    if pn_norm.startswith(q_norm): return 880
    if q_norm in pn_norm:          return 850
    if q in desc:                  return 700

    words = q_norm.split()
    if not words: return 0

    pn_matches   = sum(1 for w in words if w in pn or w in pn_norm)
    desc_matches = sum(1 for w in words if w not in pn and w not in pn_norm and w in desc)
    total_matched = pn_matches + desc_matches
    if total_matched == 0: return 0

    score = (pn_matches / len(words)) * 600 + (desc_matches / len(words)) * 400
    if total_matched == len(words): score += 200
    if pn_matches > desc_matches:   score += 50
    return round(score)

def search_parts(parts_list, query):
    scored = [(p, score_result(p, query)) for p in parts_list]
    scored = [(p, s) for p, s in scored if s > 0]
    scored.sort(key=lambda x: -x[1])
    return [p for p, _ in scored[:MAX_RESULTS]]

def calc_iframe_height(n_on_page, total, total_pages):
    if n_on_page == 0:
        return EMPTY_MSG_PX + BUFFER_PX
    h = n_on_page * CARD_HEIGHT_PX + BUFFER_PX
    return h

# ── UI ────────────────────────────────────────────────────────────────────────

st.markdown("<h1 style='text-align: center;'>Parts Finder</h1>", unsafe_allow_html=True)

parts_list, message = load_parts_data()
if parts_list is None:
    st.error(message)
    st.stop()
st.success(message)

query = st.text_input(
    label="Search",
    placeholder="Type part number or description...",
    label_visibility="collapsed"
)

if query.strip():
    # Reset page when query changes
    if st.session_state.get('last_query') != query:
        st.session_state.page = 1
        st.session_state.last_query = query

    all_results = search_parts(parts_list, query)
    total = len(all_results)
    total_pages = max(1, -(-total // PER_PAGE))
    current_page = st.session_state.get('page', 1)
    current_page = max(1, min(current_page, total_pages))

    # Result count
    if total > 0:
        st.markdown(
            f"<p style='color:#555; font-size:13px; margin-bottom:4px;'>"
            f"{total} result{'s' if total != 1 else ''} found</p>",
            unsafe_allow_html=True
        )
    
    # Slice for current page
    start = (current_page - 1) * PER_PAGE
    page_items = all_results[start:start + PER_PAGE]
    n_on_page = len(page_items)

    # Build results HTML
    def escape_html(s):
        return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

    if page_items:
        cards = '\n'.join(
            f'<div class="result-card">'
            f'<div class="part-number">{escape_html(p["part_number"])}</div>'
            f'<div class="part-desc">{escape_html(p["description"])}</div>'
            f'</div>'
            for p in page_items
        )
    else:
        cards = '<div id="empty-msg">No results found. Try different keywords.</div>'

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    padding: 4px 2px;
    background: transparent;
  }}
  html::-webkit-scrollbar {{ display: none; }}
  html {{ -ms-overflow-style: none; scrollbar-width: none; }}

  .result-card {{
    border: 1px solid #ddd;
    border-radius: 5px;
    padding: 10px 12px;
    margin-bottom: 7px;
    background: #f9f9f9;
  }}
  .part-number {{ font-weight: bold; color: #0066cc; font-size: 14px; margin-bottom: 3px; }}
  .part-desc   {{ color: #333; font-size: 13px; }}
  #empty-msg   {{ color: #888; font-size: 14px; margin-top: 8px; }}

  @media (max-width: 600px) {{
    .result-card {{
      border-radius: 10px;
      padding: 14px 16px;
      margin-bottom: 10px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.06);
      -webkit-tap-highlight-color: rgba(0,102,204,0.08);
    }}
    .part-number {{ font-size: 15px; margin-bottom: 5px; }}
    .part-desc   {{ font-size: 14px; line-height: 1.4; }}
    #empty-msg   {{ font-size: 15px; margin-top: 12px; text-align: center; }}
  }}
</style>
</head>
<body>
{cards}
</body>
</html>"""

    iframe_h = calc_iframe_height(n_on_page, total, total_pages)
    components.html(html, height=iframe_h, scrolling=False)

    # Pagination below results
    if total_pages > 1:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("← Prev", disabled=(current_page <= 1), key="prev"):
                st.session_state.page = current_page - 1
                st.rerun()
        with col2:
            st.markdown(
                f"<p style='text-align:center; margin-top:6px; color:#555; font-size:13px;'>"
                f"Page {current_page} of {total_pages}</p>",
                unsafe_allow_html=True
            )
        with col3:
            if st.button("Next →", disabled=(current_page >= total_pages), key="next"):
                st.session_state.page = current_page + 1
                st.rerun()

st.write("---")
st.markdown(
    "<p style='text-align: center;'>For support or feedback: "
    "<a href='mailto:Syed.naqvi@bgis.com'>Syed.naqvi@bgis.com</a></p>",
    unsafe_allow_html=True
)
