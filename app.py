import streamlit as st
import time
import logging
from typing import Optional

# Import our custom modules
from config import config
from data_manager import DataManager
from search_engine import EnhancedSearchEngine
from ui_components import UIComponents

# Configure logging
logger = logging.getLogger(__name__)

# Configure Streamlit page
st.set_page_config(
    page_title="Parts Finder - Smart Parts Search",
    page_icon="🔧",
    layout="centered",
    initial_sidebar_state="collapsed"
)

class PartsFinderApp:
    """Main Parts Finder application class."""
    
    def __init__(self):
        self.config = config
        self.data_manager = DataManager(self.config)
        self.search_engine = EnhancedSearchEngine(self.config)
        self.ui = UIComponents()
        
        # Validate configuration
        if not self.config.validate():
            st.error("❌ Invalid configuration. Please check your environment variables.")
            st.stop()
    
    def run(self):
        """Main application entry point."""
        try:
            # Initialize session state
            self.ui.init_session_state()
            
            # Render custom CSS
            self.ui.render_custom_css()
            
            # Load data with error handling
            df, data_metadata = self._load_data_with_status()
            
            # Render main interface
            self._render_main_interface(df, data_metadata)
            
            # Render admin panel if needed
            if st.sidebar.checkbox("🔧 Admin Panel"):
                self.ui.render_admin_panel(self.data_manager, self.search_engine)
        
        except Exception as e:
            logger.error(f"Application error: {str(e)}")
            self.ui.show_error_message(
                f"Application error: {str(e)}. Please refresh the page or contact support.",
                "error"
            )
    
    def _load_data_with_status(self):
        """Load data and show loading status."""
        with st.spinner("Loading parts database..."):
            df, metadata = self.data_manager.load_parts_database()
        
        # Show data status
        self.ui.render_data_status(metadata)
        
        return df, metadata
    
    def _render_main_interface(self, df, data_metadata):
        """Render the main search interface."""
        # Header
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(
            "<h1 style='text-align: center; font-size: 4em; margin-bottom: 30px;'>🔧 Parts Finder</h1>", 
            unsafe_allow_html=True
        )
        
        # Search section
        self._render_search_section(df)
        
        # Show data quality info if available
        if data_metadata.get('data_quality'):
            with st.expander("📊 Data Quality Info"):
                quality = data_metadata['data_quality']
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total Parts", f"{quality.get('total_parts', 0):,}")
                with col2:
                    st.metric("Unique Parts", f"{quality.get('unique_part_numbers', 0):,}")
                with col3:
                    avg_desc_len = quality.get('avg_description_length', 0)
                    st.metric("Avg Description Length", f"{avg_desc_len:.0f} chars")
    
    def _render_search_section(self, df):
        """Render the search input and results section."""
        # Search input with debouncing
        search_query = st.text_input(
            label="Search",
            placeholder="Enter part number or description...",
            value=st.session_state.get('search_query', ''),
            label_visibility="collapsed",
            key="search_input_field",
            help="Search for parts by number or description. Use partial matches for broader results."
        )
        
        # Update session state if query changed
        if search_query != st.session_state.get('search_query', ''):
            st.session_state.search_query = search_query
            st.session_state.current_page = 1  # Reset to first page on new search
        
        # Show recent searches if no query
        if not search_query.strip():
            recent_searches = self.search_engine.get_recent_searches()
            if recent_searches:
                st.markdown("<br>", unsafe_allow_html=True)
                self.ui.render_recent_searches(recent_searches)
            return
        
        # Handle empty data
        if df.empty:
            if data_metadata := getattr(self, '_last_data_metadata', None):
                if data_metadata.get('error'):
                    self.ui.show_error_message(
                        "Cannot search: Data is not available. Please check your internet connection and try again.",
                        "error"
                    )
            return
        
        # Show search suggestions for partial queries
        if len(search_query.strip()) >= 2:
            suggestions = self.search_engine.get_search_suggestions(search_query)
            if suggestions:
                with st.expander("💡 Search Suggestions", expanded=False):
                    self.ui.render_search_suggestions(suggestions, search_query)
        
        # Perform search with debouncing for better UX
        self._perform_search_with_debouncing(search_query, df)
    
    def _perform_search_with_debouncing(self, query: str, df):
        """Perform search with debouncing to avoid too many requests."""
        # Skip very short queries
        if len(query.strip()) < self.config.min_search_length:
            self.ui.show_error_message(
                f"Please enter at least {self.config.min_search_length} character(s) to search.",
                "info"
            )
            return
        
        # Show loading state for longer queries
        if len(query) > 3:
            with st.spinner("Searching..."):
                time.sleep(0.1)  # Brief pause for UI feedback
                self._execute_search(query, df)
        else:
            self._execute_search(query, df)
    
    def _execute_search(self, query: str, df):
        """Execute the actual search and display results."""
        try:
            current_page = st.session_state.get('current_page', 1)
            
            # Perform search
            results, search_metadata = self.search_engine.search(query, df, current_page)
            
            # Show search statistics
            if search_metadata.get('total_results', 0) > 0:
                self.ui.render_search_stats(search_metadata)
            
            # Handle no results
            if not results:
                no_result_suggestions = self.search_engine.get_search_suggestions(query)
                self.ui.show_no_results_message(query, no_result_suggestions)
                return
            
            # Render pagination controls (top)
            if search_metadata.get('pages', 0) > 1:
                st.markdown("<br>", unsafe_allow_html=True)
                new_page = self.ui.render_pagination(
                    current_page, 
                    search_metadata['pages'], 
                    "top_pagination"
                )
                if new_page != current_page:
                    st.session_state.current_page = new_page
                    st.rerun()
            
            # Render search results
            st.markdown("<br>", unsafe_allow_html=True)
            self._render_search_results(results, query)
            
            # Render pagination controls (bottom)
            if search_metadata.get('pages', 0) > 1:
                st.markdown("<br>", unsafe_allow_html=True)
                new_page = self.ui.render_pagination(
                    current_page, 
                    search_metadata['pages'], 
                    "bottom_pagination"
                )
                if new_page != current_page:
                    st.session_state.current_page = new_page
                    st.rerun()
        
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            self.ui.show_error_message(
                f"Search error: {str(e)}. Please try a different search term.",
                "error"
            )
    
    def _render_search_results(self, results, query):
        """Render the search results list."""
        for idx, (_, part_number, description, score) in enumerate(results):
            with st.container():
                # Add some debug info in development
                if st.sidebar.checkbox("🐛 Debug Mode") and score:
                    debug_info = f" (Score: {score})"
                    part_number_display = f"{part_number}{debug_info}"
                else:
                    part_number_display = part_number
                
                # Render individual result
                self.ui.render_search_result(
                    part_number_display, 
                    description, 
                    query, 
                    self.search_engine
                )
                
                # Add copy buttons for easy access
                col1, col2 = st.columns([3, 1])
                with col2:
                    if st.button("📋 Copy", key=f"copy_{idx}_{part_number}", help="Copy part number"):
                        st.write(f"Part number copied: `{part_number}`")
    
    def _handle_keyboard_navigation(self):
        """Handle keyboard navigation (future enhancement)."""
        # This would require JavaScript integration
        # For now, we'll use Streamlit's built-in navigation
        pass
    
    def health_check(self) -> dict:
        """Application health check endpoint."""
        try:
            # Check data source
            data_health = self.data_manager.get_health_status()
            
            # Check search functionality
            test_df = self.data_manager.load_parts_database()[0]
            search_healthy = not test_df.empty
            
            return {
                'status': 'healthy' if data_health['status'] == 'healthy' and search_healthy else 'degraded',
                'data_source': data_health,
                'search_engine': 'healthy' if search_healthy else 'unhealthy',
                'timestamp': time.time()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': time.time()
            }

def main():
    """Application entry point."""
    try:
        # Create and run the application
        app = PartsFinderApp()
        app.run()
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Fatal application error: {str(e)}")
        st.error(f"😞 Fatal application error: {str(e)}")
        st.error("Please refresh the page or contact support if the problem persists.")

if __name__ == "__main__":
    main()
