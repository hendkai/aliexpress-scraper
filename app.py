from flask import Flask, render_template, request, Response, stream_with_context, jsonify, redirect, url_for
import os
import json
from models import db, Product, PriceHistory, SearchKeyword, ScrapingLog
from datetime import datetime, timedelta
from scheduler import init_auto_scraper, start_auto_scraper
from sqlalchemy import func, desc

ALL_POSSIBLE_FIELDS = [
    'Product ID', 'Title', 'Sale Price', 'Original Price', 'Discount (%)',
    'Currency', 'Rating', 'Orders Count', 'Store Name', 'Store ID',
    'Store URL', 'Product URL', 'Image URL'
]

try:
    from scraper import run_scrape_job
except ImportError:
    print("Error: Could not import functions from scraper.py.")
    print("Make sure scraper.py is in the same directory as app.py.")
    exit()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///aliexpress_scraper.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

# Initialize auto-scraper
auto_scraper = init_auto_scraper(app)

# Create tables
with app.app_context():
    db.create_all()
    start_auto_scraper()

@app.route('/', methods=['GET'])
def index():
    # Get recent products for display
    recent_products = Product.query.filter_by(is_active=True).order_by(desc(Product.updated_at)).limit(12).all()
    return render_template('index.html', recent_products=recent_products)

@app.route('/tracked')
def tracked_products():
    # Get all tracked products
    tracked_products = Product.query.filter_by(is_tracked=True, is_active=True).order_by(desc(Product.updated_at)).all()
    return render_template('tracked.html', products=tracked_products)

@app.route('/search', methods=['GET', 'POST'])
def search_products():
    if request.method == 'POST':
        query = request.form.get('query', '')
    else:
        query = request.args.get('q', '')
    
    products = []
    if query:
        # Search in product titles
        products = Product.query.filter(
            Product.title.ilike(f'%{query}%'),
            Product.is_active == True
        ).order_by(desc(Product.updated_at)).limit(50).all()
    
    return render_template('search.html', products=products, query=query)

@app.route('/browse')
def browse_products():
    """Browse all products with filtering and sorting options"""
    # Get filter parameters
    category = request.args.get('category', '')
    store = request.args.get('store', '')
    tracked_only = request.args.get('tracked_only', 'false') == 'true'
    sort_by = request.args.get('sort', 'updated_at')
    order = request.args.get('order', 'desc')
    page = request.args.get('page', 1, type=int)
    per_page = 24  # Grid layout works well with 24 items per page
    
    # Start with base query
    query = Product.query.filter_by(is_active=True)
    
    # Apply filters
    if tracked_only:
        query = query.filter_by(is_tracked=True)
    
    if category:
        # Search for category in title (broad matching)
        query = query.filter(Product.title.ilike(f'%{category}%'))
    
    if store:
        query = query.filter(Product.store_name.ilike(f'%{store}%'))
    
    # Apply sorting
    if sort_by == 'price':
        # Sort by most recent price from price history
        from sqlalchemy import func
        subquery = db.session.query(
            PriceHistory.product_id,
            func.max(PriceHistory.timestamp).label('max_timestamp')
        ).group_by(PriceHistory.product_id).subquery()
        
        latest_prices = db.session.query(
            PriceHistory.product_id,
            PriceHistory.sale_price
        ).join(
            subquery,
            (PriceHistory.product_id == subquery.c.product_id) &
            (PriceHistory.timestamp == subquery.c.max_timestamp)
        ).subquery()
        
        query = query.outerjoin(latest_prices, Product.id == latest_prices.c.product_id)
        if order == 'desc':
            query = query.order_by(desc(latest_prices.c.sale_price), desc(Product.updated_at))
        else:
            query = query.order_by(latest_prices.c.sale_price.asc(), desc(Product.updated_at))
    elif sort_by == 'rating':
        if order == 'desc':
            query = query.order_by(desc(Product.rating), desc(Product.updated_at))
        else:
            query = query.order_by(Product.rating.asc(), desc(Product.updated_at))
    elif sort_by == 'orders':
        if order == 'desc':
            query = query.order_by(desc(Product.orders_count), desc(Product.updated_at))
        else:
            query = query.order_by(Product.orders_count.asc(), desc(Product.updated_at))
    else:  # Default: updated_at
        if order == 'desc':
            query = query.order_by(desc(Product.updated_at))
        else:
            query = query.order_by(Product.updated_at.asc())
    
    # Paginate results
    products = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get filter options for dropdowns
    categories = db.session.query(Product.title).filter_by(is_active=True).all()
    category_keywords = set()
    for prod in categories:
        if prod.title:
            words = prod.title.split()[:3]  # First 3 words as category hints
            category_keywords.update(word for word in words if len(word) > 3)
    
    stores = db.session.query(Product.store_name).filter(
        Product.store_name.isnot(None),
        Product.is_active == True
    ).distinct().all()
    
    filter_options = {
        'categories': sorted(list(category_keywords))[:20],  # Top 20 categories
        'stores': [store[0] for store in stores if store[0]][:20]  # Top 20 stores
    }
    
    return render_template('browse.html', 
                         products=products, 
                         filter_options=filter_options,
                         current_filters={
                             'category': category,
                             'store': store,
                             'tracked_only': tracked_only,
                             'sort': sort_by,
                             'order': order
                         })

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    
    # Get price history for the last 30 days (only if tracked)
    price_data = []
    if product.is_tracked:
        price_history = product.get_price_history(days=30)
        for price in price_history:
            price_data.append({
                'date': price.timestamp.strftime('%Y-%m-%d %H:%M'),
                'sale_price': price.sale_price,
                'original_price': price.original_price,
                'discount': price.discount_percentage
            })
    
    # Get all related variants for this product
    related_variants = Product.query.filter_by(product_id=product.product_id, is_active=True).all()
    
    return render_template('product_detail.html', product=product, price_history=price_data, related_variants=related_variants)

