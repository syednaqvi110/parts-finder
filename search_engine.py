import pandas as pd
import re
import logging
from typing import List, Tuple, Set, Dict, Any
from rapidfuzz import fuzz, process
from collections import defaultdict, Counter
from datetime import datetime
import streamlit as st
from config import AppConfig

logger = logging.getLogger(__name__)

class SearchAnalytics:
    """Track and analyze search patterns."""
    
    def __init__(self):
        if 'search_analytics' not in st.session_state:
            st.session_state.search_analytics = {
                'total_searches': 0,
                'search_history': [],
                'popular_queries': Counter(),
                'no_result_queries': [],
                'performance_metrics': []
            }
    
    def log_search(self, query: str, result_count: int, search_time_ms: float):
        """Log a search query and its results."""
        analytics = st.session_state.search_analytics
        
        analytics['total_searches'] += 1
        analytics['search_history'].append({
            'query': query,
            'result_count': result_count,
            'timestamp': datetime.now().isoformat(),
            'search_time_ms': search_time_ms
        })
        
        # Keep only last 1000 searches
        if len(analytics['search_history']) > 1000:
            analytics['search_history'] = analytics['search_history'][-1000:]
        
        # Track popular queries
        if len(query.strip()) > 2:
            analytics['popular_queries'][query.lower()] += 1
        
        # Track no-result queries
        if result_count == 0 and query.strip():
            analytics['no_result_queries'].append(query)
            if len(analytics['no_result_queries']) > 100:
                analytics['no_result_queries'] = analytics['no_result_queries'][-100:]
        
        # Track performance
        analytics['performance_metrics'].append(search_time_ms)
        if len(analytics['performance_metrics']) > 100:
            analytics['performance_metrics'] = analytics['performance_metrics'][-100:]
    
    def get_suggestions(self, partial_query: str, limit: int = 5) -> List[str]:
        """Get search suggestions based on search history."""
        if len(partial_query.strip()) < 2:
            return []
        
        analytics = st.session_state.search_analytics
        partial_lower = partial_query.lower()
        
        # Find matching queries from history
        suggestions = []
        for query, count in analytics['popular_queries'].most_common(50):
            if partial_lower in query and query != partial_lower:
                suggestions.append(query)
                if len(suggestions) >= limit:
                    break
        
        return suggestions
    
    def get_recent_searches(self, limit: int = 10) -> List[str]:
        """Get recent unique search queries."""
        analytics = st.session_state.search_analytics
        recent_queries = []
        seen = set()
        
        for search in reversed(analytics['search_history']):
            query = search['query'].strip()
            if query and query not in seen and search['result_count'] > 0:
                recent_queries.append(query)
                seen.add(query)
                if len(recent_queries) >= limit:
                    break
        
        return recent_queries

