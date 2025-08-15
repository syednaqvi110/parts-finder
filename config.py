import os
import logging
from typing import Optional
from dataclasses import dataclass

@dataclass
class AppConfig:
    """Application configuration with environment variable support."""
    
    # Data source configuration
    parts_database_url: str
    data_cache_ttl: int = 300  # 5 minutes
    data_timeout: int = 15  # seconds
    
    # Search configuration
    search_debounce_ms: int = 300
    max_search_results: int = 50
    min_search_length: int = 1
    fuzzy_threshold: int = 45
    
    # UI configuration
    results_per_page: int = 20
    max_recent_searches: int = 10
    
    # Performance configuration
    enable_analytics: bool = True
    enable_search_suggestions: bool = True
    
    # Logging configuration
    log_level: str = "INFO"
    
    @classmethod
    def from_env(cls) -> 'AppConfig':
        """Create configuration from environment variables."""
        return cls(
            parts_database_url=os.getenv(
                'PARTS_DATABASE_URL',
                "https://docs.google.com/spreadsheets/d/e/2PACX-1vSc2GTX3jc2NjJlR_zWVqDyTGf6bhCVc4GGaN_WMQDDlXZ8ofJVh5cbCPAD0d0lHY0anWXreyMdon33/pub?output=csv"
            ),
            data_cache_ttl=int(os.getenv('DATA_CACHE_TTL', '300')),
            data_timeout=int(os.getenv('DATA_TIMEOUT', '15')),
            search_debounce_ms=int(os.getenv('SEARCH_DEBOUNCE_MS', '300')),
            max_search_results=int(os.getenv('MAX_SEARCH_RESULTS', '50')),
            min_search_length=int(os.getenv('MIN_SEARCH_LENGTH', '1')),
            fuzzy_threshold=int(os.getenv('FUZZY_THRESHOLD', '45')),
            results_per_page=int(os.getenv('RESULTS_PER_PAGE', '20')),
            max_recent_searches=int(os.getenv('MAX_RECENT_SEARCHES', '10')),
            enable_analytics=os.getenv('ENABLE_ANALYTICS', 'true').lower() == 'true',
            enable_search_suggestions=os.getenv('ENABLE_SEARCH_SUGGESTIONS', 'true').lower() == 'true',
            log_level=os.getenv('LOG_LEVEL', 'INFO').upper()
        )
    
    def validate(self) -> bool:
        """Validate configuration values."""
        if not self.parts_database_url:
            return False
        if self.data_cache_ttl < 0:
            return False
        if self.max_search_results < 1:
            return False
        if self.results_per_page < 1:
            return False
        return True

def setup_logging(config: AppConfig) -> None:
    """Setup application logging."""
    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )

# Global configuration instance
config = AppConfig.from_env()
setup_logging(config)