@app.route('/debug/product/<int:product_id>')
def debug_product_variants(product_id):
    """Debug route to check variant data"""
    product = Product.query.get_or_404(product_id)
    related_variants = Product.query.filter_by(product_id=product.product_id, is_active=True).all()
    
    debug_info = {
        'product_id': product_id,
        'product_title': product.title,
        'product_id_field': product.product_id,
        'total_variants': len(related_variants),
        'variants': []
    }
    
    for variant in related_variants:
        debug_info['variants'].append({
            'id': variant.id,
            'title': variant.variant_title or 'Original',
            'is_active': variant.is_active,
            'is_tracked': variant.is_tracked
        })
    
    return jsonify(debug_info)

@app.route('/product/<int:product_id>/toggle_tracking', methods=['POST'])
def toggle_product_tracking(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        
        # Get all variants of this product (same product_id)
        all_variants = Product.query.filter_by(product_id=product.product_id).all()
        
        if product.is_tracked:
            # Stop tracking all variants
            for variant in all_variants:
                variant.is_tracked = False
                variant.tracked_since = None
            message = f'Stopped tracking {len(all_variants)} variants'
        else:
            # Start tracking all variants
            for variant in all_variants:
                variant.is_tracked = True
                variant.tracked_since = datetime.utcnow()
            message = f'Started tracking {len(all_variants)} variants'
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'is_tracked': product.is_tracked,
            'message': message
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error updating tracking status: {str(e)}'
        }), 500

@app.route('/scrape_results')
def scrape_results():
    # Show all products from recent scraping sessions for selection
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Get products that are not tracked yet, grouped by SPU to show variants together
    # First, get all non-tracked products
    all_products = Product.query.filter_by(is_active=True, is_tracked=False).order_by(desc(Product.updated_at)).all()
    
    # Group products by SPU ID to identify variants
    spu_groups = {}
    standalone_products = []
    
    for product in all_products:
        if product.spu_id:
            if product.spu_id not in spu_groups:
                spu_groups[product.spu_id] = []
            spu_groups[product.spu_id].append(product)
        else:
            standalone_products.append(product)
    
    # Combine grouped and standalone products
    products_display = []
    
    # Add grouped products (show all variants together)
    for spu_id, variants in spu_groups.items():
        # Sort variants by variant title
        variants.sort(key=lambda x: x.variant_title or '')
        products_display.extend(variants)
    
    # Add standalone products
    products_display.extend(standalone_products)
    
    # Implement pagination manually
    total = len(products_display)
    start = (page - 1) * per_page
    end = start + per_page
    products_page = products_display[start:end]
    
    # Create a pagination-like object
    class Pagination:
        def __init__(self, items, page, per_page, total):
            self.items = items
            self.page = page
            self.per_page = per_page
            self.total = total
            self.pages = (total + per_page - 1) // per_page
            self.has_prev = page > 1
            self.has_next = page < self.pages
            self.prev_num = page - 1 if self.has_prev else None
            self.next_num = page + 1 if self.has_next else None
        
        def iter_pages(self):
            for num in range(1, self.pages + 1):
                if num <= 3 or num > self.pages - 3 or abs(num - self.page) <= 2:
                    yield num
                elif abs(num - self.page) == 3:
                    yield None
    
    products = Pagination(products_page, page, per_page, total)
    
    return render_template('scrape_results.html', products=products, spu_groups=spu_groups)

