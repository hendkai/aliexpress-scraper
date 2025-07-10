# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Development
- Install dependencies: `pip install -r requirements.txt`
- Start the web application: `python app.py`
- Run scraper directly: `python scraper.py`

### Database
- Database is automatically created on first run (SQLite: `aliexpress_scraper.db`)
- All tables are created automatically when the app starts

### Project Structure
- `app.py` - Flask web application with database integration
- `scraper.py` - Core scraping logic and AliExpress API integration
- `models.py` - SQLAlchemy database models
- `scheduler.py` - Automatic background scraping system
- `templates/` - Jinja2 templates for web interface
  - `index.html` - Main scraping interface
  - `search.html` - Product search and browse
  - `product_detail.html` - Product details with price history charts
  - `keywords.html` - Auto-scraping keyword management
  - `logs.html` - Scraping activity logs
- `results/` - Directory for backup CSV and JSON files
- `session_cache.json` - Cached browser session data (30-minute validity)
- `aliexpress_scraper.db` - SQLite database file

## Architecture

### Multi-Layer Architecture
The application operates on a multi-layer architecture:

1. **Web Layer (`app.py`)**:
   - Flask application with SQLAlchemy ORM integration
   - Server-Sent Events (SSE) for real-time progress streaming
   - Multiple routes for different functionalities:
     - `/` - Main scraping interface with recent products
     - `/search` - Product search and browse
     - `/product/<id>` - Product detail view with price history
     - `/keywords` - Auto-scraping keyword management
     - `/logs` - Scraping activity monitoring
     - `/api/*` - REST API endpoints for AJAX requests
   - User input validation and parameter processing

2. **Database Layer (`models.py`)**:
   - SQLAlchemy models for data persistence
   - Product table with basic product information
   - PriceHistory table for tracking price changes over time
   - SearchKeyword table for managing automatic scraping
   - ScrapingLog table for monitoring scraping activities
   - Relationships and methods for easy data access

3. **Scraping Layer (`scraper.py`)**:
   - Smart session management with browser automation fallback
   - Direct AliExpress API calls using SessionPage from DrissionPage
   - Database integration for product and price history storage
   - Configurable request delays and filtering options
   - Dual output: database storage + file backup

4. **Scheduler Layer (`scheduler.py`)**:
   - Background automatic scraping system
   - Schedule-based keyword scraping (configurable intervals)
   - Automatic price history updates
   - Error handling and logging for unattended operation
   - Threading for non-blocking execution

### Session Management Strategy
- **Primary**: Uses cached session data (cookies, user-agent) for 30 minutes
- **Fallback**: Headless browser automation (DrissionPage) for fresh session initialization
- **Optimization**: Blocks images and CSS during browser sessions to improve performance

### Data Flow

#### Manual Scraping:
1. User configures search parameters through web interface
2. Session data retrieved from cache or browser automation
3. Sequential API requests to AliExpress with configurable delays
4. Raw product data extracted and filtered based on user selections
5. Products saved to database with price history entries
6. Backup files created in `results/` directory
7. Real-time progress streamed back to user interface

#### Automatic Scraping:
1. Scheduler checks active keywords based on configured intervals
2. Background scraping initiated for due keywords
3. Products updated in database with new price history entries
4. Scraping logs created for monitoring
5. Process repeats according to keyword schedules

#### Product Browsing:
1. User searches products or browses recent additions
2. Products displayed with current prices and images
3. User selects product to view detailed information
4. Price history chart rendered with historical data
5. Links to original AliExpress product pages

### Database Schema

#### Product Fields:
- Basic: Product ID, Title, Description, Image URL, Product URL
- Pricing: Currency (stored separately from price history)
- Store: Store Name, Store ID, Store URL
- Metrics: Rating, Orders Count
- Meta: Created/Updated timestamps, Active status

#### Price History Fields:
- Sale Price, Original Price, Discount Percentage
- Timestamp for price tracking
- Foreign key relationship to Product

#### Search Keywords:
- Keyword text and active status
- Scraping frequency (hours) and last scraped timestamp

#### Scraping Logs:
- Keyword, start/finish times, status, product count
- Error messages for failed scraping attempts


### Key Features

#### Price History Tracking:
- Automatic price tracking over time for all products
- Visual price history charts using Chart.js
- Support for different time ranges (30 days default)
- Price comparison between sale and original prices

#### Automatic Scraping:
- Background scheduler for regular price updates
- Configurable scraping intervals (1 hour to weekly)
- Keyword-based automatic product discovery
- Comprehensive logging and monitoring

#### Search and Browse:
- Full-text search across product titles
- Product browsing with images and current prices
- Recently updated products display
- Product detail pages with complete information

#### Error Handling:
- Database transaction rollbacks on failures
- Graceful handling of session expiration and API failures
- Real-time error reporting through SSE stream
- Automatic retry logic for session initialization
- Comprehensive logging throughout all processes

### Rate Limiting & Anti-Block Features
- Configurable delay between requests (0.2-10 seconds, default 1 second)
- Longer delays for automatic scraping (2 seconds default)
- Sequential request processing to avoid overwhelming servers
- Session caching to minimize browser automation overhead
- Proper referer headers and user-agent rotation
- Limited page scraping for automatic runs (3 pages max)