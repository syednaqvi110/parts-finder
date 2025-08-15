import streamlit as st
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

class UIComponents:
    """UI helper components for the Parts Finder app."""
    
    @staticmethod
    def render_custom_css():
        """Render custom CSS for the application."""
        st.markdown("""
        <style>
            /* Hide Streamlit UI elements */
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .stDeployButton {display:none;}
            .stDecoration {display:none;}
            
            /* Search highlighting */
            .highlight {
                background-color: #fff3cd;
                font-weight: bold;
                padding: 1px 2px;
                border-radius: 2px;
            }
            
            /* Loading spinner */
            .loading-spinner {
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }
            
            .spinner {
                border: 3px solid #f3f3f3;
                border-top: 3px solid #1f77b4;
                border-radius: 50%;
                width: 30px;
                height: 30px;
                animation: spin 1s linear infinite;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            /* Search suggestions */
            .search-suggestions {
                background: white;
                border: 1px solid #ddd;
                border-radius: 4px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                margin-top: 5px;
                max-height: 200px;
                overflow-y: auto;
            }
            
            .suggestion-item {
                padding: 8px 12px;
                cursor: pointer;
                border-bottom: 1px solid #eee;
            }
            
            .suggestion-item:hover {
                background-color: #f5f5f5;
            }
            
            .suggestion-item:last-child {
                border-bottom: none;
            }
            
            /* Error messages */
            .error-message {
                background-color: #f8d7da;
                color: #721c24;
                padding: 12px;
                border-radius: 4px;
                border: 1px solid #f5c6cb;
                margin: 10px 0;
            }
            
            .warning-message {
                background-color: #fff3cd;
                color: #856404;
                padding: 12px;
                border-radius: 4px;
                border: 1px solid #ffeaa7;
                margin: 10px 0;
            }
            
            .info-message {
                background-color: #d1ecf1;
                color: #0c5460;
                padding: 12px;
                border-radius: 4px;
                border: 1px solid #bee5eb;
                margin: 10px 0;
            }
            
            .success-message {
                background-color: #d4edda;
                color: #155724;
                padding: 12px;
                border-radius: 4px;
                border: 1px solid #c3e6cb;
                margin: 10px 0;
            }
            
            /* Search results */
            .search-result {
                border-left: 3px solid #1f77b4;
                padding: 10px 15px;
                margin: 10px 0;
                background-color: #f8f9fa;
                border-radius: 0 4px 4px 0;
            }
            
            .part-number {
                font-size: 1.1em;
                font-weight: bold;
                color: #1f77b4;
                margin-bottom: 5px;
            }
            
            .part-description {
                color: #333;
                line-height: 1.4;
            }
            
            /* Recent searches */
            .recent-searches {
                background-color: #f8f9fa;
                border-radius: 4px;
                padding: 10px;
                margin: 10px 0;
            }
            
            .recent-search-item {
                display: inline-block;
                background-color: #e9ecef;
                color: #495057;
                padding: 4px 8px;
                margin: 2px;
                border-radius: 12px;
                font-size: 0.85em;
                cursor: pointer;
                border: 1px solid #dee2e6;
            }
            
            .recent-search-item:hover {
                background-color: #dee2e6;
            }
            
            /* Pagination */
            .pagination {
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 10px;
                margin: 20px 0;
            }
            
            .pagination-button {
                padding: 8px 12px;
                border: 1px solid #dee2e6;
                background-color: white;
                color: #495057;
                border-radius: 4px;
                cursor: pointer;
                text-decoration: none;
            }
            
            .pagination-button:hover {
                background-color: #e9ecef;
            }
            
            .pagination-button.active {
                background-color: #1f77b4;
                color: white;
                border-color: #1f77b4;
            }
            
            .pagination-button.disabled {
                background-color: #f8f9fa;
                color: #6c757d;
                cursor: not-allowed;
                border-color: #dee2e6;
            }
            
            /* Statistics */
            .stats-container {
                display: flex;
                gap: 20px;
                margin: 20px 0;
                flex-wrap: wrap;
            }
            
            .stat-item {
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 4px;
                text-align: center;
                min-width: 100px;
                border: 1px solid #dee2e6;
            }
            
            .stat-value {
                font-size: 1.5em;
                font-weight: bold;
                color: #1f77b4;
            }
            
            .stat-label {
                font-size: 0.85em;
                color: #6c757d;
                margin-top: 5px;
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
            }
        </style>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def show_loading_spinner(message: str = "Searching..."):
        """Display a loading spinner with message."""
        st.markdown(f"""
        <div class="loading-spinner">
            <div class="spinner"></div>
            <span style="margin-left: 10px;">{message}</span>
        </div>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def show_error_message(message: str, error_type: str = "error"):
        """Display an error message with appropriate styling."""
        css_class = f"{error_type}-message"
        st.markdown(f'<div class="{css_class}">{message}</div>', unsafe_allow_html=True)
    
    @staticmethod
    def show_no_results_message(query: str, suggestions: List[str] = None):
        """Display a helpful no results message."""
        st.markdown(f"""
        <div class="info-message">
            <strong>No results found for "{query}"</strong><br>
            Try:
            <ul style="margin: 10px 0; padding-left: 20px;">
                <li>Checking your spelling</li>
                <li>Using different keywords</li>
                <li>Using fewer words</li>
                <li>Using part of the part number</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        if suggestions:
            st.markdown("**Did you mean:**")
            for suggestion in suggestions[:3]:
                if st.button(f"🔍 {suggestion}", key=f"suggestion_{suggestion}"):
                    st.session_state.search_query = suggestion
                    st.rerun()
    
    @staticmethod
    def render_search_result(part_number: str, description: str, query: str, search_engine):
        """Render a single search result with highlighting."""
        highlighted_part = search_engine.highlight_matches(part_number, query)
        highlighted_desc = search_engine.highlight_matches(description, query)
        
        st.markdown(f"""
        <div class="search-result">
            <div class="part-number">{highlighted_part}</div>
            <div class="part-description">{highlighted_desc}</div>
        </div>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def render_recent_searches(recent_searches: List[str]):
        """Render recent searches as clickable pills."""
        if not recent_searches:
            return
        
        st.markdown("**Recent searches:**")
        
        # Create columns for recent searches
        cols = st.columns(min(len(recent_searches), 5))
        for i, search in enumerate(recent_searches):
            col_idx = i % len(cols)
            with cols[col_idx]:
                if st.button(f"🕐 {search}", key=f"recent_{i}_{search}", help="Click to search again"):
                    st.session_state.search_query = search
                    st.rerun()
    
    @staticmethod
    def render_pagination(current_page: int, total_pages: int, base_key: str = "page"):
        """Render pagination controls."""
        if total_pages <= 1:
            return current_page
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            # Previous button
            prev_disabled = current_page <= 1
            if st.button("← Previous", disabled=prev_disabled, key=f"{base_key}_prev"):
                return max(1, current_page - 1)
            
            # Page info
            st.markdown(f"<div style='text-align: center; margin: 10px 0;'>Page {current_page} of {total_pages}</div>", 
                       unsafe_allow_html=True)
            
            # Next button
            next_disabled = current_page >= total_pages
            if st.button("Next →", disabled=next_disabled, key=f"{base_key}_next"):
                return min(total_pages, current_page + 1)
        
        return current_page
    
    @staticmethod
    def render_search_stats(metadata: Dict[str, Any]):
        """Render search statistics."""
        if not metadata:
            return
        
        cols = st.columns(4)
        
        with cols[0]:
            st.metric("Results", metadata.get('total_results', 0))
        
        with cols[1]:
            search_time = metadata.get('search_time_ms', 0)
            st.metric("Search Time", f"{search_time:.0f}ms")
        
        with cols[2]:
            st.metric("Pages", metadata.get('pages', 0))
        
        with cols[3]:
            showing = metadata.get('showing_results', '')
            if showing:
                st.markdown(f"**Showing:** {showing}")
    
    @staticmethod
    def render_data_status(metadata: Dict[str, Any]):
        """Render data loading status information."""
        if not metadata:
            return
        
        if metadata.get('error'):
            UIComponents.show_error_message(
                f"⚠️ Data Loading Error: {metadata['error']}", 
                "error"
            )
            return
        
        if metadata.get('success'):
            load_time = metadata.get('load_time')
            row_count = metadata.get('row_count', 0)
            
            if load_time:
                time_str = load_time.strftime("%H:%M:%S")
                UIComponents.show_error_message(
                    f"✅ Data loaded successfully at {time_str} • {row_count:,} parts available",
                    "success"
                )
    
    @staticmethod
    def render_search_suggestions(suggestions: List[str], query: str):
        """Render search suggestions dropdown."""
        if not suggestions or not query:
            return
        
        st.markdown("**Suggestions:**")
        for suggestion in suggestions:
            if st.button(f"💡 {suggestion}", key=f"suggest_{suggestion}"):
                st.session_state.search_query = suggestion
                st.rerun()
    
    @staticmethod
    def init_session_state():
        """Initialize session state variables."""
        if 'search_query' not in st.session_state:
            st.session_state.search_query = ""
        if 'current_page' not in st.session_state:
            st.session_state.current_page = 1
        if 'last_search_time' not in st.session_state:
            st.session_state.last_search_time = 0
    
    @staticmethod
    def should_debounce_search(debounce_ms: int = 300) -> bool:
        """Check if search should be debounced."""
        current_time = time.time() * 1000
        last_search_time = st.session_state.get('last_search_time', 0)
        
        if current_time - last_search_time < debounce_ms:
            return True
        
        st.session_state.last_search_time = current_time
        return False
    
    @staticmethod
    def render_admin_panel(data_manager, search_engine):
        """Render admin/debug panel in sidebar."""
        with st.sidebar:
            st.markdown("### 🔧 Admin Panel")
            
            # Data health check
            if st.button("🔍 Check Data Health"):
                with st.spinner("Checking..."):
                    health = data_manager.get_health_status()
                    
                    if health['status'] == 'healthy':
                        st.success(f"✅ Data source healthy ({health.get('response_time_ms', 0):.0f}ms)")
                    else:
                        st.error(f"❌ Data source {health['status']}: {health.get('error', 'Unknown error')}")
            
            # Search analytics
            if st.checkbox("📊 Show Analytics"):
                analytics = search_engine.get_analytics_summary()
                
                st.markdown("**Search Analytics:**")
                st.json(analytics)
            
            # Cache management
            if st.button("🗑️ Clear Cache"):
                st.cache_data.clear()
                st.success("Cache cleared!")
                st.rerun()