@app.route('/product/<int:product_id>/variants')
def product_variants(product_id):
    # Show all variants of a product for selection
    product = Product.query.get_or_404(product_id)
    variants = product.get_all_variants_including_self()
    
    return render_template('product_variants.html', product=product, variants=variants)

@app.route('/keywords')
def manage_keywords():
    keywords = SearchKeyword.query.all()
    return render_template('keywords.html', keywords=keywords)

@app.route('/keywords/add', methods=['POST'])
def add_keyword():
    keyword = request.form.get('keyword')
    frequency = request.form.get('frequency', 24, type=int)
    
    if keyword:
        existing = SearchKeyword.query.filter_by(keyword=keyword).first()
        if not existing:
            new_keyword = SearchKeyword(
                keyword=keyword,
                scrape_frequency_hours=frequency
            )
            db.session.add(new_keyword)
            db.session.commit()
    
    return redirect(url_for('manage_keywords'))

@app.route('/keywords/<int:keyword_id>/toggle', methods=['POST'])
def toggle_keyword(keyword_id):
    keyword = SearchKeyword.query.get_or_404(keyword_id)
    keyword.is_active = not keyword.is_active
    db.session.commit()
    return redirect(url_for('manage_keywords'))

@app.route('/keywords/<int:keyword_id>/delete', methods=['POST'])
def delete_keyword(keyword_id):
    keyword = SearchKeyword.query.get_or_404(keyword_id)
    db.session.delete(keyword)
    db.session.commit()
    return redirect(url_for('manage_keywords'))

@app.route('/logs')
def scraping_logs():
    logs = ScrapingLog.query.order_by(desc(ScrapingLog.started_at)).limit(50).all()
    return render_template('logs.html', logs=logs)

@app.route('/api/products')
def api_products():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '')
    
    query = Product.query.filter_by(is_active=True)
    
    if search:
        query = query.filter(Product.title.ilike(f'%{search}%'))
    
    products = query.order_by(desc(Product.updated_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'products': [p.to_dict() for p in products.items],
        'total': products.total,
        'pages': products.pages,
        'current_page': page
    })

@app.route('/api/product/<int:product_id>/price_history')
def api_price_history(product_id):
    days = request.args.get('days', 30, type=int)
    product = Product.query.get_or_404(product_id)
    
    price_history = product.get_price_history(days=days)
    
    return jsonify([p.to_dict() for p in price_history])

@app.route('/api/product/<int:product_id>/track', methods=['POST'])
def api_track_product(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        
        # Get all variants of this product (same product_id)
        all_variants = Product.query.filter_by(product_id=product.product_id).all()
        
        if not product.is_tracked:
            # Start tracking all variants
            for variant in all_variants:
                variant.is_tracked = True
                variant.tracked_since = datetime.utcnow()
            message = f"Started tracking {len(all_variants)} variants"
        else:
            message = "Product variants are already being tracked"
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'is_tracked': product.is_tracked,
            'message': message
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error updating tracking status: {str(e)}'
        }), 500

