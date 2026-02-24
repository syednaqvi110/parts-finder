import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
import json

# ============================================================================
# CONFIGURATION
# ============================================================================
PARTS_DATA_FILE = "parts_data.csv"

# ============================================================================
# PAGE CONFIG
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
</style>
""", unsafe_allow_html=True)

# ============================================================================
# DATA LOADING (Python side — load once, pass to JS)
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

        parts_list = df[['part_number', 'description']].to_dict(orient='records')
        return parts_list, f"Loaded {len(parts_list)} parts"

    except Exception as e:
        return None, f"Error: {str(e)}"


# ============================================================================
# MAIN
# ============================================================================
st.markdown("<h1 style='text-align: center;'>Parts Finder</h1>", unsafe_allow_html=True)

parts_list, message = load_parts_data()

if parts_list is None:
    st.error(message)
    st.stop()

st.success(message)

# Embed all parts as JSON and run the entire search UI in JS.
# No Streamlit reruns involved — filtering happens 100% client-side on every keystroke.
parts_json = json.dumps(parts_list)

components.html(f"""
<!DOCTYPE html>
<html>
<head>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: sans-serif; padding: 12px; background: transparent; }}

  #search-input {{
    width: 100%;
    padding: 10px 14px;
    font-size: 16px;
    border: 1px solid #ccc;
    border-radius: 6px;
    outline: none;
    transition: border-color 0.2s;
  }}
  #search-input:focus {{ border-color: #0066cc; box-shadow: 0 0 0 2px rgba(0,102,204,0.15); }}

  #results-count {{
    margin: 10px 0 6px;
    font-size: 13px;
    color: #555;
  }}

  .result-card {{
    border: 1px solid #ddd;
    border-radius: 5px;
    padding: 10px 12px;
    margin-bottom: 7px;
    background: #f9f9f9;
  }}
  .part-number {{
    font-weight: bold;
    color: #0066cc;
    font-size: 14px;
    margin-bottom: 3px;
  }}
  .part-desc {{
    color: #333;
    font-size: 13px;
  }}
  .highlight {{ background: #ffff99; font-weight: bold; }}

  #pagination {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 10px;
    font-size: 13px;
    color: #555;
  }}
  #pagination button {{
    padding: 5px 12px;
    border: 1px solid #ccc;
    border-radius: 4px;
    background: white;
    cursor: pointer;
    font-size: 13px;
  }}
  #pagination button:disabled {{ opacity: 0.4; cursor: default; }}
  #pagination button:hover:not(:disabled) {{ background: #f0f0f0; }}

  #empty-msg {{ color: #888; font-size: 14px; margin-top: 12px; }}
</style>
</head>
<body>

<input id="search-input" type="text" placeholder="Type part number or description" autofocus />
<div id="results-count"></div>
<div id="results-list"></div>
<div id="pagination">
  <button id="btn-prev" onclick="changePage(-1)" disabled>← Prev</button>
  <span id="page-info"></span>
  <button id="btn-next" onclick="changePage(1)" disabled>Next →</button>
</div>
<div id="empty-msg" style="display:none">No results found. Try different keywords.</div>

<script>
  const PARTS = {parts_json};
  const PER_PAGE = 20;
  const MAX_RESULTS = 100;

  let currentResults = [];
  let currentPage = 1;
  let debounceTimer = null;

  function escapeHtml(str) {{
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }}

  function highlightText(text, query) {{
    if (!query) return escapeHtml(text);
    const escaped = escapeHtml(text);
    const words = query.toLowerCase().split(/\s+/).filter(w => w.length > 2);
    if (!words.length) return escaped;
    const pattern = new RegExp('(' + words.map(w =>
      w.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&')
    ).join('|') + ')', 'gi');
    return escaped.replace(pattern, '<span class="highlight">$1</span>');
  }}

  function scoreResult(part, query) {{
    const q = query.toLowerCase().trim();
    const pn = part.part_number.toLowerCase();
    const desc = part.description.toLowerCase();

    if (q === pn) return 100;
    if (pn.includes(q)) return 80;
    if (desc.includes(q)) return 60;

    let score = 0;
    const words = q.split(/\s+/).filter(w => w.length > 2);
    for (const word of words) {{
      if (pn.includes(word)) score += 40;
      else if (desc.includes(word)) score += 20;
    }}
    return score;
  }}

  function doSearch(query) {{
    const q = query.trim();
    if (!q) {{
      currentResults = [];
      currentPage = 1;
      renderResults(q);
      return;
    }}

    const scored = [];
    for (const part of PARTS) {{
      const s = scoreResult(part, q);
      if (s > 0) scored.push({{ part, score: s }});
    }}
    scored.sort((a, b) => b.score - a.score);
    currentResults = scored.slice(0, MAX_RESULTS).map(x => x.part);
    currentPage = 1;
    renderResults(q);
  }}

  function renderResults(query) {{
    const total = currentResults.length;
    const totalPages = Math.max(1, Math.ceil(total / PER_PAGE));
    currentPage = Math.min(currentPage, totalPages);

    const start = (currentPage - 1) * PER_PAGE;
    const end = Math.min(start + PER_PAGE, total);
    const pageItems = currentResults.slice(start, end);

    const countEl = document.getElementById('results-count');
    const listEl = document.getElementById('results-list');
    const emptyEl = document.getElementById('empty-msg');
    const prevBtn = document.getElementById('btn-prev');
    const nextBtn = document.getElementById('btn-next');
    const pageInfo = document.getElementById('page-info');
    const paginationEl = document.getElementById('pagination');

    if (!query) {{
      countEl.textContent = '';
      listEl.innerHTML = '';
      emptyEl.style.display = 'none';
      paginationEl.style.display = 'none';
      return;
    }}

    if (total === 0) {{
      countEl.textContent = '';
      listEl.innerHTML = '';
      emptyEl.style.display = 'block';
      paginationEl.style.display = 'none';
      return;
    }}

    emptyEl.style.display = 'none';
    countEl.textContent = `${{total}} result${{total !== 1 ? 's' : ''}} found`;

    listEl.innerHTML = pageItems.map(part => `
      <div class="result-card">
        <div class="part-number">${{highlightText(part.part_number, query)}}</div>
        <div class="part-desc">${{highlightText(part.description, query)}}</div>
      </div>
    `).join('');

    if (totalPages > 1) {{
      paginationEl.style.display = 'flex';
      pageInfo.textContent = `Page ${{currentPage}} of ${{totalPages}}`;
      prevBtn.disabled = currentPage <= 1;
      nextBtn.disabled = currentPage >= totalPages;
    }} else {{
      paginationEl.style.display = 'none';
    }}
  }}

  function changePage(delta) {{
    currentPage += delta;
    renderResults(document.getElementById('search-input').value);
    window.scrollTo(0, 0);
  }}

  document.getElementById('search-input').addEventListener('input', function() {{
    clearTimeout(debounceTimer);
    const val = this.value;
    debounceTimer = setTimeout(() => doSearch(val), 200);
  }});
</script>
</body>
</html>
""", height=700, scrolling=True)

# Contact footer (outside the component)
st.write("---")
st.markdown(
    "<p style='text-align: center;'>For support or feedback: "
    "<a href='mailto:Syed.naqvi@bgis.com'>Syed.naqvi@bgis.com</a></p>",
    unsafe_allow_html=True
)
