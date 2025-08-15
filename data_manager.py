import pandas as pd
import requests
import logging
import streamlit as st
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
from io import StringIO
from config import AppConfig

logger = logging.getLogger(__name__)

class DataLoadError(Exception):
    """Custom exception for data loading errors."""
    pass

class DataManager:
    """Manages parts database loading, validation, and caching."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self._last_load_time: Optional[datetime] = None
        self._load_errors: list = []
    
    @st.cache_data(ttl=300, show_spinner=False)
    def load_parts_database(_self) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Load and validate parts data from source with comprehensive error handling."""
        metadata = {
            'load_time': datetime.now(),
            'success': False,
            'error': None,
            'row_count': 0,
            'data_quality': {}
        }
        
        try:
            logger.info(f"Loading parts database from: {_self.config.parts_database_url}")
            
            # Make request with proper timeout and error handling
            response = requests.get(
                _self.config.parts_database_url,
                timeout=_self.config.data_timeout,
                headers={'User-Agent': 'PartsFinderApp/1.0'}
            )
            response.raise_for_status()
            
            if not response.text.strip():
                raise DataLoadError("Empty response from data source")
            
            # Parse CSV with robust error handling
            df = _self._parse_csv_content(response.text)
            
            # Validate and clean data
            df = _self._validate_and_clean_data(df)
            
            # Generate data quality metrics
            metadata['data_quality'] = _self._analyze_data_quality(df)
            metadata['row_count'] = len(df)
            metadata['success'] = True
            
            logger.info(f"Successfully loaded {len(df)} parts")
            return df, metadata
            
        except requests.exceptions.Timeout:
            error_msg = "Data source timeout - please try again"
            logger.error(f"Timeout loading data: {error_msg}")
            metadata['error'] = error_msg
            
        except requests.exceptions.ConnectionError:
            error_msg = "Cannot connect to data source - check internet connection"
            logger.error(f"Connection error: {error_msg}")
            metadata['error'] = error_msg
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"Data source error (HTTP {e.response.status_code})"
            logger.error(f"HTTP error: {error_msg}")
            metadata['error'] = error_msg
            
        except DataLoadError as e:
            error_msg = str(e)
            logger.error(f"Data validation error: {error_msg}")
            metadata['error'] = error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error loading data: {str(e)}"
            logger.error(f"Unexpected error: {error_msg}")
            metadata['error'] = error_msg
        
        # Return empty dataframe with error metadata
        return pd.DataFrame(), metadata
    
    def _parse_csv_content(self, content: str) -> pd.DataFrame:
        """Parse CSV content with multiple fallback strategies."""
        parsing_strategies = [
            # Strategy 1: Standard parsing
            lambda: pd.read_csv(StringIO(content), quotechar='"', skipinitialspace=True),
            
            # Strategy 2: Python engine with error handling
            lambda: pd.read_csv(
                StringIO(content), 
                quotechar='"', 
                skipinitialspace=True,
                on_bad_lines='skip', 
                engine='python'
            ),
            
            # Strategy 3: Different delimiter detection
            lambda: pd.read_csv(
                StringIO(content),
                sep=None,
                engine='python',
                on_bad_lines='skip'
            )
        ]
        
        for i, strategy in enumerate(parsing_strategies):
            try:
                df = strategy()
                logger.info(f"CSV parsed successfully with strategy {i+1}")
                return df
            except Exception as e:
                logger.warning(f"CSV parsing strategy {i+1} failed: {str(e)}")
                continue
        
        raise DataLoadError("All CSV parsing strategies failed")
    
    def _validate_and_clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate and clean the loaded data."""
        if df.empty:
            raise DataLoadError("Loaded data is empty")
        
        # Check for required columns
        required_columns = ['part_number', 'description']
        
        # Try to find columns with similar names (case insensitive)
        df.columns = df.columns.str.strip().str.lower()
        
        missing_columns = []
        for col in required_columns:
            if col not in df.columns:
                # Try to find similar column names
                similar_cols = [c for c in df.columns if col.replace('_', '') in c.replace('_', '')]
                if similar_cols:
                    df = df.rename(columns={similar_cols[0]: col})
                    logger.info(f"Mapped column '{similar_cols[0]}' to '{col}'")
                else:
                    missing_columns.append(col)
        
        if missing_columns:
            raise DataLoadError(f"Missing required columns: {missing_columns}")
        
        # Clean and validate data
        original_count = len(df)
        
        # Convert to string and strip whitespace
        df['part_number'] = df['part_number'].astype(str).str.strip()
        df['description'] = df['description'].astype(str).str.strip()
        
        # Remove rows with missing data
        df = df.dropna(subset=['part_number', 'description'])
        df = df[df['part_number'].str.len() > 0]
        df = df[df['description'].str.len() > 0]
        
        # Remove obvious invalid entries
        df = df[df['part_number'] != 'nan']
        df = df[df['description'] != 'nan']
        
        # Remove duplicates
        duplicate_count = df.duplicated(subset=['part_number']).sum()
        if duplicate_count > 0:
            logger.warning(f"Removing {duplicate_count} duplicate part numbers")
            df = df.drop_duplicates(subset=['part_number'], keep='first')
        
        cleaned_count = len(df)
        removed_count = original_count - cleaned_count
        
        if removed_count > 0:
            logger.info(f"Cleaned data: removed {removed_count} invalid rows ({removed_count/original_count*100:.1f}%)")
        
        if df.empty:
            raise DataLoadError("No valid data remaining after cleaning")
        
        return df.reset_index(drop=True)
    
    def _analyze_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze data quality metrics."""
        return {
            'total_parts': len(df),
            'unique_part_numbers': df['part_number'].nunique(),
            'avg_description_length': df['description'].str.len().mean(),
            'empty_descriptions': (df['description'].str.len() == 0).sum(),
            'duplicate_part_numbers': df['part_number'].duplicated().sum(),
            'has_special_chars': df['part_number'].str.contains(r'[^A-Za-z0-9\-_]').sum()
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of data source."""
        try:
            response = requests.head(self.config.parts_database_url, timeout=5)
            return {
                'status': 'healthy' if response.status_code == 200 else 'degraded',
                'status_code': response.status_code,
                'response_time_ms': response.elapsed.total_seconds() * 1000,
                'last_check': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'last_check': datetime.now().isoformat()
            }
    
    def is_data_stale(self, load_time: datetime) -> bool:
        """Check if data is stale based on TTL."""
        if not load_time:
            return True
        return datetime.now() - load_time > timedelta(seconds=self.config.data_cache_ttl)
