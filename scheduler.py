import schedule
import time
import threading
from datetime import datetime, timedelta
from models import db, SearchKeyword, ScrapingLog, Product
from scraper import run_scrape_job, initialize_session_data, scrape_aliexpress_data, extract_product_details, save_results_to_database
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AutoScraper:
    def __init__(self, app):
        self.app = app
        self.running = False
        self.thread = None
        
    def start(self):
        """Start the automatic scraping scheduler"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        logger.info("Auto-scraper started")
    
    def stop(self):
        """Stop the automatic scraping scheduler"""
        self.running = False
        if self.thread:
            self.thread.join()
        logger.info("Auto-scraper stopped")
    
    def _run_scheduler(self):
        """Main scheduler loop"""
        # Schedule checks every hour
        schedule.every(1).hours.do(self._check_and_scrape)
        
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def _check_and_scrape(self):
        """Check which keywords need scraping and execute them"""
        with self.app.app_context():
            try:
                # Get active keywords that need scraping
                keywords_to_scrape = self._get_keywords_to_scrape()
                
                for keyword_obj in keywords_to_scrape:
                    self._scrape_keyword(keyword_obj)
                    
            except Exception as e:
                logger.error(f"Error in scheduler: {e}")
    
    def _get_keywords_to_scrape(self):
        """Get keywords that need to be scraped based on their schedule"""
        now = datetime.utcnow()
        keywords = SearchKeyword.query.filter_by(is_active=True).all()
        
        keywords_to_scrape = []
        
        for keyword in keywords:
            # Check if it's time to scrape this keyword
            if keyword.last_scraped is None:
                # Never scraped before, scrape now
                keywords_to_scrape.append(keyword)
            else:
                # Check if enough time has passed
                frequency = keyword.track_frequency_hours if keyword.track_frequency_hours else keyword.scrape_frequency_hours
                next_scrape_time = keyword.last_scraped + timedelta(hours=frequency)
                if now >= next_scrape_time:
                    keywords_to_scrape.append(keyword)
        
        return keywords_to_scrape
    
    def _scrape_keyword(self, keyword_obj):
        """Update tracked products for a specific keyword"""
        logger.info(f"Starting automatic price update for keyword: {keyword_obj.keyword}")
        
        # Create scraping log entry
        scraping_log = ScrapingLog(
            keyword=keyword_obj.keyword,
            status='running'
        )
        db.session.add(scraping_log)
        db.session.commit()
        
        try:
            # Get tracked products for this keyword
            tracked_products = Product.query.filter(
                Product.is_tracked == True,
                Product.is_active == True,
                Product.title.ilike(f'%{keyword_obj.keyword}%')
            ).all()
            
            if not tracked_products:
                logger.info(f"No tracked products found for keyword: {keyword_obj.keyword}")
                scraping_log.status = 'completed'
                scraping_log.finished_at = datetime.utcnow()
                scraping_log.products_found = 0
                db.session.commit()
                return
            
            logger.info(f"Found {len(tracked_products)} tracked products for keyword: {keyword_obj.keyword}")
            
            # For discovery: also scrape new products occasionally
            update_count = 0
            if keyword_obj.scrape_for_discovery:
                logger.info(f"Also discovering new products for keyword: {keyword_obj.keyword}")
                
                # Initialize session
                cookies, user_agent = initialize_session_data(keyword_obj.keyword, log_callback=logger.info)
                
                # Scrape data (limit to 2 pages for discovery)
                raw_products = scrape_aliexpress_data(
                    keyword=keyword_obj.keyword,
                    max_pages=2,
                    cookies=cookies,
                    user_agent=user_agent,
                    delay=3.0,  # Use longer delay for automatic scraping
                    log_callback=logger.info
                )
                
                # Extract all available fields for automatic scraping
                all_fields = [
                    'Product ID', 'Title', 'Sale Price', 'Original Price', 'Discount (%)',
                    'Currency', 'Rating', 'Orders Count', 'Store Name', 'Store ID',
                    'Store URL', 'Product URL', 'Image URL'
                ]
                
                extracted_data = extract_product_details(raw_products, all_fields, log_callback=logger.info)
                
                # Save to database (only updates price history for tracked products)
                update_count = save_results_to_database(keyword_obj.keyword, extracted_data, log_callback=logger.info, track_products=False)
            else:
                logger.info(f"Only updating existing tracked products for keyword: {keyword_obj.keyword}")
                
                # For tracked products only: scrape their specific pages for price updates
                # This would require individual product page scraping which is more complex
                # For now, we'll rely on the discovery scraping to update tracked products
                update_count = len(tracked_products)
            
            # Update keyword last scraped time
            keyword_obj.last_scraped = datetime.utcnow()
            
            # Update scraping log
            scraping_log.status = 'completed'
            scraping_log.finished_at = datetime.utcnow()
            scraping_log.products_found = update_count
            
            db.session.commit()
            
            logger.info(f"Completed automatic update for keyword: {keyword_obj.keyword}, updated {update_count} products")
            
        except Exception as e:
            logger.error(f"Error updating keyword {keyword_obj.keyword}: {e}")
            
            # Update scraping log with error
            scraping_log.status = 'failed'
            scraping_log.finished_at = datetime.utcnow()
            scraping_log.error_message = str(e)
            
            db.session.commit()

# Global auto-scraper instance
auto_scraper = None

def init_auto_scraper(app):
    """Initialize the auto-scraper with the Flask app"""
    global auto_scraper
    auto_scraper = AutoScraper(app)
    return auto_scraper

def start_auto_scraper():
    """Start the auto-scraper"""
    global auto_scraper
    if auto_scraper:
        auto_scraper.start()

def stop_auto_scraper():
    """Stop the auto-scraper"""
    global auto_scraper
    if auto_scraper:
        auto_scraper.stop()