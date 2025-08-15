🔧 Parts Finder - Smart Parts Search Engine
A powerful, intelligent search engine for parts lookup designed for technicians and engineers. Features advanced search algorithms, real-time results, comprehensive error handling, and analytics.
Show Image
✨ Features
🔍 Advanced Search

Multi-strategy Search Algorithm: Exact matches, prefix matching, substring matching, and fuzzy search
Smart Ranking: Results ranked by relevance with configurable scoring
Typo Tolerance: Fuzzy matching with configurable threshold
Real-time Results: Debounced search with instant feedback
Search Suggestions: AI-powered query suggestions based on search history
Recent Searches: Quick access to previously searched terms

🚀 Performance & UX

Fast Loading: Optimized data caching with configurable TTL
Pagination: Handle large datasets with smooth navigation
Loading States: Visual feedback during search operations
Error Recovery: Graceful handling of network issues and data problems
Mobile Responsive: Works perfectly on all device sizes

📊 Analytics & Monitoring

Search Analytics: Track popular queries, search patterns, and performance
Data Quality Metrics: Monitor data health and completeness
Performance Monitoring: Search timing and response metrics
Health Checks: Automated system health monitoring

🔧 Administration

Environment Configuration: Easy setup with environment variables
Multiple Data Sources: Support for Google Sheets, CSV files, and more
Admin Panel: Built-in administration interface
Cache Management: Manual cache clearing and data refresh
Debug Mode: Detailed search scoring and performance information

🚀 Quick Start
1. Setup Data Source
Create a Google Sheet with two columns:

part_number: The part number/identifier
description: Part description

Publish your sheet as CSV:

File → Share → Publish to web
Choose "Entire Document" and "CSV"
Copy the generated URL

2. Clone and Configure
bashgit clone <your-repo-url>
cd parts-finder

# Copy environment configuration
cp .env.example .env

# Edit .env file with your Google Sheets URL
nano .env
3. Install Dependencies
bashpip install -r requirements.txt
4. Run the Application
bashstreamlit run app.py
The app will be available at http://localhost:8501
⚙️ Configuration
The application is highly configurable through environment variables. See .env.example for all available options:
Key Configuration Options
VariableDefaultDescriptionPARTS_DATABASE_URLRequiredURL to your CSV data sourceDATA_CACHE_TTL300Cache time-to-live in secondsMAX_SEARCH_RESULTS50Maximum search results returnedSEARCH_DEBOUNCE_MS300Search debounce delay in millisecondsRESULTS_PER_PAGE20Results per page for paginationFUZZY_THRESHOLD45Fuzzy matching threshold (0-100)ENABLE_ANALYTICStrueEnable search analytics trackingLOG_LEVELINFOLogging level (DEBUG/INFO/WARNING/ERROR)
🏗️ Architecture
The application is built with a modular architecture:
parts-finder/
├── app.py                 # Main application entry point
├── config.py             # Configuration management
├── data_manager.py       # Data loading and validation
├── search_engine.py      # Advanced search algorithms
├── ui_components.py      # UI helper components
├── requirements.txt      # Python dependencies
├── .env.example         # Environment configuration template
└── README.md           # This file
Core Components

Configuration Management: Environment-based configuration with validation
Data Manager: Robust data loading with error handling and caching
Search Engine: Multi-strategy search with analytics and suggestions
UI Components: Reusable interface components with consistent styling

🔍 Search Capabilities
Search Strategies (in order of priority)

Exact Matches: Perfect matches get highest priority (score: 100)
Prefix Matches: Parts starting with search query (score: 90-95)
Substring Matches: Parts containing search query (score: 70-90)
Word Matches: Individual word matches (score: 50-85)
Fuzzy Matches: Approximate matches using edit distance (score: 30-70)

Search Features

Multi-word Search: Searches across multiple words automatically
Partial Matching: Find parts with incomplete part numbers
Case Insensitive: Search works regardless of case
Special Character Handling: Handles hyphens, underscores, and spaces
Performance Optimization: Caching and efficient algorithms for large datasets

📊 Analytics Dashboard
Access the admin panel through the sidebar to view:

Search Statistics: Total searches, average response time, popular queries
Data Quality Metrics: Part count, data completeness, duplicate detection
Performance Monitoring: Search timing, cache hit rates, error rates
Health Status: Data source connectivity and system health

🚀 Deployment
Streamlit Cloud

Push your code to GitHub
Connect to Streamlit Cloud
Add your environment variables in the Streamlit Cloud dashboard
Deploy!

Docker Deployment
dockerfileFROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
Environment Variables for Production
bash# Production environment variables
PARTS_DATABASE_URL=your_production_csv_url
DATA_CACHE_TTL=600
ENABLE_ANALYTICS=true
LOG_LEVEL=WARNING
🧪 Testing
Run the test suite:
bash# Install test dependencies
pip install pytest pytest-cov

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html
🔧 Development
Adding New Features

Data Sources: Extend DataManager class to support new data formats
Search Algorithms: Add new search strategies to EnhancedSearchEngine
UI Components: Create reusable components in UIComponents
Configuration: Add new options to AppConfig class

Code Quality
The codebase follows these principles:

Type Hints: Full type annotation for better IDE support
Error Handling: Comprehensive error handling with user-friendly messages
Logging: Structured logging for debugging and monitoring
Modularity: Clean separation of concerns
Documentation: Inline documentation and examples

🐛 Troubleshooting
Common Issues
Data Not Loading

Check your CSV URL is publicly accessible
Verify CSV format has part_number and description columns
Check internet connectivity

Slow Search Performance

Reduce MAX_SEARCH_RESULTS in configuration
Increase SEARCH_DEBOUNCE_MS for slower typing
Consider data optimization (remove duplicates, clean descriptions)

Memory Issues

Reduce DATA_CACHE_TTL to refresh data more frequently
Limit dataset size or implement data pagination
Monitor memory usage in production

Debug Mode
Enable debug mode in the sidebar to see:

Search algorithm scoring
Performance metrics
Data quality information
Cache statistics

📈 Performance Optimization

Caching: Automatic data caching with configurable TTL
Debouncing: Search request debouncing to reduce server load
Pagination: Efficient result pagination for large datasets
Indexing: Pre-computed search indices for faster lookups
Algorithm Optimization: Multi-pass search with early termination

🤝 Contributing

Fork the repository
Create a feature branch: git checkout -b feature/new-feature
Make your changes and add tests
Commit your changes: git commit -am 'Add new feature'
Push to the branch: git push origin feature/new-feature
Submit a pull request

📄 License
This project is licensed under the MIT License - see the LICENSE file for details.
🆘 Support

Documentation: Check this README and inline code documentation
Issues: Report bugs and request features through GitHub Issues
Discussions: Join discussions in GitHub Discussions
Email: Contact the maintainer for urgent issues

🗓️ Roadmap

 Machine Learning: AI-powered search ranking and suggestions
 API Integration: REST API for external system integration
 Mobile App: Native mobile applications
 Advanced Filters: Category, manufacturer, and date filters
 Inventory Integration: Real-time inventory status
 Multi-language Support: Internationalization
 Advanced Analytics: Machine learning insights and predictions