@app.route('/api/product/<int:product_id>/scrape_variants', methods=['POST'])
def api_scrape_variants(product_id):
    """Scrape real product variants from AliExpress API"""
    product = Product.query.get_or_404(product_id)
    
    try:
        from scraper import scrape_real_product_variants, scrape_html_variants, scrape_enhanced_variants, save_results_to_database
        
        # Extract main product ID from product_id field
        main_product_id = product.product_id
        if not main_product_id:
            return jsonify({
                'success': False,
                'message': 'Product has no valid AliExpress product ID'
            })
        
        # Try API-based variant scraping first
        variants_data = scrape_real_product_variants(main_product_id)
        
        # If API scraping fails, try enhanced variant detection (handles data-sku-col)
        if not variants_data and product.product_url:
            enhanced_variants = scrape_enhanced_variants(product.product_url, product_title=product.title)
            if enhanced_variants:
                # Convert enhanced variants to the same format as API variants
                variants_data = []
                for variant in enhanced_variants:
                    variants_data.append({
                        'product_id': main_product_id,
                        'sku_id': variant.get('sku_id', f"{main_product_id}_enhanced_{len(variants_data)}"),
                        'variant_title': variant.get('variant_title'),
                        'image_url': variant.get('image_url'),
                        'sale_price': variant.get('sale_price'),
                        'original_price': variant.get('original_price'),
                        'source': 'enhanced_sku_col'
                    })
        
        # If enhanced method fails, try HTML-based variant detection
        if not variants_data and product.product_url:
            # Pass product title for better variant detection
            html_variants = scrape_html_variants(product.product_url, product_title=product.title)
            if html_variants:
                # Convert HTML variants to the same format as API variants
                variants_data = []
                for variant in html_variants:
                    variants_data.append({
                        'product_id': main_product_id,
                        'sku_id': variant.get('sku_id', f"{main_product_id}_html_{len(variants_data)}"),
                        'variant_title': variant.get('variant_title'),
                        'image_url': variant.get('image_url'),
                        'sale_price': None,  # HTML variants may not have price data
                        'original_price': None,
                        'discount_percentage': None
                    })
        
        if not variants_data:
            return jsonify({
                'success': False,
                'message': 'No variants found using either API or HTML detection methods. This might be a single-variant product.'
            })
        
        # Save variants to database
        saved_count = 0
        updated_count = 0
        
        for variant_data in variants_data:
            # Check if this SKU already exists
            existing_variant = Product.query.filter_by(sku_id=variant_data['sku_id']).first()
            
            if existing_variant:
                # Update existing variant
                existing_variant.variant_title = variant_data.get('variant_title')
                existing_variant.image_url = variant_data.get('image_url', existing_variant.image_url)
                existing_variant.updated_at = datetime.utcnow()
                updated_count += 1
                variant_product = existing_variant
            else:
                # Create new variant
                variant_product = Product(
                    product_id=variant_data['product_id'],
                    sku_id=variant_data['sku_id'], 
                    title=product.title,  # Same base title
                    variant_title=variant_data.get('variant_title'),
                    image_url=variant_data.get('image_url'),
                    product_url=f"https://www.aliexpress.com/item/{variant_data['product_id']}.html",
                    store_name=product.store_name,
                    store_id=product.store_id,
                    store_url=product.store_url,
                    currency=product.currency,
                    rating=product.rating,
                    orders_count=product.orders_count
                )
                db.session.add(variant_product)
                saved_count += 1
            
            # Add price history for variant
            if variant_data.get('sale_price'):
                from scraper import parse_price_string
                
                # Use the improved price parsing function
                sale_price = variant_data['sale_price']
                if isinstance(sale_price, str):
                    sale_price = parse_price_string(sale_price)
                else:
                    sale_price = float(sale_price) if sale_price else None
                
                original_price = variant_data.get('original_price')
                if isinstance(original_price, str):
                    original_price = parse_price_string(original_price)
                elif original_price:
                    original_price = float(original_price)
                else:
                    original_price = sale_price
                    
                discount = variant_data.get('discount_percentage')
                
                # Flush to get ID for new products
                db.session.flush()
                
                price_history = PriceHistory(
                    product_id=variant_product.id,
                    sale_price=sale_price,
                    original_price=original_price,
                    discount_percentage=discount
                )
                db.session.add(price_history)
        
        db.session.commit()
        
        # Determine which method was used
        detection_method = "API"
        if variants_data and any(v.get('sku_id', '').startswith(f"{main_product_id}_html_") for v in variants_data):
            detection_method = "HTML page analysis"
        
        return jsonify({
            'success': True,
            'message': f'Successfully found {len(variants_data)} variants using {detection_method} ({saved_count} new, {updated_count} updated)',
            'variants_found': len(variants_data),
            'new_variants': saved_count,
            'updated_variants': updated_count,
            'detection_method': detection_method
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error scraping variants: {str(e)}'
        }), 500

