# AliExpress Product Scraper

A powerful and user-friendly web interface for scraping product data from AliExpress with advanced product variant system and automated price monitoring.

![MIT License](https://img.shields.io/badge/License-MIT-green.svg)
![Python](https://img.shields.io/badge/Python-3.6+-blue.svg)

## Screenshots

### Search Interface
![Search Interface](screenshots/Capture1.PNG)

### Results and Field Selection
![Field Selection and Results](screenshots/Capture.PNG)

## 🌟 Key Features

### 🛍️ **Product Variant System**
- **Automatic Variant Detection**: Multi-level fallback (API → Interactive → HTML Analysis)
- **Intelligent Grouping**: Variants are automatically organized by product groups
- **Real Product Images**: Authentic AliExpress images for each variant
- **Automatic Tracking**: All discovered variants are automatically monitored

### 📊 **Product Monitoring & Tracking**
- **Price History Charts**: Visual representation of price trends with Chart.js
- **Selective Tracking**: Choose products individually or automatically for monitoring
- **Real-time Updates**: Automatic price updates and new variant discovery
- **Detailed Product Pages**: Comprehensive view with variants, price history, and store info

### 🌐 **Advanced Navigation**
- **Browse Gallery**: Browse all products with filters and sorting options
- **Search System**: Full-text search across all product titles
- **Settings Area**: Database management, statistics, and export functions
- **Responsive Design**: Optimized for desktop and mobile devices

### 🚀 **Scraping Engine**
- **API-based Scraping**: Fast and efficient data collection via AliExpress API
- **Intelligent Session Management**: Browser automation only for initial cookie capture
- **Anti-blocking Protection**: 
  - Configurable delay between requests (0.2–10 seconds)
  - Sequential processing to avoid server overload
  - Session caching to minimize browser automation overhead
- **Real-time Streaming**: Live updates during scraping process

### 📈 **Automation**
- **Scheduled Scraping**: Keyword-based automatic product updates
- **Scheduler System**: Configurable intervals for different search terms
- **Background Processing**: Automatic price monitoring without user interaction
- **Comprehensive Logging**: Detailed logging of all scraping activities

## 🏗️ Project Structure

```
aliexpress-scraper/
├── app.py                      # Flask web app with extended routing
├── scraper.py                  # Core scraping logic with variant system
├── models.py                   # SQLAlchemy database models
├── scheduler.py                # Automatic, scheduled scraping
├── templates/                  # Jinja2 templates for web interface
│   ├── index.html             # Main scraping interface
│   ├── browse.html            # Product gallery with filters
│   ├── product_detail.html    # Detail view with variants & charts
│   ├── search.html            # Search functionality
│   ├── settings.html          # Admin area
│   └── ...                    # Additional templates
├── results/                    # Exported CSV and JSON files
├── aliexpress_scraper.db      # SQLite database file
└── session_cache.json         # Cached session data
```

## 📦 Installation

1. Clone the repository:
```bash
git clone https://github.com/ImranDevPython/aliexpress-scraper.git
cd aliexpress-scraper
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## 🚀 Usage

### 1. Start the Application
```bash
python app.py
```

### 2. Open Web Interface
```
http://localhost:5000
```

### 3. Navigation and Features

#### **Main Page (Scraping)**
- Enter search term (e.g., "3D Filament", "Bluetooth Headphones")
- Choose number of pages to scrape (1–60)
- Select fields and set filters
- Configure request delay (recommended: 1 second)
- Start scraping and observe real-time progress

#### **Browse Gallery** (`/browse`)
- Browse all products in a clear gallery view
- Filter by category, store, or tracked products only
- Sort by price, rating, orders, or recency
- Pagination for large product collections

#### **Product Details** (`/product/<id>`)
- Complete product information with price history chart
- **Variant Gallery**: All available product variants with real images
- **Update Button**: Automatically find and track new variants
- **Tracking Control**: Enable/disable product for price monitoring
- Direct link to original AliExpress page

#### **Search** (`/search`)
- Full-text search across all stored products
- Quick filtering by product titles

#### **Settings** (`/settings`)
- Database statistics and management
- Data export for tracked products
- Cleanup of old data
- System overview

### 4. Using the Variant System

The heart of the application is the intelligent product variant system:

1. **Find Variants Automatically**: Click the "Update" button on a product detail page
2. **Multi-Level Detection**: The system automatically attempts:
   - API-based variant extraction
   - Interactive browser navigation
   - Intelligent HTML analysis with product-specific rules
3. **Automatic Tracking**: All discovered variants are automatically monitored
4. **Real Images**: Authentic AliExpress product images for each variant

## 🗄️ Database Structure

### Core Models
- **Product**: Product data, variants, shop, price, status, tracking
  - `product_id`: AliExpress Product ID (groups variants)
  - `sku_id`: Unique SKU for specific variants
  - `variant_title`: Variant description (e.g., "1KG Red", "Size L")
  - `is_tracked`: Tracking status for price monitoring
- **PriceHistory**: Historical price trends with timestamps
- **SearchKeyword**: Monitored search terms and their intervals
- **ScrapingLog**: Logging of all scraping activities

### Variant Grouping
Products are grouped via the `product_id` field. All variants of a product share the same `product_id` but have different `sku_id`s.

## 📋 Available Fields

- **Product ID** - AliExpress product identifier
- **SKU ID** - Unique variant identifier
- **Title** - Product title
- **Variant Title** - Variant description
- **Sale Price** - Current selling price
- **Original Price** - Original price
- **Discount (%)** - Discount percentage
- **Currency** - Currency
- **Rating** - Product rating
- **Orders Count** - Number of orders
- **Store Name** - Shop name
- **Store ID** - Shop identifier
- **Store URL** - Shop link
- **Product URL** - Product link
- **Image URL** - Product image

## ⚙️ Automatic Scraping & Scheduling

### Keyword Management
1. **Add Keywords**: Define search terms with intervals via `/keywords`
2. **Automatic Monitoring**: Scheduler performs regular searches
3. **Price History**: Automatic updates for tracked products
4. **View Logs**: Monitor all scraping activities via `/logs`

### Recommended Intervals
- **Frequent Updates**: 1-6 hours for important products
- **Regular Checks**: 12-24 hours for standard monitoring
- **Weekly Scans**: 168 hours for comprehensive market analysis

## 🛡️ Best Practices

### 1. **Request Delay**
- **Standard**: 1 second between requests
- **Automatic Scraping**: 2 seconds (more conservative)
- **Lower Values** (0.2–0.5s) increase blocking risk

### 2. **Page Count**
- **Manual**: Up to 60 pages per search
- **Automatic**: Maximum 3 pages to preserve server resources
- **Use Filters** for more targeted searches and better results

### 3. **Session Management**
- **Cache Duration**: 30 minutes for optimal performance
- **If Issues**: Delete `session_cache.json` and restart browser
- **Stealth Mode**: Automatic user-agent rotation

### 4. **Variant Optimization**
- **Update Frequency**: No more than once every 24 hours per product
- **Batch Processing**: Update multiple products simultaneously
- **Tracking Strategy**: Only track relevant variants permanently

## 🔧 Advanced Features

### API Endpoints
- `GET /api/products` - Product list with pagination
- `POST /api/product/<id>/update` - Update product and variants
- `POST /api/product/<id>/track` - Enable/disable tracking
- `GET /api/product/<id>/price_history` - Retrieve price history

### Data Export
- **JSON**: Complete data backup with metadata
- **CSV**: Spreadsheet-compatible format
- **Automatic**: Backup after each scraping session

### Debugging
- `GET /debug/product/<id>` - Variant debug information
- Comprehensive console logs for development
- Test scripts for variant system validation

## 🌍 Multi-Level Variant Detection

The system employs a sophisticated fallback strategy for maximum variant discovery:

### 1. **API Method** (Primary)
- Direct AliExpress API calls for official variant data
- Fastest and most reliable method
- Includes complete SKU information and pricing

### 2. **Interactive Browser Method** (Secondary)
- Automated browser navigation through variant options
- Simulates user interaction with color/size selectors
- Captures real-time price changes per variant

### 3. **HTML Analysis Method** (Fallback)
- Intelligent product-specific variant generation
- Uses product characteristics and known patterns
- Includes real AliExpress image URLs for known products

### 4. **Smart Demo Mode**
- For specific products (e.g., ANYCUBIC filaments)
- Pre-configured variants with authentic images
- Based on actual product analysis and user feedback

## 📈 Performance & Scalability

### Database Optimization
- Indexed product and variant relationships
- Efficient price history queries
- Automatic cleanup of old data

### Memory Management
- Session caching with TTL
- Streaming responses for large datasets
- Pagination for UI performance

### Monitoring
- Real-time scraping progress
- Error tracking and recovery
- Performance metrics and statistics

## 🛠️ Development & Testing

### Test Scripts
- `test_variants.py` - Variant system validation
- `test_browse_and_variants.py` - Browse functionality testing
- `debug_variant_scraping.py` - Debug variant detection

### Development Tools
- Debug routes for troubleshooting
- Comprehensive error logging
- Development mode with detailed output

## 📜 License

This project is licensed under the MIT License – see [LICENSE](LICENSE).

## ⚠️ Disclaimer

This tool is for educational purposes only. Use at your own responsibility and in compliance with AliExpress terms of service. Scraping should be done respectfully with appropriate delays.

## 🤝 Contributing

Contributions are welcome! Please create issues for bugs or feature requests, and pull requests for code improvements.

## 📞 Support

For questions or support:
- Create an issue on GitHub
- Check the debug endpoints for troubleshooting
- Review the comprehensive logging for error details

---

**Developed with ❤️ for E-Commerce Data Analysis**