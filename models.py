from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import json

db = SQLAlchemy()

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    title = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.Text)
    product_url = db.Column(db.Text, nullable=False)
    store_name = db.Column(db.String(200))
    store_id = db.Column(db.String(50))
    store_url = db.Column(db.Text)
    currency = db.Column(db.String(10))
    rating = db.Column(db.Float)
    orders_count = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    is_tracked = db.Column(db.Boolean, default=False)  # User manually selected for tracking
    tracked_since = db.Column(db.DateTime)  # When user started tracking this product
    
    # Relationship to price history
    price_history = db.relationship('PriceHistory', backref='product', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Product {self.product_id}: {self.title[:50]}...>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'title': self.title,
            'description': self.description,
            'image_url': self.image_url,
            'product_url': self.product_url,
            'store_name': self.store_name,
            'store_id': self.store_id,
            'store_url': self.store_url,
            'currency': self.currency,
            'rating': self.rating,
            'orders_count': self.orders_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'is_tracked': self.is_tracked,
            'tracked_since': self.tracked_since.isoformat() if self.tracked_since else None
        }
    
    def get_current_price(self):
        """Get the most recent price for this product"""
        latest_price = PriceHistory.query.filter_by(product_id=self.id).order_by(PriceHistory.timestamp.desc()).first()
        return latest_price
    
    def get_price_history(self, days=30):
        """Get price history for the last N days"""
        since_date = datetime.utcnow() - timedelta(days=days)
        return PriceHistory.query.filter_by(product_id=self.id).filter(PriceHistory.timestamp >= since_date).order_by(PriceHistory.timestamp.asc()).all()
    
    def start_tracking(self):
        """Start tracking this product"""
        self.is_tracked = True
        self.tracked_since = datetime.utcnow()
        db.session.commit()
    
    def stop_tracking(self):
        """Stop tracking this product"""
        self.is_tracked = False
        self.tracked_since = None
        db.session.commit()

class PriceHistory(db.Model):
    __tablename__ = 'price_history'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    sale_price = db.Column(db.Float)
    original_price = db.Column(db.Float)
    discount_percentage = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<PriceHistory {self.product_id}: {self.sale_price} at {self.timestamp}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'sale_price': self.sale_price,
            'original_price': self.original_price,
            'discount_percentage': self.discount_percentage,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }

class SearchKeyword(db.Model):
    __tablename__ = 'search_keywords'
    
    id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(200), nullable=False, unique=True)
    is_active = db.Column(db.Boolean, default=True)
    scrape_frequency_hours = db.Column(db.Integer, default=24)  # How often to scrape tracked products
    last_scraped = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    scrape_for_discovery = db.Column(db.Boolean, default=True)  # Whether to scrape for new products
    track_frequency_hours = db.Column(db.Integer, default=6)  # How often to update tracked products
    
    def __repr__(self):
        return f'<SearchKeyword {self.keyword}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'keyword': self.keyword,
            'is_active': self.is_active,
            'scrape_frequency_hours': self.scrape_frequency_hours,
            'last_scraped': self.last_scraped.isoformat() if self.last_scraped else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class ScrapingLog(db.Model):
    __tablename__ = 'scraping_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(200), nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    finished_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='running')  # running, completed, failed
    products_found = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text)
    
    def __repr__(self):
        return f'<ScrapingLog {self.keyword}: {self.status}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'keyword': self.keyword,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
            'status': self.status,
            'products_found': self.products_found,
            'error_message': self.error_message
        }