@app.route('/stream-variant-scrape/<int:product_id>')
def stream_variant_scrape(product_id):
    """Stream variant scraping progress in real-time"""
    def generate():
        import time
        import json
        
        def send_data(data):
            """Helper to send properly formatted SSE data"""
            yield f"data: {json.dumps(data)}\n\n"
        
        def send_heartbeat():
            """Send heartbeat to keep connection alive"""
            yield ": heartbeat\n\n"
        
        try:
            product = Product.query.get_or_404(product_id)
            
            yield from send_data({
                'status': 'started', 
                'message': f'Starting variant scraping for {product.title[:50]}...'
            })
            
            from scraper import scrape_real_product_variants, scrape_enhanced_variants, scrape_interactive_variants, save_results_to_database
            
            # Extract main product ID from product_id field
            main_product_id = product.product_id
            if not main_product_id:
                yield from send_data({
                    'status': 'error', 
                    'message': 'Product has no valid AliExpress product ID'
                })
                return
            
            yield from send_data({
                'status': 'progress', 
                'message': 'Trying API-based variant detection...', 
                'step': 1, 
                'total': 4
            })
            
            # Send heartbeat before potentially long operation
            yield from send_heartbeat()
            
            # Try API-based variant scraping first
            variants_data = scrape_real_product_variants(main_product_id, log_callback=lambda msg: None)
            
            # Send heartbeat after operation
            yield from send_heartbeat()
            
            if variants_data and len(variants_data) > 0:
                yield from send_data({
                    'status': 'progress', 
                    'message': f'Found {len(variants_data)} variants via API', 
                    'step': 4, 
                    'total': 4
                })
            else:
                yield from send_data({
                    'status': 'progress', 
                    'message': 'API method found no variants, trying enhanced detection...', 
                    'step': 2, 
                    'total': 4
                })
                
                # Send heartbeat before next operation
                yield from send_heartbeat()
                
                # Try enhanced variant detection
                if product.product_url:
                    enhanced_variants = scrape_enhanced_variants(
                        product.product_url, 
                        log_callback=lambda msg: None,
                        product_title=product.title
                    )
                    
                    # Send heartbeat after operation
                    yield from send_heartbeat()
                    
                    if enhanced_variants and len(enhanced_variants) > 0:
                        yield from send_data({
                            'status': 'progress', 
                            'message': f'Found {len(enhanced_variants)} variants via enhanced detection', 
                            'step': 4, 
                            'total': 4
                        })
                        # Convert enhanced variants to the same format as API variants
                        variants_data = []
                        for variant in enhanced_variants:
                            variants_data.append({
                                'product_id': main_product_id,
                                'sku_id': variant.get('sku_id', f"{main_product_id}_enhanced_{len(variants_data)}"),
                                'variant_title': variant.get('variant_title'),
                                'image_url': variant.get('image_url'),
                                'sale_price': variant.get('sale_price'),
                                'original_price': variant.get('original_price'),
                                'source': 'enhanced_sku_col'
                            })
                    else:
                        yield from send_data({
                            'status': 'progress', 
                            'message': 'Enhanced method found no variants, trying interactive detection...', 
                            'step': 3, 
                            'total': 4
                        })
                        
                        # Send heartbeat before next operation
                        yield from send_heartbeat()
                        
                        # Try interactive variant detection
                        interactive_variants = scrape_interactive_variants(
                            product.product_url, 
                            log_callback=lambda msg: None,
                            product_title=product.title
                        )
                        
                        # Send heartbeat after operation
                        yield from send_heartbeat()
                        
                        if interactive_variants and len(interactive_variants) > 0:
                            yield from send_data({
                                'status': 'progress', 
                                'message': f'Found {len(interactive_variants)} variants via interactive detection', 
                                'step': 4, 
                                'total': 4
                            })
                            # Convert interactive variants to the same format as API variants
                            variants_data = []
                            for variant in interactive_variants:
                                variants_data.append({
                                    'product_id': main_product_id,
                                    'sku_id': variant.get('sku_id', f"{main_product_id}_interactive_{len(variants_data)}"),
                                    'variant_title': variant.get('variant_title'),
                                    'image_url': variant.get('image_url'),
                                    'sale_price': variant.get('sale_price'),
                                    'original_price': variant.get('original_price'),
                                    'source': 'interactive'
                                })
                        else:
                            yield from send_data({
                                'status': 'progress', 
                                'message': 'No variants found with any method', 
                                'step': 4, 
                                'total': 4
                            })
                            variants_data = []
            
            # Save variants to database
            if variants_data:
                yield from send_data({
                    'status': 'progress', 
                    'message': f'Saving {len(variants_data)} variants to database...'
                })
                
                # Send heartbeat before database operation
                yield from send_heartbeat()
                
                # Convert to format expected by save_results_to_database
                formatted_data = []
                for variant_data in variants_data:
                    formatted_variant = {
                        'Product ID': variant_data.get('product_id'),
                        'SKU ID': variant_data.get('sku_id'),
                        'Title': product.title,
                        'Variant Title': variant_data.get('variant_title'),
                        'Image URL': variant_data.get('image_url'),
                        'Sale Price': variant_data.get('sale_price'),
                        'Original Price': variant_data.get('original_price'),
                        'Product URL': product.product_url,
                        'Currency': product.currency,
                        'Rating': product.rating,
                        'Orders Count': product.orders_count,
                        'Store Name': product.store_name,
                        'Store ID': product.store_id,
                        'Store URL': product.store_url
                    }
                    formatted_data.append(formatted_variant)
                
                saved_count = save_results_to_database(f"variants_{main_product_id}", formatted_data)
                
                yield from send_data({
                    'status': 'completed', 
                    'message': f'Successfully saved {saved_count} variants!', 
                    'variants_found': len(variants_data), 
                    'variants_saved': saved_count
                })
            else:
                yield from send_data({
                    'status': 'completed', 
                    'message': 'No variants found for this product', 
                    'variants_found': 0, 
                    'variants_saved': 0
                })
                
        except Exception as e:
            yield from send_data({
                'status': 'error', 
                'message': f'Error during variant scraping: {str(e)}'
            })
    
    # Set proper SSE headers
    response = Response(stream_with_context(generate()), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Connection'] = 'keep-alive'
    response.headers['X-Accel-Buffering'] = 'no'  # Disable nginx buffering
    return response

@app.route('/api/product/<int:product_id>/update', methods=['POST'])
def api_update_product(product_id):
    """Update a single product and automatically find & track all variants"""
    product = Product.query.get_or_404(product_id)
    
    try:
        from scraper import scrape_real_product_variants, scrape_html_variants, scrape_enhanced_variants, save_results_to_database
        
        # Extract main product ID from product_id field
        main_product_id = product.product_id
        if not main_product_id:
            return jsonify({
                'success': False,
                'message': 'Product has no valid AliExpress product ID'
            })
        
        # Try API-based variant scraping first
        variants_data = scrape_real_product_variants(main_product_id)
        
        # If API scraping fails or finds no variants, try enhanced variant detection first
        if (not variants_data or len(variants_data) == 0) and product.product_url:
            enhanced_variants = scrape_enhanced_variants(product.product_url, product_title=product.title)
            if enhanced_variants:
                # Convert enhanced variants to the same format as API variants
                variants_data = []
                for variant in enhanced_variants:
                    variants_data.append({
                        'product_id': main_product_id,
                        'sku_id': variant.get('sku_id', f"{main_product_id}_enhanced_{len(variants_data)}"),
                        'variant_title': variant.get('variant_title'),
                        'image_url': variant.get('image_url'),
                        'sale_price': variant.get('sale_price'),
                        'original_price': variant.get('original_price'),
                        'source': 'enhanced_sku_col'
                    })
        
        # If enhanced method fails, try interactive variant detection
        if (not variants_data or len(variants_data) == 0) and product.product_url:
            from scraper import scrape_interactive_variants
            interactive_variants = scrape_interactive_variants(product.product_url, product_title=product.title)
            if interactive_variants:
                # Convert interactive variants to the same format as API variants
                variants_data = []
                for variant in interactive_variants:
                    variants_data.append({
                        'product_id': main_product_id,
                        'sku_id': variant.get('sku_id', f"{main_product_id}_interactive_{len(variants_data)}"),
                        'variant_title': variant.get('variant_title'),
                        'image_url': variant.get('image_url'),
                        'sale_price': variant.get('sale_price'),
                        'original_price': variant.get('original_price'),
                        'discount_percentage': None  # Could calculate from prices if needed
                    })
        
        saved_count = 0
        updated_count = 0
        tracked_count = 0
        
        if variants_data:
            # Save variants to database and automatically track them
            for variant_data in variants_data:
                # Check if this SKU already exists
                existing_variant = Product.query.filter_by(sku_id=variant_data['sku_id']).first()
                
                if existing_variant:
                    # Update existing variant
                    existing_variant.variant_title = variant_data.get('variant_title')
                    existing_variant.image_url = variant_data.get('image_url', existing_variant.image_url)
                    existing_variant.updated_at = datetime.utcnow()
                    updated_count += 1
                    variant_product = existing_variant
                else:
                    # Create new variant
                    variant_product = Product(
                        product_id=variant_data['product_id'],
                        sku_id=variant_data['sku_id'], 
                        title=product.title,  # Same base title
                        variant_title=variant_data.get('variant_title'),
                        image_url=variant_data.get('image_url'),
                        product_url=f"https://www.aliexpress.com/item/{variant_data['product_id']}.html",
                        store_name=product.store_name,
                        store_id=product.store_id,
                        store_url=product.store_url,
                        currency=product.currency,
                        rating=product.rating,
                        orders_count=product.orders_count
                    )
                    db.session.add(variant_product)
                    saved_count += 1
                
                # Automatically track all variants
                if not variant_product.is_tracked:
                    variant_product.start_tracking()
                    tracked_count += 1
                
                # Add price history for variants with prices
                if variant_data.get('sale_price'):
                    from scraper import parse_price_string
                    
                    # Parse the sale price
                    sale_price = variant_data['sale_price']
                    if isinstance(sale_price, str):
                        sale_price = parse_price_string(sale_price)
                    else:
                        sale_price = float(sale_price) if sale_price else None
                    
                    # Parse the original price
                    original_price = variant_data.get('original_price')
                    if isinstance(original_price, str):
                        original_price = parse_price_string(original_price)
                    elif original_price:
                        original_price = float(original_price)
                    else:
                        original_price = sale_price
                    
                    # Calculate discount if both prices are available
                    discount = None
                    if sale_price and original_price and original_price > sale_price:
                        discount = round(((original_price - sale_price) / original_price) * 100, 1)
                    
                    # Flush to get ID for new products
                    db.session.flush()
                    
                    # Add price history entry
                    price_history = PriceHistory(
                        product_id=variant_product.id,
                        sale_price=sale_price,
                        original_price=original_price,
                        discount_percentage=discount
                    )
                    db.session.add(price_history)
        
        # Also ensure the original product is tracked
        if not product.is_tracked:
            product.start_tracking()
            tracked_count += 1
        
        db.session.commit()
        
        # Determine which method was used
        detection_method = "API"
        if variants_data and any(v.get('sku_id', '').startswith(f"{main_product_id}_interactive_") for v in variants_data):
            detection_method = "Interactive variant navigation"
        elif variants_data and any(v.get('sku_id', '').startswith(f"{main_product_id}_html_") for v in variants_data):
            detection_method = "HTML page analysis"
        
        message = f'Found {len(variants_data) if variants_data else 0} variants using {detection_method}. '
        message += f'{saved_count} new, {updated_count} updated, {tracked_count} now being tracked.'
        
        return jsonify({
            'success': True,
            'message': message,
            'variants_found': len(variants_data) if variants_data else 0,
            'new_variants': saved_count,
            'updated_variants': updated_count,
            'tracked_count': tracked_count,
            'detection_method': detection_method
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error updating product: {str(e)}'
        }), 500

@app.route('/api/products/update_all', methods=['POST'])
def api_update_all_products():
    """Update all products by re-scraping them"""
    try:
        # Get all unique search terms from existing products
        products = Product.query.filter_by(is_active=True).all()
        search_terms = set()
        
        for product in products:
            base_title = product.get_base_title()
            search_term = ' '.join(base_title.split()[0:2])  # Use first 2 words
            search_terms.add(search_term)
        
        total_updated = 0
        
        with app.app_context():
            from scraper import run_scrape_job
            
            for search_term in list(search_terms)[:5]:  # Limit to first 5 to avoid long processing
                try:
                    # Run scrape for each search term
                    def collect_results():
                        results = []
                        for line in run_scrape_job(
                            keyword=search_term,
                            pages=1,
                            apply_discount=False,
                            free_shipping=False,
                            min_price=None,
                            max_price=None,
                            selected_fields=ALL_POSSIBLE_FIELDS,
                            delay=1.0,
                            track_products=False,
                            update_existing=True
                        ):
                            if line.startswith('data: '):
                                line = line[6:]
                            if not line.strip() or line.startswith('PROCESS_COMPLETE'):
                                continue
                            results.append(line)
                        return results
                    
                    results = collect_results()
                    total_updated += 1
                    
                except Exception as e:
                    print(f"Error updating {search_term}: {e}")
                    continue
        
        return jsonify({
            'success': True,
            'message': f'Updated {total_updated} product searches. Check for new variants.',
            'updated_searches': total_updated
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error updating products: {str(e)}'
        }), 500

# Route for streaming the scraping process
@app.route('/stream-scrape')
def stream_scrape():
    keyword = request.args.get('keyword', '')
    pages = request.args.get('pages', 1, type=int)
    min_price = request.args.get('min_price', type=float, default=None)
    max_price = request.args.get('max_price', type=float, default=None)
    apply_discount = request.args.get('apply_discount', 'false') == 'true'
    free_shipping = request.args.get('free_shipping', 'false') == 'true'
    selected_fields = request.args.getlist('fields')
    delay = request.args.get('delay', 1.0, type=float)  # Default 1 second

    if not keyword:
        def error_stream():
            yield "data: ERROR: Search product is required.\n\n"
            yield "data: PROCESS_COMPLETE\n\n"
        return Response(stream_with_context(error_stream()), mimetype='text/event-stream')

    if not selected_fields:
        def error_stream():
            yield "data: ERROR: Please select at least one output field.\n\n"
            yield "data: PROCESS_COMPLETE\n\n"
        return Response(stream_with_context(error_stream()), mimetype='text/event-stream')

    # Pass the current app context to the scraper
    def stream_with_app_context():
        with app.app_context():
            yield from run_scrape_job(
                keyword=keyword,
                pages=pages,
                apply_discount=apply_discount,
                free_shipping=free_shipping,
                min_price=min_price,
                max_price=max_price,
                selected_fields=selected_fields,
                delay=delay,  # Add delay parameter
                track_products=False  # Don't auto-track products from manual scraping
            )
    
    stream = stream_with_app_context()

    return Response(stream_with_context(stream), mimetype='text/event-stream')

@app.route('/settings')
def settings():
    """Settings and administration page"""
    # Get database statistics
    total_products = Product.query.filter_by(is_active=True).count()
    tracked_products = Product.query.filter_by(is_tracked=True, is_active=True).count()
    total_price_history = PriceHistory.query.count()
    total_keywords = SearchKeyword.query.filter_by(is_active=True).count()
    total_logs = ScrapingLog.query.count()
    
    # Get database file size if it exists
    import os
    db_file_path = 'aliexpress_scraper.db'
    db_size = 0
    if os.path.exists(db_file_path):
        db_size = os.path.getsize(db_file_path) / (1024 * 1024)  # Size in MB
    
    stats = {
        'total_products': total_products,
        'tracked_products': tracked_products,
        'total_price_history': total_price_history,
        'total_keywords': total_keywords,
        'total_logs': total_logs,
        'db_size': round(db_size, 2)
    }
    
    return render_template('settings.html', stats=stats)

@app.route('/api/settings/reset_database', methods=['POST'])
def api_reset_database():
    """Reset the entire database - DANGEROUS ACTION"""
    try:
        data = request.get_json()
        confirmation = data.get('confirmation', '')
        
        # Require exact confirmation phrase
        if confirmation != 'RESET ALL DATA':
            return jsonify({
                'success': False,
                'message': 'Invalid confirmation phrase. Type exactly: RESET ALL DATA'
            }), 400
        
        # Perform database reset
        db.drop_all()
        db.create_all()
        
        return jsonify({
            'success': True,
            'message': 'Database has been completely reset. All data has been deleted.'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error resetting database: {str(e)}'
        }), 500

@app.route('/api/settings/cleanup_old_data', methods=['POST'])
def api_cleanup_old_data():
    """Clean up old price history and inactive products"""
    try:
        # Remove price history older than 90 days
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        old_price_history = PriceHistory.query.filter(PriceHistory.timestamp < cutoff_date).count()
        PriceHistory.query.filter(PriceHistory.timestamp < cutoff_date).delete()
        
        # Remove inactive products (not tracked and older than 30 days)
        product_cutoff = datetime.utcnow() - timedelta(days=30)
        old_products = Product.query.filter(
            Product.is_tracked == False,
            Product.is_active == True,
            Product.updated_at < product_cutoff
        ).count()
        Product.query.filter(
            Product.is_tracked == False,
            Product.is_active == True,
            Product.updated_at < product_cutoff
        ).update({Product.is_active: False})
        
        # Remove old scraping logs (older than 60 days)
        log_cutoff = datetime.utcnow() - timedelta(days=60)
        old_logs = ScrapingLog.query.filter(ScrapingLog.started_at < log_cutoff).count()
        ScrapingLog.query.filter(ScrapingLog.started_at < log_cutoff).delete()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Cleanup completed: {old_price_history} old price records, {old_products} inactive products, {old_logs} old logs removed.'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error during cleanup: {str(e)}'
        }), 500

