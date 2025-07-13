from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import json

db = SQLAlchemy()

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.String(50), nullable=False, index=True)  # Main product ID
    sku_id = db.Column(db.String(50), unique=True, nullable=False, index=True)  # Unique SKU for each variant
    spu_id = db.Column(db.String(50), index=True)  # AliExpress SPU identifier for grouping variants
    title = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    variant_title = db.Column(db.String(500))  # Extracted variant specification (e.g., "N100", "N150")
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
            'sku_id': self.sku_id,
            'spu_id': self.spu_id,
            'title': self.title,
            'description': self.description,
            'variant_title': self.variant_title,
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
    
    def get_variants(self):
        """Get all variants of this product (products with same product_id but different SKU)"""
        if not self.product_id:
            return []
        return Product.query.filter(
            Product.product_id == self.product_id,
            Product.is_active == True,
            Product.sku_id != self.sku_id  # Exclude self
        ).all()
    
    def get_all_variants_including_self(self):
        """Get all variants including this product"""
        if not self.product_id:
            return [self]
        return Product.query.filter(
            Product.product_id == self.product_id,
            Product.is_active == True
        ).order_by(Product.variant_title).all()
    
    def get_related_variants(self):
        """Get related products that could be variants based on similar titles and different specifications"""
        base_title = self.get_base_title()
        
        # If we have SPU grouping, use that first
        if self.spu_id:
            return Product.query.filter_by(spu_id=self.spu_id, is_active=True).all()
        
        # Otherwise, find products with similar base titles but different variants
        # Use the brand name and product type for matching
        title_words = base_title.split()
        
        # Look for brand name (usually first word) and product type
        brand = title_words[0] if title_words else ""
        
        # For JAYO products, look for other JAYO filament products
        if brand.upper() == "JAYO":
            search_terms = ["JAYO", "Filament", "PLA", "PETG", "3D"]
        else:
            # Use first 2-3 key words
            search_terms = title_words[:3]
        
        # Find products that contain the key terms
        related_products = []
        
        for term in search_terms:
            if len(term) > 2:  # Skip very short words
                products = Product.query.filter(
                    Product.title.contains(term),
                    Product.is_active == True,
                    Product.id != self.id  # Exclude self
                ).limit(15).all()
                related_products.extend(products)
        
        # Remove duplicates
        seen_ids = set()
        unique_products = []
        for product in related_products:
            if product.id not in seen_ids:
                seen_ids.add(product.id)
                unique_products.append(product)
        
        # Filter to only include products that seem to be actual variants
        variants = []
        
        for product in unique_products:
            # Check if it's likely a variant:
            # 1. Same store (if available) - but allow different stores for JAYO
            if (self.store_id and product.store_id and 
                self.store_id != product.store_id and 
                brand.upper() != "JAYO"):
                continue
                
            # 2. Similar product category (check for common keywords)
            common_keywords = ["PLA", "PETG", "ABS", "TPU", "Filament", "3D", "Drucker"]
            self_keywords = [word.upper() for word in base_title.split() if word.upper() in common_keywords]
            product_keywords = [word.upper() for word in product.title.split() if word.upper() in common_keywords]
            
            # Must have at least 2 keywords in common
            if len(set(self_keywords) & set(product_keywords)) >= 2:
                variants.append(product)
        
        # Always include self at the beginning
        if self not in variants:
            variants.insert(0, self)
        
        # Sort by variant title for better organization, then by ID
        variants.sort(key=lambda x: (x.variant_title or 'ZZZZ', x.id))
        
        return variants[:12]  # Limit to 12 variants for UI purposes
    
    def get_base_title(self):
        """Get the base product title without variant specifications"""
        if not self.variant_title:
            return self.title
        # Remove variant specification from title
        return self.title.replace(self.variant_title, '').strip()

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