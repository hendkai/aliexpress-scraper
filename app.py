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
    
    return render_template('product_detail.html', product=product, price_history=price_data)

@app.route('/product/<int:product_id>/toggle_tracking', methods=['POST'])
def toggle_product_tracking(product_id):
    product = Product.query.get_or_404(product_id)
    
    if product.is_tracked:
        product.stop_tracking()
    else:
        product.start_tracking()
    
    return jsonify({
        'success': True,
        'is_tracked': product.is_tracked,
        'message': 'Product tracking started' if product.is_tracked else 'Product tracking stopped'
    })

@app.route('/scrape_results')
def scrape_results():
    # Show all products from recent scraping sessions for selection
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Get products that are not tracked yet, ordered by most recent
    products = Product.query.filter_by(is_active=True, is_tracked=False).order_by(desc(Product.updated_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('scrape_results.html', products=products)

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

if __name__ == '__main__':
    app.run(debug=True, threaded=True)