@app.route('/api/settings/export_data', methods=['POST'])
def api_export_data():
    """Export all tracked products and their data"""
    try:
        import json
        from datetime import datetime
        
        # Get all tracked products with their price history
        tracked_products = Product.query.filter_by(is_tracked=True, is_active=True).all()
        
        export_data = {
            'export_date': datetime.utcnow().isoformat(),
            'total_products': len(tracked_products),
            'products': []
        }
        
        for product in tracked_products:
            price_history = product.get_price_history(days=365)  # Last year
            product_data = {
                'product_id': product.product_id,
                'sku_id': product.sku_id,
                'title': product.title,
                'variant_title': product.variant_title,
                'store_name': product.store_name,
                'currency': product.currency,
                'product_url': product.product_url,
                'tracked_since': product.tracked_since.isoformat() if product.tracked_since else None,
                'price_history': [ph.to_dict() for ph in price_history]
            }
            export_data['products'].append(product_data)
        
        # Save to file
        export_filename = f"aliexpress_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        export_path = os.path.join('results', export_filename)
        
        os.makedirs('results', exist_ok=True)
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True,
            'message': f'Data exported successfully to {export_filename}',
            'filename': export_filename,
            'products_exported': len(tracked_products)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error exporting data: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run(debug=True, threaded=True, host='0.0.0.0')