class EnhancedSearchEngine:
    """Enhanced search engine with improved algorithms and features."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.analytics = SearchAnalytics()
        
        # Pre-compile regex patterns for performance
        self.word_split_pattern = re.compile(r'[-_\s\.]+')
        self.highlight_cache = {}
    
    def search(self, query: str, df: pd.DataFrame, page: int = 1) -> Tuple[List[Tuple], Dict[str, Any]]:
        """Main search function with analytics and pagination."""
        start_time = datetime.now()
        
        # Input validation
        if not query or not query.strip():
            return [], {'total_results': 0, 'pages': 0, 'current_page': page}
        
        if df.empty:
            return [], {'total_results': 0, 'pages': 0, 'current_page': page, 'error': 'No data available'}
        
        query = query.strip()
        if len(query) < self.config.min_search_length:
            return [], {'total_results': 0, 'pages': 0, 'current_page': page}
        
        # Perform search
        all_results = self._perform_search(query, df)
        
        # Calculate pagination
        total_results = len(all_results)
        total_pages = (total_results + self.config.results_per_page - 1) // self.config.results_per_page
        start_idx = (page - 1) * self.config.results_per_page
        end_idx = start_idx + self.config.results_per_page
        
        paginated_results = all_results[start_idx:end_idx]
        
        # Log analytics
        search_time = (datetime.now() - start_time).total_seconds() * 1000
        if self.config.enable_analytics:
            self.analytics.log_search(query, total_results, search_time)
        
        metadata = {
            'total_results': total_results,
            'pages': total_pages,
            'current_page': page,
            'search_time_ms': search_time,
            'showing_results': f"{start_idx + 1}-{min(end_idx, total_results)} of {total_results}" if total_results > 0 else "0 results"
        }
        
        return paginated_results, metadata
    
    def _perform_search(self, query: str, df: pd.DataFrame) -> List[Tuple]:
        """Core search algorithm with multiple strategies."""
        query_lower = query.lower()
        results = []
        seen_indices = set()
        
        # Strategy 1: Exact matches (highest priority)
        exact_results = self._exact_match_search(query_lower, df)
        for result in exact_results:
            if result[0] not in seen_indices:
                results.append(result)
                seen_indices.add(result[0])
        
        # Strategy 2: Prefix and substring matches
        substring_results = self._substring_search(query_lower, df, seen_indices)
        results.extend(substring_results)
        seen_indices.update(r[0] for r in substring_results)
        
        # Strategy 3: Word-based matches
        word_results = self._word_match_search(query_lower, df, seen_indices)
        results.extend(word_results)
        seen_indices.update(r[0] for r in word_results)
        
        # Strategy 4: Fuzzy matches (lowest priority)
        if len(query) > 2:
            fuzzy_results = self._fuzzy_search(query_lower, df, seen_indices)
            results.extend(fuzzy_results)
        
        # Sort by score and limit results
        results.sort(key=lambda x: x[3], reverse=True)
        return results[:self.config.max_search_results]
    
    def _exact_match_search(self, query: str, df: pd.DataFrame) -> List[Tuple]:
        """Find exact matches."""
        results = []
        
        for idx, row in df.iterrows():
            part_num_lower = row['part_number'].lower()
            desc_lower = row['description'].lower()
            
            if query == part_num_lower:
                results.append((idx, row['part_number'], row['description'], 100))
            elif query == desc_lower:
                results.append((idx, row['part_number'], row['description'], 98))
        
        return results
    
    def _substring_search(self, query: str, df: pd.DataFrame, seen_indices: Set[int]) -> List[Tuple]:
        """Find prefix and substring matches."""
        results = []
        
        for idx, row in df.iterrows():
            if idx in seen_indices:
                continue
                
            part_num_lower = row['part_number'].lower()
            desc_lower = row['description'].lower()
            
            # Prefix matches
            if part_num_lower.startswith(query):
                score = 95 - min(10, len(part_num_lower) - len(query))  # Prefer shorter matches
                results.append((idx, row['part_number'], row['description'], score))
            elif desc_lower.startswith(query):
                results.append((idx, row['part_number'], row['description'], 88))
            
            # Substring matches
            elif query in part_num_lower:
                position_penalty = part_num_lower.index(query) * 2  # Prefer matches at beginning
                score = max(70, 90 - position_penalty)
                results.append((idx, row['part_number'], row['description'], score))
            elif query in desc_lower:
                results.append((idx, row['part_number'], row['description'], 75))
        
        return results
    
    def _word_match_search(self, query: str, df: pd.DataFrame, seen_indices: Set[int]) -> List[Tuple]:
        """Find word-based matches."""
        results = []
        query_words = set(self.word_split_pattern.split(query.lower()))
        query_words = {w for w in query_words if len(w) > 1}  # Filter short words
        
        if not query_words:
            return results
        
        for idx, row in df.iterrows():
            if idx in seen_indices:
                continue
            
            part_words = set(self.word_split_pattern.split(row['part_number'].lower()))
            desc_words = set(row['description'].lower().split())
            
            # Calculate word matches
            part_matches = len(query_words.intersection(part_words))
            desc_matches = len(query_words.intersection(desc_words))
            
            total_matches = part_matches * 2 + desc_matches  # Weight part number matches higher
            
            if total_matches > 0:
                # Score based on match ratio and total matches
                match_ratio = (part_matches + desc_matches) / len(query_words)
                base_score = 50 + (match_ratio * 30)
                bonus = min(10, total_matches * 2)
                score = int(base_score + bonus)
                results.append((idx, row['part_number'], row['description'], score))
        
        return results
    
    def _fuzzy_search(self, query: str, df: pd.DataFrame, seen_indices: Set[int]) -> List[Tuple]:
        """Perform fuzzy matching on remaining items."""
        remaining_indices = [i for i in range(len(df)) if i not in seen_indices]
        
        if not remaining_indices:
            return []
        
        # Create searchable text for remaining items
        searchable_texts = []
        for idx in remaining_indices:
            row = df.iloc[idx]
            searchable_text = f"{row['part_number']} {row['description']}".lower()
            searchable_texts.append(searchable_text)
        
        # Perform fuzzy search
        fuzzy_results = process.extract(
            query, 
            searchable_texts, 
            scorer=fuzz.WRatio, 
            limit=min(30, len(remaining_indices))
        )
        
        results = []
        for match_text, score, relative_idx in fuzzy_results:
            if score >= self.config.fuzzy_threshold:
                actual_idx = remaining_indices[relative_idx]
                row = df.iloc[actual_idx]
                
                # Adjust score to fit our range
                adjusted_score = int(30 + (score - self.config.fuzzy_threshold) * 40 / (100 - self.config.fuzzy_threshold))
                results.append((actual_idx, row['part_number'], row['description'], adjusted_score))
        
        return results
    
    def get_search_suggestions(self, partial_query: str) -> List[str]:
        """Get search suggestions."""
        if not self.config.enable_search_suggestions:
            return []
        return self.analytics.get_suggestions(partial_query)
    
    def get_recent_searches(self) -> List[str]:
        """Get recent searches."""
        return self.analytics.get_recent_searches(self.config.max_recent_searches)
    
    def highlight_matches(self, text: str, query: str) -> str:
        """Highlight matching terms in text with caching."""
        cache_key = f"{text}:{query}"
        if cache_key in self.highlight_cache:
            return self.highlight_cache[cache_key]
        
        if not query.strip():
            return text
        
        # Extract meaningful words from query
        query_words = [word for word in self.word_split_pattern.split(query.lower()) if len(word) > 1]
        
        highlighted = text
        for word in query_words:
            pattern = re.compile(f'({re.escape(word)})', re.IGNORECASE)
            highlighted = pattern.sub(r'<span class="highlight">\1</span>', highlighted)
        
        # Cache result (keep cache size manageable)
        if len(self.highlight_cache) > 1000:
            # Clear oldest entries
            items = list(self.highlight_cache.items())
            self.highlight_cache = dict(items[-500:])
        
        self.highlight_cache[cache_key] = highlighted
        return highlighted
    
    def get_analytics_summary(self) -> Dict[str, Any]:
        """Get search analytics summary."""
        analytics = st.session_state.search_analytics
        
        avg_search_time = 0
        if analytics['performance_metrics']:
            avg_search_time = sum(analytics['performance_metrics']) / len(analytics['performance_metrics'])
        
        return {
            'total_searches': analytics['total_searches'],
            'avg_search_time_ms': round(avg_search_time, 2),
            'top_queries': dict(analytics['popular_queries'].most_common(5)),
            'no_result_rate': len(analytics['no_result_queries']) / max(1, analytics['total_searches']) * 100
        }
