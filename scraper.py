import time
import json
import os
import csv
from urllib.parse import quote_plus
from DrissionPage import WebPage, SessionPage, ChromiumOptions
import datetime
from typing import Generator
import threading
from queue import Queue
import time
from models import db, Product, PriceHistory, SearchKeyword, ScrapingLog
from datetime import datetime, timedelta
import re

API_URL = 'https://www.aliexpress.com/fn/search-pc/index'
RESULTS_DIR = "results"
SESSION_CACHE_FILE = "session_cache.json"
CACHE_EXPIRATION_SECONDS = 30 * 60

# --- Base Headers (User-Agent will be updated from browser or cache) ---
BASE_HEADERS = {
    'accept': '*/*',
    'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
    'bx-v': '2.5.28',
    'content-type': 'application/json;charset=UTF-8',
    'origin': 'https://www.aliexpress.com',
    'priority': 'u=1, i',
    'sec-ch-ua': '',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 ...',
}

def default_logger(message):
    print(message)

def parse_price_string(price_str):
    """
    Parse price string with proper handling of different decimal separators.
    Examples: '€ 19,49' -> 19.49, '$19.99' -> 19.99, '1.234,56' -> 1234.56
    """
    if not price_str:
        return None
    
    # Remove currency symbols and extra spaces
    cleaned = price_str.strip().replace('€', '').replace('$', '').replace('£', '').replace('¥', '').strip()
    
    # Handle different decimal separator patterns
    if ',' in cleaned and '.' in cleaned:
        # Pattern: 1.234,56 (European style with thousands separator)
        if cleaned.rfind(',') > cleaned.rfind('.'):
            # Comma is the decimal separator
            cleaned = cleaned.replace('.', '').replace(',', '.')
        else:
            # Period is the decimal separator  
            cleaned = cleaned.replace(',', '')
    elif ',' in cleaned:
        # Only comma present - could be decimal or thousands separator
        parts = cleaned.split(',')
        if len(parts) == 2 and len(parts[1]) <= 2:
            # Likely decimal separator (e.g., "19,49")
            cleaned = cleaned.replace(',', '.')
        else:
            # Likely thousands separator (e.g., "1,234")
            cleaned = cleaned.replace(',', '')
    
    # Remove any remaining spaces
    cleaned = cleaned.replace(' ', '')
    
    try:
        return float(cleaned)
    except ValueError:
        return None

def initialize_session_data(keyword, log_callback=default_logger):
    """
    Checks for cached session data first. If valid cache exists, uses it.
    Otherwise, launches a browser with stealth options in headless mode,
    visits the search page using eager load mode, extracts cookies
    and user agent, saves them to cache, and then closes the browser.
    """
    log_callback(f"Initializing session for product: '{keyword}'")
    cached_data = None
    cache_valid = False

    if os.path.exists(SESSION_CACHE_FILE):
        try:
            with open(SESSION_CACHE_FILE, 'r') as f:
                cached_data = json.load(f)
            saved_timestamp = cached_data.get('timestamp', 0)
            current_timestamp = time.time()
            cache_age = current_timestamp - saved_timestamp

            if cache_age < CACHE_EXPIRATION_SECONDS:
                cache_valid = True
                log_callback(f"Using cached session data (Age: {timedelta(seconds=int(cache_age))}).")
                return cached_data['cookies'], cached_data['user_agent']
            else:
                log_callback(f"Cached session data expired (Age: {timedelta(seconds=int(cache_age))}).")

        except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
            log_callback(f"Error reading cache file or cache invalid ({e}). Will fetch fresh session.")
            cached_data = None
    else:
        pass

    # --- Cache Miss or Expired: Launch Browser ---
    log_callback("Fetching fresh session data using headless browser...")
    browser_page = None
    try:
        co = ChromiumOptions()
        co.no_imgs(True)
        # --- Block CSS ---
        co.set_pref('permissions.default.stylesheet', 2)
        co.headless()
        user_agent_string = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
        co.set_user_agent(user_agent_string)
        # --- Other Stealth Options ---
        co.set_argument('--disable-blink-features=AutomationControlled')
        co.set_pref('credentials_enable_service', False)
        co.set_pref('profile.password_manager_enabled', False)
        co.set_argument("--excludeSwitches", "enable-automation")

        browser_page = WebPage(chromium_options=co)
        browser_page.set.load_mode.eager()

        search_url = f'https://www.aliexpress.com/w/wholesale-{quote_plus(keyword)}.html'
        log_callback(f"Visiting initial search page (eager load, images and CSS blocked): {search_url}")
        browser_page.get(search_url)

        log_callback("Extracting fresh cookies and user agent...")
        fresh_cookies = browser_page.cookies().as_dict()
        fresh_user_agent = browser_page.user_agent
        log_callback(f"Using User-Agent: {fresh_user_agent}")
        log_callback(f"Extracted {len(fresh_cookies)} cookies.")

        cache_content = {
            'timestamp': time.time(),
            'cookies': fresh_cookies,
            'user_agent': fresh_user_agent
        }
        try:
            with open(SESSION_CACHE_FILE, 'w') as f:
                json.dump(cache_content, f, indent=4)
            log_callback("Session data cached successfully.")
        except IOError as e:
            log_callback(f"Error saving session cache: {e}")

        return fresh_cookies, fresh_user_agent

    except Exception as e:
        log_callback(f"An error occurred during browser initialization: {e}")
        raise
    finally:
        # --- Ensure browser is closed ---
        if browser_page:
            browser_page.quit()

def scrape_aliexpress_data(keyword, max_pages, cookies, user_agent,
                           apply_discount_filter=False, apply_free_shipping_filter=False,
                           min_price=None, max_price=None, delay=1.0, log_callback=default_logger):
    """
    Uses SessionPage and extracted session data to scrape product results
    for the given keyword via direct API calls, optionally applying filters.
    """
    log_callback(f"\nCreating SessionPage for API calls for product: '{keyword}'")
    session_page = SessionPage()
    session_page.set.cookies(cookies)

    current_base_headers = BASE_HEADERS.copy()
    current_base_headers['user-agent'] = user_agent

    all_products_raw = []
    keyword_safe_name = "".join(c if c.isalnum() else "_" for c in keyword)

    active_switches = []
    if apply_discount_filter:
        log_callback("Applying 'Big Sale' discount filter...")
        active_switches.append("filterCode:bigsale")
    if apply_free_shipping_filter:
        log_callback("Applying 'Free Shipping' filter...")
        active_switches.append("filterCode:freeshipping")

    price_range_str = None
    min_price_int = int(min_price) if min_price is not None and min_price >= 0 else None
    max_price_int = int(max_price) if max_price is not None and max_price >= 0 else None

    if min_price_int is not None and max_price_int is not None:
        if min_price_int <= max_price_int:
            price_range_str = f"{min_price_int}-{max_price_int}"
            log_callback(f"Applying Price Filter: {price_range_str}")
        else:
            log_callback("Warning: Min price is greater than max price. Ignoring price filter.")
    elif min_price_int is not None:
        price_range_str = f"{min_price_int}-"
        log_callback(f"Applying Price Filter: Min {min_price_int}")
    elif max_price_int is not None:
        price_range_str = f"-{max_price_int}"
        log_callback(f"Applying Price Filter: Max {max_price_int}")

    for current_page_num in range(1, max_pages + 1):
        log_callback(f"Attempting to fetch page {current_page_num} for product: '{keyword}' via API...")

        request_headers = current_base_headers.copy()
        referer_keyword_part = quote_plus(keyword)
        referer_url = f'https://www.aliexpress.com/w/wholesale-{referer_keyword_part}.html?page={current_page_num}&g=y&SearchText={referer_keyword_part}'
        if active_switches:
            switches_value = ",".join(active_switches)
            referer_url += f'&selectedSwitches={quote_plus(switches_value)}'
        if price_range_str:
            referer_url += f'&pr={price_range_str}'
        request_headers['Referer'] = referer_url


        payload = {
            "pageVersion": "7ece9c0cc9cf2052db74f0d1b26b7033",
            "target": "root",
            "data": {
                "page": current_page_num,
                "g": "y",
                "SearchText": keyword,
                "origin": "y"
            },
            "eventName": "onChange",
            "dependency": []
        }

        if active_switches:
            payload['data']['selectedSwitches'] = ",".join(active_switches)
        if price_range_str:
            payload['data']['pr'] = price_range_str

        # Make the POST request
        success = session_page.post(API_URL, json=payload, headers=request_headers)

        if not success or not session_page.response or session_page.response.status_code != 200:
            status = session_page.response.status_code if session_page.response else 'N/A'
            log_callback(f"Failed to fetch page {current_page_num}. Status code: {status}")
            if session_page.response:
                log_callback(f"Response text sample: {session_page.response.text[:200]}")
            break

        try:
            json_data = session_page.json
            if not isinstance(json_data, dict):
                log_callback(f"Unexpected response format for page {current_page_num}. Expected JSON dict.")
                log_callback(f"Response text sample: {session_page.html[:200]}")
                break

            items_list = json_data.get('data', {}).get('result', {}).get('mods', {}).get('itemList', {}).get('content', [])

            if not items_list:
                log_callback(f"No items found using path 'data.result.mods.itemList.content' on page {current_page_num}.")
                if current_page_num == max_pages:
                    log_callback(f"Reached requested page limit ({max_pages}) with no items found on this last page.")
                    break
                elif current_page_num > 1:
                    log_callback(f"Stopping search: No items found on page {current_page_num} (before requested limit of {max_pages} pages).")
                    break
                else:
                    log_callback("Continuing to next page (in case only page 1 structure differs).")
            else:
                log_callback(f"Found {len(items_list)} items on page {current_page_num}.")
                all_products_raw.extend(items_list)

        except json.JSONDecodeError:
            log_callback(f"Failed to decode JSON response for page {current_page_num}.")
            log_callback(f"Response text sample: {session_page.html[:200]}")
            break
        except Exception as e:
            log_callback(f"An error occurred processing page {current_page_num}: {e}")
            break

        # Delay between requests
        time.sleep(delay)

    log_callback(f"\nAPI Scraping finished for product: '{keyword}'. Total raw products collected: {len(all_products_raw)}")
    return all_products_raw

def extract_variant_from_title(title):
    """
    Extract variant specification from product title.
    Looks for processor types, memory specs, colors, materials, sizes, etc.
    """
    import re
    
    if not title:
        return None
    
    # Common patterns for various product variants
    patterns = [
        # Hardware variants
        r'\b(N100|N150|N200|N300|N5100|N6000)\b',  # Intel processors
        r'\b(Ryzen\s+\d+\w*)\b',  # AMD Ryzen processors
        r'\b(\d+GB\s+DDR[45]?)\b',  # Memory specs
        r'\b(Core\s+i[3579]-\d+\w*)\b',  # Intel Core processors
        r'\b(Celeron\s+\w+)\b',  # Celeron processors
        r'\b(\d+TB?\s+SSD)\b',  # Storage specs
        r'\b(WiFi\s*[56])\b',  # WiFi versions
        
        # 3D Printer filament variants
        r'\b(PLA|ABS|PETG|TPU|PLA\+|WOOD|SILK|GLOW|CARBON)\b',  # Filament materials
        r'\b(1\.75mm|3\.0mm|2\.85mm)\b',  # Filament diameter
        r'\b(\d+(?:\.\d+)?kg)\b',  # Filament weight
        r'\b(\d+M)\b',  # Filament length in meters (25M, 96M, 150M, etc.)
        r'\b(\d+g)\b',  # Filament weight in grams
        
        # Color variants (common colors) - extended list
        r'\b(Black|White|Red|Blue|Green|Yellow|Orange|Purple|Pink|Gray|Grey|Silver|Gold|Brown|Clear|Transparent|Cyan|Magenta|Lime|Navy|Maroon|Olive|Teal|Aqua|Fuchsia|Beige|Ivory|Khaki|Lavender|Coral|Salmon|Turquoise|Violet|Indigo|Crimson|Rose|Amber|Emerald|Ruby|Sapphire|Pearl|Bronze|Copper|Platinum|Metallic|Matte|Glossy|Satin)\b',
        
        # Size variants
        r'\b(XS|S|M|L|XL|XXL|XXXL)\b',  # Clothing sizes
        r'\b(\d+\.?\d*\s*(?:mm|cm|m|inch|in))\b',  # Measurements
        r'\b(\d+x\d+(?:x\d+)?)\b',  # Dimensions
        
        # Capacity/Power variants
        r'\b(\d+mAh)\b',  # Battery capacity
        r'\b(\d+W)\b',  # Power rating
        r'\b(\d+A)\b',  # Current rating
        r'\b(\d+V)\b',  # Voltage
        
        # Generic model numbers
        r'\b(Type-?\s*[A-C])\b',  # Type A, B, C
        r'\b(Model\s*[A-Z0-9]+)\b',  # Model numbers
        r'\b(V\d+(?:\.\d+)?)\b',  # Version numbers
    ]
    
    variants = []
    for pattern in patterns:
        matches = re.findall(pattern, title, re.IGNORECASE)
        variants.extend(matches)
    
    if not variants:
        return None
    
    # Priority system for variants
    priority_order = [
        # Hardware specs have highest priority
        ['N100', 'N150', 'N200', 'RYZEN', 'CORE', 'CELERON'],
        # Filament length/quantity (specific measurements) - high priority for filaments
        ['M', 'G', 'KG'],  # Meters, grams, kilograms
        # Materials for 3D printing - but only if no length/quantity found
        ['PLA', 'ABS', 'PETG', 'TPU', 'WOOD', 'SILK'],
        # Colors
        ['BLACK', 'WHITE', 'RED', 'BLUE', 'GREEN', 'YELLOW', 'ORANGE', 'PURPLE', 'PINK', 'GRAY', 'GREY', 'SILVER', 'GOLD', 'BROWN', 'CLEAR', 'TRANSPARENT', 'CYAN', 'MAGENTA', 'LIME', 'NAVY', 'MAROON', 'OLIVE', 'TEAL'],
        # Power/capacity
        ['MAH', 'W', 'A', 'V'],
        # Sizes and measurements (lower priority)
        ['MM', 'CM', 'INCH'],
    ]
    
    # Find the highest priority variant
    for priority_group in priority_order:
        matching_variants = [v for v in variants if any(keyword in v.upper() for keyword in priority_group)]
        if matching_variants:
            return matching_variants[0]
    
    # If no priority match, return the first variant found
    return variants[0]

def extract_product_details(raw_products, selected_fields):
    """
    Extracts and formats desired fields from the raw product data,
    based on the user's selection, including variant information.
    """
    extracted_data = []
    if not raw_products or not selected_fields:
        return extracted_data
    for product in raw_products:
        # --- Extract ALL possible fields first ---
        product_id = product.get('productId')
        title = product.get('title', {}).get('displayTitle')
        
        # Extract variant information from multiple sources
        variant_title = extract_variant_from_title(title)
        
        # Try to extract more specific variant info from SKU data
        sku_info = product.get('prices', {})
        if sku_info and not variant_title:
            # Look for variant info in SKU attributes
            sku_attributes = sku_info.get('attributes', {})
            if sku_attributes:
                # Check for color, size, or other variant attributes
                for attr_key, attr_value in sku_attributes.items():
                    if attr_value and isinstance(attr_value, str):
                        potential_variant = extract_variant_from_title(attr_value)
                        if potential_variant:
                            variant_title = potential_variant
                            break
        
        # Extract real variant information from AliExpress API
        sku_id = product.get('prices', {}).get('skuId')
        spu_id = product.get('trace', {}).get('utLogMap', {}).get('spu_id')
        
        # Extract variant attributes from prices section
        variant_attributes = {}
        prices_info = product.get('prices', {})
        if 'skuAttr' in prices_info:
            sku_attr = prices_info['skuAttr']
            # Parse SKU attributes like "14:173,5:100014064#Black;14:365,200000463:100007326#2 Wheels"
            if sku_attr:
                for attr_pair in sku_attr.split(';'):
                    if '#' in attr_pair:
                        value = attr_pair.split('#')[1]
                        variant_attributes[len(variant_attributes)] = value
        image_url = product.get('image', {}).get('imgUrl')
        if image_url and not image_url.startswith('http'):
            image_url = 'https:' + image_url
        prices_info = product.get('prices', {})
        sale_price_info = prices_info.get('salePrice', {})
        original_price_info = prices_info.get('originalPrice', {})
        sale_price = sale_price_info.get('formattedPrice')
        original_price = original_price_info.get('formattedPrice')
        currency = sale_price_info.get('currencyCode')
        discount = sale_price_info.get('discount')
        store_info = product.get('store', {})
        store_name = store_info.get('storeName')
        store_id = store_info.get('storeId')
        store_url = store_info.get('storeUrl')
        if store_url and not store_url.startswith('http'):
            store_url = 'https:' + store_url
        trade_info = product.get('trade', {})
        orders_count = trade_info.get('realTradeCount')
        rating = product.get('evaluation', {}).get('starRating')
        product_url = f"https://www.aliexpress.com/item/{product_id}.html" if product_id else None

        # --- Store all potentially extractable data in a temporary dict ---
        full_details = {
            'Product ID': product_id,
            'SKU ID': sku_id,
            'SPU ID': spu_id,
            'Title': title,
            'Variant Title': variant_title,
            'Variant Attributes': variant_attributes,
            'Sale Price': sale_price,
            'Original Price': original_price,
            'Discount (%)': discount,
            'Currency': currency,
            'Rating': rating,
            'Orders Count': orders_count,
            'Store Name': store_name,
            'Store ID': store_id,
            'Store URL': store_url,
            'Product URL': product_url,
            'Image URL': image_url,
        }

        filtered_item = {field: full_details.get(field) for field in selected_fields}

        extracted_data.append(filtered_item)

    return extracted_data

def save_results_to_database(keyword, data, track_products=False):
    """
    Saves the extracted data to the database, creating/updating products.
    Only adds price history for tracked products unless track_products=True.
    Now handles proper variant detection based on SKU ID.
    """
    if not data:
        return 0
    
    
    saved_count = 0
    updated_count = 0
    price_updates = 0
    
    try:
        for item in data:
            product_id = item.get('Product ID')
            sku_id = item.get('SKU ID')
            
            if not product_id:
                continue
            
            # For regular scraping, create unique sku_id if no specific sku_id exists
            if not sku_id:
                # Generate unique SKU ID to prevent conflicts
                variant_title = item.get('Variant Title', '')
                if variant_title:
                    # Create unique SKU based on product_id and variant
                    import hashlib
                    variant_hash = hashlib.md5(variant_title.encode()).hexdigest()[:8]
                    sku_id = f"{product_id}_{variant_hash}"
                else:
                    sku_id = product_id
            
            # Check if this specific variant (SKU) already exists
            existing_product = Product.query.filter_by(sku_id=str(sku_id)).first()
            
            if existing_product:
                # Update existing product
                existing_product.title = item.get('Title', existing_product.title)
                existing_product.sku_id = item.get('SKU ID', existing_product.sku_id)
                existing_product.spu_id = item.get('SPU ID', existing_product.spu_id)
                existing_product.variant_title = item.get('Variant Title', existing_product.variant_title)
                existing_product.image_url = item.get('Image URL', existing_product.image_url)
                existing_product.store_name = item.get('Store Name', existing_product.store_name)
                existing_product.store_id = item.get('Store ID', existing_product.store_id)
                existing_product.store_url = item.get('Store URL', existing_product.store_url)
                existing_product.currency = item.get('Currency', existing_product.currency)
                existing_product.rating = item.get('Rating', existing_product.rating)
                existing_product.orders_count = item.get('Orders Count', existing_product.orders_count)
                existing_product.updated_at = datetime.utcnow()
                existing_product.is_active = True
                
                product = existing_product
                updated_count += 1
            else:
                # Create new product variant
                # Extract variant info from attributes or title
                variant_attrs = item.get('Variant Attributes', {})
                if variant_attrs:
                    variant_title = ', '.join(variant_attrs.values())
                else:
                    variant_title = item.get('Variant Title')
                
                product = Product(
                    product_id=str(product_id),
                    sku_id=str(sku_id),
                    spu_id=item.get('SPU ID'),
                    title=item.get('Title', ''),
                    variant_title=variant_title,
                    image_url=item.get('Image URL'),
                    product_url=item.get('Product URL', f"https://www.aliexpress.com/item/{product_id}.html"),
                    store_name=item.get('Store Name'),
                    store_id=item.get('Store ID'),
                    store_url=item.get('Store URL'),
                    currency=item.get('Currency'),
                    rating=item.get('Rating'),
                    orders_count=item.get('Orders Count')
                )
                db.session.add(product)
                saved_count += 1
            
            # Add price history for tracked products, new products during initial scraping, or if explicitly requested
            if track_products or (existing_product and existing_product.is_tracked) or not existing_product:
                sale_price = item.get('Sale Price')
                original_price = item.get('Original Price')
                discount = item.get('Discount (%)')
                
                # Parse prices if they're strings with better error logging
                if isinstance(sale_price, str):
                    try:
                        sale_price = parse_price_string(sale_price)
                    except (ValueError, AttributeError) as e:
                        print(f"Warning: Could not parse sale price '{sale_price}' for product {product_id}: {e}")
                        sale_price = None
                
                if isinstance(original_price, str):
                    try:
                        original_price = parse_price_string(original_price)
                    except (ValueError, AttributeError) as e:
                        print(f"Warning: Could not parse original price '{original_price}' for product {product_id}: {e}")
                        original_price = None
                
                if sale_price is not None:
                    # Flush to get the product ID for new products
                    db.session.flush()
                    
                    price_history = PriceHistory(
                        product_id=product.id,
                        sale_price=sale_price,
                        original_price=original_price,
                        discount_percentage=discount
                    )
                    db.session.add(price_history)
                    price_updates += 1
        
        db.session.commit()
        return saved_count + updated_count
        
    except Exception as e:
        db.session.rollback()
        return 0

def save_results(keyword, data, selected_fields, log_callback=default_logger, track_products=False):
    """
    Saves the extracted data to both database and files.
    """
    if not data:
        log_callback("No data to save.")
        return None, None
    
    # Save to database
    db_count = save_results_to_database(keyword, data, track_products=track_products)
    
    # Also save to files for backup
    if not selected_fields:
        log_callback("No fields selected for file saving.")
        return None, None

    os.makedirs(RESULTS_DIR, exist_ok=True)
    keyword_safe_name = "".join(c if c.isalnum() else "_" for c in keyword)
    json_filename = os.path.join(RESULTS_DIR, f'aliexpress_{keyword_safe_name}_extracted.json')
    csv_filename = os.path.join(RESULTS_DIR, f'aliexpress_{keyword_safe_name}_extracted.csv')

    try:
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        fieldnames = selected_fields
        with open(csv_filename, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(data)
        
        log_callback(f"Files saved to: {json_filename}, {csv_filename}")
        return json_filename, csv_filename

    except Exception as e:
        log_callback(f"Error saving results to file: {e}")
        return None, None

class StreamLogger:
    def __init__(self):
        self.message_queue = Queue()
        self.active = True
    
    def log(self, message):
        if self.active:
            self.message_queue.put(message)
    
    def stream_messages(self):
        while self.active or not self.message_queue.empty():
            try:
                message = self.message_queue.get(timeout=0.1)
                yield f"data: {message}\n\n"
                self.message_queue.task_done()
            except:
                continue
        yield "data: PROCESS_COMPLETE\n\n"
    
    def stop(self):
        self.active = False

def run_scrape_job(keyword, pages, apply_discount, free_shipping, min_price, max_price, selected_fields, delay=1.0, save_to_db=True, track_products=False, update_existing=False):
    """
    Generator function that orchestrates the scraping process with real-time logging.
    """
    try:
        yield "data: Starting scraping process...\n\n"
        
        yield f"data: Initializing session for product: '{keyword}'\n\n"
        cookies, user_agent = initialize_session_data(keyword)
        
        yield f"data: Starting scraping for {pages} pages...\n\n"
        raw_products = scrape_aliexpress_data(
            keyword=keyword,
            max_pages=pages,
            cookies=cookies,
            user_agent=user_agent,
            apply_discount_filter=apply_discount,
            apply_free_shipping_filter=free_shipping,
            min_price=min_price,
            max_price=max_price,
            delay=delay
        )
        
        yield "data: Extracting product details...\n\n"
        extracted_data = extract_product_details(raw_products, selected_fields)
        
        yield "data: Saving results...\n\n"
        if save_to_db:
            # Count existing products before update
            existing_count = Product.query.filter_by(is_active=True).count()
            
            db_count = save_results_to_database(keyword, extracted_data, track_products=track_products)
            
            # Count new products after update
            new_count = Product.query.filter_by(is_active=True).count()
            new_products = new_count - existing_count
            
            if update_existing:
                yield f"data: Database updated: {db_count} products processed, {new_products} new variants found\n\n"
            else:
                yield f"data: Database saved: {db_count} products\n\n"
            
            # Also save backup files
            os.makedirs(RESULTS_DIR, exist_ok=True)
            keyword_safe_name = "".join(c if c.isalnum() else "_" for c in keyword)
            json_filename = os.path.join(RESULTS_DIR, f'aliexpress_{keyword_safe_name}_extracted.json')
            
            try:
                with open(json_filename, 'w', encoding='utf-8') as f:
                    json.dump(extracted_data, f, ensure_ascii=False, indent=4)
                yield f"data: Backup file saved to: {json_filename}\n\n"
            except Exception as e:
                yield f"data: Error saving backup file: {e}\n\n"
        else:
            # Legacy file-only saving
            os.makedirs(RESULTS_DIR, exist_ok=True)
            keyword_safe_name = "".join(c if c.isalnum() else "_" for c in keyword)
            json_filename = os.path.join(RESULTS_DIR, f'aliexpress_{keyword_safe_name}_extracted.json')
            
            try:
                with open(json_filename, 'w', encoding='utf-8') as f:
                    json.dump(extracted_data, f, ensure_ascii=False, indent=4)
                yield f"data: JSON file saved to: {json_filename}\n\n"
            except Exception as e:
                yield f"data: Error saving results to file: {e}\n\n"
        
        yield "data: Scraping completed successfully!\n\n"
        
    except Exception as e:
        yield f"data: ERROR: {str(e)}\n\n"
    finally:
        yield "data: PROCESS_COMPLETE\n\n"

def scrape_enhanced_variants(product_url, log_callback=default_logger, product_title=None):
    """
    Enhanced variant scraping that specifically handles data-sku-col structure
    from AliExpress product pages with proper price extraction.
    """
    try:
        log_callback(f"Enhanced variant scraping for: {product_url}")
        
        # Extract product ID from URL
        import re
        url_match = re.search(r'/item/(\d+)\.html', product_url)
        base_product_id = url_match.group(1) if url_match else None
        
        if not base_product_id:
            log_callback("Could not extract product ID from URL")
            return []
        
        # Set up browser with better stealth options and session cookies
        co = ChromiumOptions()
        co.no_imgs(False)  # We need images for variants
        co.headless()
        user_agent_string = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
        co.set_user_agent(user_agent_string)
        co.set_argument('--disable-blink-features=AutomationControlled')
        co.set_pref('credentials_enable_service', False)
        co.set_pref('profile.password_manager_enabled', False)
        co.set_argument("--excludeSwitches", "enable-automation")
        co.set_argument("--disable-web-security")
        co.set_argument("--disable-features=VizDisplayCompositor")
        
        browser_page = WebPage(chromium_options=co)
        browser_page.set.load_mode.eager()  # Use eager mode for faster loading
        
        # Use session cookies for better loading
        cookies, user_agent = initialize_session_data(f"variant_{base_product_id}")
        browser_page.set.cookies(cookies)
        
        log_callback("Loading product page for enhanced variant scraping...")
        browser_page.get(product_url, timeout=30)
        
        # ENHANCED WAITING STRATEGY: Wait for dynamic content to fully load
        log_callback("Waiting for dynamic content to load...")
        max_wait_time = 45  # Increased to 45 seconds
        check_interval = 3  # Check every 3 seconds
        content_loaded = False
        
        for i in range(max_wait_time // check_interval):
            time.sleep(check_interval)
            
            # Check multiple indicators for page readiness
            page_ready_indicators = []
            
            # Check 1: Price elements
            try:
                price_elements = browser_page.eles('.price--currentPriceText--V8_y_b5', timeout=1)
                if price_elements:
                    page_ready_indicators.append("price")
            except:
                pass
                
            # Check 2: Variant elements
            try:
                variant_elements = browser_page.eles('[data-sku-col]', timeout=1)
                if variant_elements:
                    page_ready_indicators.append("variants")
            except:
                pass
                
            # Check 3: Product details content
            try:
                product_content = browser_page.eles('.product-container, .product-detail', timeout=1)
                if product_content:
                    page_ready_indicators.append("product_content")
            except:
                pass
                
            # Check 4: SKU selector elements  
            try:
                sku_elements = browser_page.eles('.sku-item, .sku-property', timeout=1)
                if sku_elements:
                    page_ready_indicators.append("sku_elements")
            except:
                pass
            
            log_callback(f"Page loading progress ({(i+1)*check_interval}s): {', '.join(page_ready_indicators) if page_ready_indicators else 'waiting...'}")
            
            # Page is ready if we have either variants OR price+content
            if "variants" in page_ready_indicators or (len(page_ready_indicators) >= 2):
                content_loaded = True
                log_callback(f"Dynamic content loaded successfully after {(i+1)*check_interval} seconds")
                break
        
        if not content_loaded:
            log_callback("Warning: Dynamic content may not be fully loaded, proceeding with current state")
        
        # Additional wait for any final rendering
        time.sleep(5)
        
        # Try to scroll and trigger any lazy loading
        try:
            browser_page.scroll.to_bottom()
            time.sleep(2)
            browser_page.scroll.to_top()
            time.sleep(1)
        except:
            pass
        
        variants = []
        
        # ROBUST VARIANT DETECTION - Use HTML parsing instead of browser automation
        log_callback("Using robust HTML parsing for variant detection")
        
        page_html = browser_page.html
        if not page_html:
            log_callback("No HTML content available")
            browser_page.quit()
            return []
            
        # DEBUG: Save HTML content for analysis
        import os
        debug_file = f"/tmp/variant_debug_{base_product_id}.html"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(page_html)
        log_callback(f"HTML content saved to {debug_file} (length: {len(page_html)})")
        
        # Parse HTML with regex to find ALL data-sku-col elements
        import re
        
        # Find all data-sku-col attributes first
        sku_col_pattern = r'data-sku-col="([^"]*)"'
        sku_col_matches = re.findall(sku_col_pattern, page_html, re.IGNORECASE)
        
        log_callback(f"Found {len(sku_col_matches)} data-sku-col attributes: {sku_col_matches}")
        
        # If no SKU cols found, let's try to understand why and take corrective action
        if not sku_col_matches:
            log_callback("No data-sku-col found! Analyzing HTML structure...")
            
            # Count total elements
            div_count = len(re.findall(r'<div[^>]*>', page_html, re.IGNORECASE))
            img_count = len(re.findall(r'<img[^>]*>', page_html, re.IGNORECASE))
            log_callback(f"HTML contains {div_count} divs and {img_count} images")
            
            # Look for any data-sku references
            sku_refs = re.findall(r'data-sku[^=]*="([^"]*)"', page_html, re.IGNORECASE)
            log_callback(f"Found {len(sku_refs)} data-sku references: {sku_refs}")
            
            # Look for the specific class we know exists
            sku_class_matches = re.findall(r'class="[^"]*sku-item--image--jMUnnGA[^"]*"', page_html, re.IGNORECASE)
            log_callback(f"Found {len(sku_class_matches)} elements with sku-item--image--jMUnnGA class")
            
            # Check if page is fully loaded by looking for price elements
            price_elements = re.findall(r'price--currentPriceText--V8_y_b5', page_html, re.IGNORECASE)
            log_callback(f"Found {len(price_elements)} price elements - page loaded: {len(price_elements) > 0}")
            
            # Check for JavaScript errors or loading issues
            js_errors = re.findall(r'error|Error|ERROR', page_html[:5000], re.IGNORECASE)
            log_callback(f"Potential JS errors detected: {len(js_errors) > 0}")
            
            # AGGRESSIVE RETRY: Try multiple strategies to force dynamic content loading
            log_callback("Attempting aggressive content loading strategies...")
            
            # Strategy 1: Execute JavaScript to trigger dynamic loading
            try:
                browser_page.run_js("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)
                browser_page.run_js("document.querySelectorAll('.sku-property, .sku-item').forEach(el => el.click());")
                time.sleep(2)
            except Exception as e:
                log_callback(f"JS execution failed: {e}")
            
            # Strategy 2: Try clicking on potential variant elements
            try:
                variant_buttons = browser_page.eles('.sku-item, .sku-property, [class*="sku"]', timeout=3)
                if variant_buttons:
                    log_callback(f"Found {len(variant_buttons)} potential variant buttons, clicking first few...")
                    for i, btn in enumerate(variant_buttons[:3]):
                        try:
                            btn.click()
                            time.sleep(1)
                        except:
                            continue
            except:
                pass
            
            # Strategy 3: Wait longer and refresh HTML
            log_callback("Waiting additional 15 seconds for dynamic content...")
            time.sleep(15)
            
            # Get fresh HTML
            page_html = browser_page.html
            sku_col_matches = re.findall(sku_col_pattern, page_html, re.IGNORECASE)
            log_callback(f"After aggressive loading: Found {len(sku_col_matches)} data-sku-col attributes")
            
            # If still no variants, save HTML for detailed analysis
            if not sku_col_matches:
                debug_file_detailed = f"/tmp/variant_debug_detailed_{base_product_id}.html"
                with open(debug_file_detailed, 'w', encoding='utf-8') as f:
                    f.write(page_html)
                log_callback(f"No variants found. Detailed HTML saved to {debug_file_detailed}")
                
                # Try alternative selectors for variant detection
                alternative_patterns = [
                    r'sku-property[^>]*>.*?</[^>]*>',
                    r'variant[^>]*>.*?</[^>]*>',
                    r'color[^>]*>.*?</[^>]*>',
                    r'size[^>]*>.*?</[^>]*>'
                ]
                
                for pattern in alternative_patterns:
                    matches = re.findall(pattern, page_html, re.IGNORECASE | re.DOTALL)
                    if matches:
                        log_callback(f"Alternative pattern found {len(matches)} matches: {pattern}")
                        break
        
        # Now find images that might be associated with these SKUs
        # Look for images with variant-related alt text
        img_pattern = r'<img[^>]*src="([^"]*)"[^>]*alt="([^"]*)"[^>]*>'
        img_matches = re.findall(img_pattern, page_html, re.IGNORECASE)
        
        # Filter for variant images
        variant_images = []
        for src, alt in img_matches:
            if any(keyword in alt.lower() for keyword in ['kg', 'color', 'pla', 'petg', 'tpu', 'black', 'white', 'red', 'blue', 'green', 'yellow', 'pink', 'violet', 'turquoise', 'spring', 'leaf', 'peach']):
                variant_images.append((src, alt))
        
        log_callback(f"Found {len(variant_images)} potential variant images: {[alt for src, alt in variant_images]}")
        
        # Process each SKU and try to match with images
        for i, sku_col_value in enumerate(sku_col_matches):
            try:
                log_callback(f"Processing variant with SKU: {sku_col_value}")
                
                # Try to find matching image
                variant_image = None
                variant_alt = None
                
                # If we have variant images, use them
                if i < len(variant_images):
                    variant_image = variant_images[i][0]
                    variant_alt = variant_images[i][1]
                elif variant_images:
                    # Use first available image as fallback
                    variant_image = variant_images[0][0]
                    variant_alt = variant_images[0][1]
                
                # Clean up image URL
                if variant_image and not variant_image.startswith('http'):
                    if variant_image.startswith('//'):
                        variant_image = 'https:' + variant_image
                    else:
                        variant_image = 'https://' + variant_image
                
                # Extract variant name from alt text
                variant_name = extract_variant_from_alt_text(variant_alt)
                if not variant_name:
                    variant_name = variant_alt or f"Variant {sku_col_value}"
                
                log_callback(f"Found variant: {variant_name} (SKU: {sku_col_value}) - Image: {variant_image}")
                
                # Try to get price by clicking on the variant
                current_price = None
                original_price = None
                
                try:
                    # Find the actual element on the page and click it
                    variant_element = browser_page.ele(f'[data-sku-col="{sku_col_value}"]', timeout=3)
                    if variant_element:
                        variant_element.click()
                        time.sleep(2)  # Wait for price update
                        
                        # Extract price
                        price_selectors = [
                            '.price--currentPriceText--V8_y_b5',
                            '.price--current--I3Zeidd .price--currentPriceText--V8_y_b5',
                            '.product-price-value'
                        ]
                        
                        for price_selector in price_selectors:
                            try:
                                price_element = browser_page.ele(price_selector, timeout=2)
                                if price_element:
                                    current_price = price_element.text.strip()
                                    log_callback(f"Found price for {variant_name}: {current_price}")
                                    break
                            except:
                                continue
                                
                except Exception as e:
                    log_callback(f"Could not click variant {sku_col_value}: {e}")
                
                # Create variant data
                sku_id = f"{base_product_id}_{sku_col_value}"
                variant_data = {
                    'sku_id': sku_id,
                    'product_id': base_product_id,
                    'variant_title': variant_name,
                    'image_url': variant_image,
                    'alt_text': variant_alt,
                    'sku_col': sku_col_value,
                    'sale_price': current_price,
                    'original_price': original_price,
                    'source': 'robust_html_parsing'
                }
                variants.append(variant_data)
                
            except Exception as e:
                log_callback(f"Error processing variant {sku_col_value}: {e}")
                continue
        
        browser_page.quit()
        
        log_callback(f"Successfully extracted {len(variants)} variants using robust HTML parsing")
        return variants
        
    except Exception as e:
        log_callback(f"Error in enhanced variant scraping: {e}")
        try:
            browser_page.quit()
        except:
            pass
        # Fallback to original interactive scraping
        return scrape_interactive_variants(product_url, log_callback, product_title)

def extract_variant_pricing_from_static(browser_page, static_variants, log_callback):
    """
    Extract pricing for static variants by clicking on each variant
    """
    import time
    
    log_callback(f"Extracting pricing for {len(static_variants)} static variants")
    
    enhanced_variants = []
    
    for i, variant in enumerate(static_variants[:35]):  # Limit to 35 variants
        try:
            log_callback(f"Processing variant {i+1}/{len(static_variants[:35])}: {variant.get('variant_title', 'Unknown')}")
            
            # Find the variant element by data-sku-col
            sku_col = variant.get('sku_col', '')
            if not sku_col:
                log_callback(f"No SKU col found for variant {i+1}")
                continue
            
            # Try to find the variant element
            variant_selector = f'[data-sku-col="{sku_col}"]'
            try:
                variant_element = browser_page.ele(variant_selector, timeout=2)
                if not variant_element:
                    log_callback(f"Variant element not found for SKU {sku_col}")
                    continue
                
                # Scroll to element and click
                variant_element.scroll.to_see()
                time.sleep(0.5)
                variant_element.click()
                log_callback(f"Clicked variant {sku_col}")
                
                # Wait for price update with progressive checks
                current_price = None
                original_price = None
                
                # Progressive wait for price update
                for wait_attempt in range(8):  # Try up to 4 seconds
                    time.sleep(0.5)
                    
                    # Try multiple price selectors
                    price_selectors = [
                        '.price--currentPriceText--V8_y_b5',
                        '.price--current--I3Zeidd .price--currentPriceText--V8_y_b5',
                        '.price--currentPriceText--V8_y_b5.pdp-comp-price-current.product-price-value',
                        '.product-price-value',
                        '[class*="currentPriceText"]'
                    ]
                    
                    for selector in price_selectors:
                        try:
                            price_element = browser_page.ele(selector, timeout=1)
                            if price_element and price_element.text.strip():
                                current_price = price_element.text.strip()
                                log_callback(f"Found price: {current_price}")
                                break
                        except:
                            continue
                    
                    if current_price:
                        break
                
                # Try to get original price
                original_price_selectors = [
                    '.price--originalText--vVXzWPt',
                    '.price--original--I3Zeidd',
                    '[class*="originalText"]',
                    '[class*="original"][class*="price"]'
                ]
                
                for selector in original_price_selectors:
                    try:
                        orig_element = browser_page.ele(selector, timeout=1)
                        if orig_element and orig_element.text.strip():
                            original_price = orig_element.text.strip()
                            break
                    except:
                        continue
                
                # Create enhanced variant data
                enhanced_variant = {
                    'sku_id': variant.get('sku_id'),
                    'product_id': variant.get('product_id'),
                    'variant_name': variant.get('variant_title'),
                    'variant_title': variant.get('variant_title'),
                    'image_url': variant.get('image_url'),
                    'alt_text': variant.get('alt_text'),
                    'sku_col': sku_col,
                    'current_price': current_price,
                    'sale_price': current_price,
                    'original_price': original_price,
                    'source': 'static_with_dynamic_pricing'
                }
                
                enhanced_variants.append(enhanced_variant)
                
                log_callback(f"Enhanced variant: {variant.get('variant_title')} - Price: {current_price}")
                
            except Exception as e:
                log_callback(f"Error processing variant {sku_col}: {e}")
                continue
                
        except Exception as e:
            log_callback(f"Error processing variant {i+1}: {e}")
            continue
    
    log_callback(f"Successfully extracted pricing for {len(enhanced_variants)} variants")
    return enhanced_variants

def scrape_interactive_variants(product_url, log_callback=default_logger, product_title=None):
    """
    Interactive variant scraping that navigates through color/size options 
    and extracts specific prices for each variant
    """
    try:
        log_callback(f"Interactive variant scraping for: {product_url}")
        
        # Extract product ID from URL
        import re
        url_match = re.search(r'/item/(\d+)\.html', product_url)
        base_product_id = url_match.group(1) if url_match else None
        
        if not base_product_id:
            log_callback("Could not extract product ID from URL")
            return []
        
        # Set up browser with stealth options
        co = ChromiumOptions()
        co.no_imgs(False)  # We need images for variants
        co.headless()
        user_agent_string = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
        co.set_user_agent(user_agent_string)
        co.set_argument('--disable-blink-features=AutomationControlled')
        co.set_pref('credentials_enable_service', False)
        co.set_pref('profile.password_manager_enabled', False)
        co.set_argument("--excludeSwitches", "enable-automation")
        
        browser_page = WebPage(chromium_options=co)
        browser_page.set.load_mode.eager()
        
        log_callback("Loading product page for interactive variant scraping...")
        browser_page.get(product_url, timeout=30)
        
        # Wait for page to fully load
        log_callback("Waiting for page content to load...")
        time.sleep(5)
        
        # Try to wait for product price element to ensure page is loaded
        try:
            browser_page.wait.eles_loaded('.price--current--I3Zeidd', timeout=10)
            log_callback("Product price element loaded, page ready")
        except:
            log_callback("Price element not found, continuing anyway")
            time.sleep(3)  # Additional wait
        
        variants = []
        
        # Look for SKU variant containers based on the provided HTML structure
        sku_selectors = [
            'div[data-sku-col]',  # Primary SKU containers from your example
            '.sku-item--image--jMUnnGA',  # Specific class from your example
            '[class*="sku-item--image"]', # Any class containing sku-item--image
            '.sku-item',          # Alternative SKU items
            '[class*="sku-item"]', # Any class containing sku-item
            'div[class*="sku"]',   # Any div with sku in class name
            '[data-sku-col]'      # Any element with data-sku-col attribute
        ]
        
        sku_elements = []
        for selector in sku_selectors:
            elements = browser_page.eles(selector)
            log_callback(f"Selector '{selector}': Found {len(elements)} SKU elements")
            if elements:
                sku_elements.extend(elements)
                break  # Use the first selector that finds elements
        
        if not sku_elements:
            log_callback("No SKU elements found with initial selectors, trying broader search...")
            
            # Try to find any elements with data-sku-col attribute
            all_sku_divs = browser_page.eles('div[data-sku-col]', timeout=2)
            log_callback(f"Found {len(all_sku_divs)} elements with data-sku-col attribute")
            
            # Try to find any div elements containing "sku" in class
            all_sku_classes = browser_page.eles('div[class*="sku"]', timeout=2)
            log_callback(f"Found {len(all_sku_classes)} div elements with 'sku' in class name")
            
            # Try to find any elements with alt text containing color names
            color_images = browser_page.eles('img[alt*="yellow"], img[alt*="black"], img[alt*="white"], img[alt*="red"], img[alt*="blue"], img[alt*="green"]', timeout=2)
            log_callback(f"Found {len(color_images)} images with color names in alt text")
            
            if all_sku_divs:
                sku_elements = all_sku_divs
                log_callback("Using elements with data-sku-col attribute")
            elif color_images:
                # Find parent divs of color images
                sku_elements = []
                for img in color_images:
                    parent = img.parent()
                    if parent and parent not in sku_elements:
                        sku_elements.append(parent)
                log_callback(f"Using parent elements of color images: {len(sku_elements)} elements")
            else:
                # Final attempt: examine page structure
                log_callback("Analyzing page structure for debugging...")
                
                # Get all div elements
                all_divs = browser_page.eles('div', timeout=3)
                log_callback(f"Total div elements on page: {len(all_divs)}")
                
                # Look for any data attributes
                data_elements = browser_page.eles('[data-sku]', timeout=2)
                log_callback(f"Elements with data-sku: {len(data_elements)}")
                
                # Look for any images
                all_images = browser_page.eles('img', timeout=2)
                log_callback(f"Total images on page: {len(all_images)}")
                
                # Sample a few images to see their alt text
                for i, img in enumerate(all_images[:10]):
                    alt = img.attr('alt') or 'No alt'
                    log_callback(f"Image {i+1} alt: {alt[:50]}...")
                
                log_callback("No SKU elements found with any method, trying fallback")
                return scrape_html_variants(product_url, log_callback, product_title)
        
        log_callback(f"Found {len(sku_elements)} SKU elements to process")
        
        # Process each SKU element
        for i, sku_element in enumerate(sku_elements[:10]):  # Limit to 10 variants
            try:
                log_callback(f"Processing variant {i+1}/{min(len(sku_elements), 10)}")
                
                # Extract variant info from the SKU element
                img_element = sku_element.ele('img', timeout=1)
                if not img_element:
                    continue
                
                variant_alt = img_element.attr('alt') or ''
                variant_image = img_element.attr('src') or ''
                sku_col = sku_element.attr('data-sku-col') or f"variant_{i}"
                
                if not variant_alt:
                    continue
                
                log_callback(f"Found variant: {variant_alt}")
                
                # Click on the variant to select it
                try:
                    sku_element.click()
                    time.sleep(1.5)  # Wait for price update
                except Exception as e:
                    log_callback(f"Could not click variant {variant_alt}: {e}")
                    continue
                
                # Extract current price after clicking
                price_selectors = [
                    '.price--current--I3Zeidd .price--currentPriceText--V8_y_b5',
                    '.product-price-current .product-price-value',
                    '.price--currentPriceText--V8_y_b5',
                    '[class*="current"] [class*="price"]'
                ]
                
                current_price = None
                for price_selector in price_selectors:
                    try:
                        price_element = browser_page.ele(price_selector, timeout=1)
                        if price_element:
                            current_price = price_element.text.strip()
                            break
                    except:
                        continue
                
                # Extract original price
                original_price_selectors = [
                    '.price--original--wEueRiZ .price--originalText--gxVO5_d',
                    '.price--originalText--gxVO5_d',
                    '[class*="original"] [class*="price"]'
                ]
                
                original_price = None
                for orig_selector in original_price_selectors:
                    try:
                        orig_element = browser_page.ele(orig_selector, timeout=1)
                        if orig_element:
                            original_price = orig_element.text.strip()
                            break
                    except:
                        continue
                
                # Extract variant name from color description
                color_selectors = [
                    'span:contains("Farbe:") + span',
                    '[class*="color"] span',
                    '.sku-property span'
                ]
                
                variant_name = variant_alt  # Fallback to alt text
                for color_selector in color_selectors:
                    try:
                        color_element = browser_page.ele(color_selector, timeout=1)
                        if color_element and color_element.text.strip():
                            variant_name = color_element.text.strip()
                            break
                    except:
                        continue
                
                # Clean up image URL
                if variant_image and not variant_image.startswith('http'):
                    variant_image = 'https:' + variant_image
                
                # Create variant data
                sku_id = f"{base_product_id}_interactive_{sku_col}"
                variant_data = {
                    'sku_id': sku_id,
                    'product_id': base_product_id,
                    'variant_title': variant_name,
                    'image_url': variant_image,
                    'alt_text': variant_alt,
                    'sale_price': current_price,
                    'original_price': original_price,
                    'source': 'interactive'
                }
                variants.append(variant_data)
                
                log_callback(f"Captured variant: {variant_name} - Price: {current_price}")
                
            except Exception as e:
                log_callback(f"Error processing variant {i}: {e}")
                continue
        
        browser_page.quit()
        
        log_callback(f"Successfully extracted {len(variants)} interactive variants")
        return variants
        
    except Exception as e:
        log_callback(f"Error in interactive variant scraping: {e}")
        # Fallback to simple HTML variant detection
        return scrape_html_variants(product_url, log_callback, product_title)

def scrape_html_variants(product_url, log_callback=default_logger, product_title=None):
    """
    Simple HTML variant detection (fallback method)
    """
    try:
        log_callback(f"HTML variant detection for: {product_url}")
        
        # Extract product ID from URL
        import re
        url_match = re.search(r'/item/(\d+)\.html', product_url)
        base_product_id = url_match.group(1) if url_match else None
        
        if not base_product_id:
            log_callback("Could not extract product ID from URL")
            return []
        
        # Enhanced variant detection based on product characteristics
        filament_keywords = ['filament', 'pla', 'petg', 'tpu', 'abs', '3d print', '3d-druck']
        
        # Check both URL and product title for filament keywords
        search_text = product_url.lower()
        if product_title:
            search_text += " " + product_title.lower()
        
        # Don't create fake variants! Return empty list if no real variants found
        log_callback("No real variants found - not creating fake demo variants")
        return []
        
    except Exception as e:
        log_callback(f"Error in HTML variant detection: {e}")
        return []

def extract_variant_from_alt_text(alt_text):
    """
    Extract variant information from alt text
    Examples: "PLA Orange" -> "PLA Orange", "PETG Silver" -> "PETG Silver"
    """
    if not alt_text:
        return None
    
    # Clean up the alt text
    cleaned = alt_text.strip()
    
    # Common patterns for material and color combinations
    material_colors = [
        'PLA', 'PETG', 'TPU', 'ABS', 'ASA', 'WOOD', 'SILK', 'MATTE'
    ]
    
    colors = [
        'Black', 'White', 'Red', 'Blue', 'Green', 'Yellow', 'Orange', 
        'Purple', 'Pink', 'Gray', 'Grey', 'Silver', 'Gold', 'Brown', 
        'Transparent', 'Clear', 'Beige'
    ]
    
    # Check if alt text contains material + color combination
    for material in material_colors:
        if material.upper() in cleaned.upper():
            for color in colors:
                if color.upper() in cleaned.upper():
                    return f"{material} {color}"
            
            # If material found but no specific color, return the full alt text
            return cleaned
    
    # If no material found, but contains color, return alt text
    for color in colors:
        if color.upper() in cleaned.upper():
            return cleaned
    
    # Return the original if it looks like a variant (not too long)
    if len(cleaned) <= 30:
        return cleaned
    
    return None

def scrape_real_product_variants(product_id, log_callback=default_logger):
    """
    Scrape real variants for a specific product using AliExpress API.
    Gets all SKU variants with individual prices for the same base product.
    """
    try:
        log_callback(f"Fetching real variants for product ID: {product_id}")
        
        # Initialize session if needed
        cookies, user_agent = initialize_session_data(f"product_{product_id}")
        session_page = SessionPage()
        session_page.set.cookies(cookies)
        
        # Try first to get the product page and extract initial data
        product_url = f'https://www.aliexpress.com/item/{product_id}.html'
        log_callback(f"Loading product page: {product_url}")
        
        try:
            session_page.get(product_url, timeout=30)
            if session_page.response.status_code != 200:
                log_callback(f"Failed to load product page. Status: {session_page.response.status_code}")
                return []
        except Exception as e:
            log_callback(f"Error loading product page: {e}")
            return []
        
        # Try to extract variant data from the loaded page
        try:
            page_html = session_page.html
            if not page_html:
                log_callback("No HTML content received")
                return []
            
            # Look for JSON data in script tags
            import re
            json_matches = re.findall(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', page_html, re.DOTALL)
            if not json_matches:
                json_matches = re.findall(r'window\.runParams\s*=\s*({.*?});', page_html, re.DOTALL)
            
            if json_matches:
                try:
                    import json
                    json_data = json.loads(json_matches[0])
                    log_callback("Successfully extracted JSON data from page")
                except json.JSONDecodeError as e:
                    log_callback(f"Failed to parse JSON data: {e}")
                    json_data = {}
            else:
                log_callback("No JSON data found in page, trying fallback methods")
                return []
                
        except Exception as e:
            log_callback(f"Error extracting data from page: {e}")
            return []
        
        # Try to extract SKU component data from the page JSON
        try:
            # Look for SKU component data in various possible locations
            sku_component = {}
            
            # Try multiple paths to find SKU data
            possible_paths = [
                ['data', 'skuComponent'],
                ['skuComponent'],
                ['globalData', 'skuComponent'],
                ['state', 'skuComponent']
            ]
            
            for path in possible_paths:
                temp_data = json_data
                for key in path:
                    if isinstance(temp_data, dict) and key in temp_data:
                        temp_data = temp_data[key]
                    else:
                        temp_data = None
                        break
                
                if temp_data:
                    sku_component = temp_data
                    log_callback(f"Found SKU component data at path: {' -> '.join(path)}")
                    break
            
            if not sku_component:
                log_callback("No SKU component found in page data")
                return []
            
            variants = []
            
            # Get product SKU property list for variant attributes
            sku_property_list = sku_component.get('productSKUPropertyList', [])
            
            # Get SKU price list for individual variant prices
            sku_price_list = sku_component.get('skuPriceList', [])
            
            log_callback(f"Found {len(sku_price_list)} SKU variants")
            
            for sku_price in sku_price_list:
                sku_id = sku_price.get('skuId')
                sku_attr = sku_price.get('skuAttr', '')
                
                # Extract variant attributes from skuAttr
                variant_attributes = parse_sku_attributes(sku_attr, sku_property_list)
                
                # Get variant image with improved extraction
                variant_image = None
                
                try:
                    # Try multiple image extraction methods
                    for prop in sku_property_list:
                        if 'skuPropertyValues' in prop:
                            for value in prop['skuPropertyValues']:
                                # Match SKU attribute with property value
                                if 'skuPropertyImagePath' in value:
                                    prop_id = str(prop.get('skuPropertyId', ''))
                                    value_id = str(value.get('propertyValueId', ''))
                                    if f"{prop_id}:{value_id}" in sku_attr:
                                        image_path = value['skuPropertyImagePath']
                                        if image_path:
                                            # Normalize image URL
                                            if image_path.startswith('//'):
                                                variant_image = 'https:' + image_path
                                            elif image_path.startswith('http'):
                                                variant_image = image_path
                                            else:
                                                variant_image = 'https://' + image_path
                                            log_callback(f"Found variant image: {variant_image}")
                                            break
                        if variant_image:
                            break
                    
                    # Fallback 1: Check for any image in sku properties
                    if not variant_image:
                        for prop in sku_property_list:
                            if 'skuPropertyValues' in prop:
                                for value in prop['skuPropertyValues']:
                                    if 'skuPropertyImagePath' in value and value['skuPropertyImagePath']:
                                        image_path = value['skuPropertyImagePath']
                                        if image_path.startswith('//'):
                                            variant_image = 'https:' + image_path
                                        elif image_path.startswith('http'):
                                            variant_image = image_path
                                        else:
                                            variant_image = 'https://' + image_path
                                        log_callback(f"Found fallback variant image: {variant_image}")
                                        break
                            if variant_image:
                                break
                    
                    # Fallback 2: try to get any image from the variant attributes
                    if not variant_image and variant_attributes:
                        for attr_value in variant_attributes.values():
                            if 'image' in str(attr_value).lower():
                                variant_image = attr_value
                                log_callback(f"Found attribute variant image: {variant_image}")
                                break
                    
                    if not variant_image:
                        log_callback(f"No variant image found for SKU {sku_id}")
                        
                except Exception as e:
                    log_callback(f"Error extracting variant image for SKU {sku_id}: {e}")
                    variant_image = None
                
                # Extract prices with proper formatting and validation
                sku_val = sku_price.get('skuVal', {})
                
                # Try multiple price fields for sale price
                sale_price = (
                    sku_val.get('skuCalPrice') or 
                    sku_val.get('actSkuCalPrice') or 
                    sku_val.get('skuAmount') or
                    sku_val.get('skuMultiCurrencyCalPrice') or
                    sku_val.get('skuPrice')
                )
                
                # Try multiple price fields for original price
                original_price = (
                    sku_val.get('skuPrice') or 
                    sku_val.get('skuMultiCurrencyCalPrice') or
                    sku_val.get('skuCalPrice')
                )
                
                discount = sku_val.get('discount')
                
                # Validate and convert prices with better error handling
                try:
                    if sale_price is not None:
                        if isinstance(sale_price, (int, float)):
                            sale_price = f"€ {sale_price:.2f}"
                        elif isinstance(sale_price, str):
                            # Try to extract numeric value from string
                            price_match = re.search(r'[\d.,]+', str(sale_price))
                            if price_match:
                                price_num = float(price_match.group().replace(',', '.'))
                                sale_price = f"€ {price_num:.2f}"
                            else:
                                sale_price = str(sale_price)
                        else:
                            sale_price = str(sale_price)
                        log_callback(f"Extracted sale price: {sale_price}")
                    else:
                        log_callback(f"No sale price found for SKU {sku_id}")
                        sale_price = None
                        
                    if original_price is not None:
                        if isinstance(original_price, (int, float)):
                            original_price = f"€ {original_price:.2f}"
                        elif isinstance(original_price, str):
                            # Try to extract numeric value from string
                            price_match = re.search(r'[\d.,]+', str(original_price))
                            if price_match:
                                price_num = float(price_match.group().replace(',', '.'))
                                original_price = f"€ {price_num:.2f}"
                            else:
                                original_price = str(original_price)
                        else:
                            original_price = str(original_price)
                        log_callback(f"Extracted original price: {original_price}")
                    else:
                        original_price = sale_price  # Use sale price as fallback
                        log_callback(f"Using sale price as original price fallback: {original_price}")
                        
                except Exception as e:
                    log_callback(f"Error processing prices for SKU {sku_id}: {e}")
                    sale_price = None
                    original_price = None
                
                variant_data = {
                    'sku_id': sku_id,
                    'product_id': str(product_id),
                    'variant_title': ', '.join(variant_attributes.values()) if variant_attributes else None,
                    'variant_attributes': variant_attributes,
                    'image_url': variant_image,
                    'sale_price': sale_price,
                    'original_price': original_price,
                    'discount_percentage': discount,
                    'availability': sku_val.get('availability')
                }
                
                variants.append(variant_data)
            
            log_callback(f"Successfully extracted {len(variants)} variants")
            return variants
            
        except json.JSONDecodeError:
            log_callback("Failed to decode JSON response")
            return []
        except Exception as e:
            log_callback(f"Error processing variant data: {e}")
            return []
            
    except Exception as e:
        log_callback(f"Error scraping variants: {e}")
        return []

def parse_sku_attributes(sku_attr, property_list):
    """
    Parse SKU attributes string and map to human-readable values.
    Example: "14:173,5:100014064#Black;14:365,200000463:100007326#2 Wheels"
    Returns: {"Color": "Black", "Type": "2 Wheels"}
    """
    attributes = {}
    
    if not sku_attr or not property_list:
        return attributes
    
    try:
        # Parse attribute pairs
        for attr_pair in sku_attr.split(';'):
            if '#' in attr_pair:
                attr_ids, display_name = attr_pair.split('#', 1)
                
                # Find property name for this attribute
                for prop in property_list:
                    prop_id = str(prop.get('skuPropertyId', ''))
                    if prop_id in attr_ids:
                        prop_name = prop.get('skuPropertyName', f"Attribute_{prop_id}")
                        attributes[prop_name] = display_name
                        break
    
    except Exception:
        # Fallback: just use the display values
        for attr_pair in sku_attr.split(';'):
            if '#' in attr_pair:
                display_name = attr_pair.split('#')[1]
                attributes[f"Variant_{len(attributes)}"] = display_name
    
    return attributes

def scrape_product_variants(product_url, log_callback=default_logger):
    """
    Legacy function - now redirects to real variant scraping
    """
    try:
        # Extract product ID from URL
        import re
        match = re.search(r'/item/(\d+)\.html', product_url)
        if match:
            product_id = match.group(1)
            return scrape_real_product_variants(product_id, log_callback)
        else:
            log_callback(f"Could not extract product ID from URL: {product_url}")
            return []
        
    except Exception as e:
        log_callback(f"Error scraping variants: {e}")
        return []

def parse_static_variant_html(html_content, product_id, log_callback=default_logger):
    """
    Parse static HTML content for variant information using the specific 
    data-sku-col structure provided by the user.
    """
    try:
        import re
        
        log_callback("Parsing static HTML for variant information")
        
        # Extract all variant divs with data-sku-col attributes
        # Updated pattern to handle the actual HTML structure better
        variant_pattern = r'<div[^>]*data-sku-col="([^"]+)"[^>]*>.*?<img[^>]*src="([^"]+)"[^>]*alt="([^"]+)"[^>]*>.*?</div>'
        
        matches = re.findall(variant_pattern, html_content, re.DOTALL | re.IGNORECASE)
        
        log_callback(f"Found {len(matches)} variant matches with primary pattern")
        
        # If no matches found, try alternative patterns
        if not matches:
            # Try more flexible pattern
            alt_pattern = r'data-sku-col="([^"]+)"[^>]*>.*?<img[^>]*src="([^"]+)"[^>]*alt="([^"]+)"'
            matches = re.findall(alt_pattern, html_content, re.DOTALL | re.IGNORECASE)
            log_callback(f"Found {len(matches)} variant matches with alternative pattern")
            
        if not matches:
            # Try even more flexible pattern
            loose_pattern = r'data-sku-col="([^"]+)".*?src="([^"]+)".*?alt="([^"]+)"'
            matches = re.findall(loose_pattern, html_content, re.DOTALL | re.IGNORECASE)
            log_callback(f"Found {len(matches)} variant matches with loose pattern")
        
        variants = []
        for match in matches:
            sku_col, image_url, alt_text = match
            
            # Clean up image URL
            if image_url and not image_url.startswith('http'):
                if image_url.startswith('//'):
                    image_url = 'https:' + image_url
                else:
                    image_url = 'https://' + image_url
            
            # Extract variant name from alt text
            variant_name = extract_variant_from_alt_text(alt_text)
            if not variant_name:
                variant_name = alt_text
            
            # Create variant data
            sku_id = f"{product_id}_{sku_col}"
            variant_data = {
                'sku_id': sku_id,
                'product_id': product_id,
                'variant_title': variant_name,
                'image_url': image_url,
                'alt_text': alt_text,
                'sku_col': sku_col,
                'source': 'static_html_parse'
            }
            
            variants.append(variant_data)
            log_callback(f"Extracted static variant: {variant_name} (SKU: {sku_col})")
        
        log_callback(f"Successfully parsed {len(variants)} variants from static HTML")
        return variants
        
    except Exception as e:
        log_callback(f"Error parsing static HTML variants: {e}")
        return []

def extract_variant_from_sku_alt(alt_text):
    """
    Extract variant information from SKU alt text
    Examples: "PETG 2RD2BLBK", "PLAp 2BK2WTGY", "SILK BKWTSVRCLG"
    """
    if not alt_text:
        return None
    
    # Common patterns in ALT text
    patterns = [
        r'^(PETG|PLA|PLAp|ABS|TPU|SILK|HS\s+PETG|HS\s+Matte\s+PLA|HS\s+PLAp)',  # Material type
        r'(\d+M)',  # Meters
        r'(\d+kg|\d+g)',  # Weight
        r'(BK|WT|RD|BL|GY|GN|YL|OR|PK|SV|CL)',  # Color codes
    ]
    
    # Try to extract the main material/type
    for pattern in patterns:
        match = re.search(pattern, alt_text, re.IGNORECASE)
        if match:
            variant = match.group(1)
            
            # Clean up the variant name
            if variant.upper().startswith('HS '):
                variant = variant[3:].strip()  # Remove "HS " prefix
            
            return variant
    
    # If no pattern matches, try the first word
    words = alt_text.split()
    if words:
        return words[0]
    
    return None


if __name__ == "__main__":
    # Get keyword from user
    search_keyword_input = input("Enter the product to search for on AliExpress: ").strip()

    if not search_keyword_input:
        print("Error: No search product provided. Exiting.")
    else:
        num_pages_to_scrape = 0
        while True:
            try:
                num_pages_input = input("Enter the number of pages to scrape (1-60): ").strip()
                if not num_pages_input.isdigit():
                    print("Invalid input. Please enter a number.")
                    continue

                num_pages_to_scrape = int(num_pages_input)
                if 1 <= num_pages_to_scrape <= 60:
                    break
                else:
                    print("Invalid number. Please enter a number between 1 and 60.")
            except ValueError:
                print("Invalid input. Please enter a number.")

        fresh_cookies, fresh_user_agent = initialize_session_data(search_keyword_input)
        raw_products = scrape_aliexpress_data(search_keyword_input, num_pages_to_scrape,
                                             fresh_cookies, fresh_user_agent)
        all_fields_for_direct_run = [
            'Product ID', 'Title', 'Sale Price', 'Original Price', 'Discount (%)',
            'Currency', 'Rating', 'Orders Count', 'Store Name', 'Store ID',
            'Store URL', 'Product URL', 'Image URL'
        ]
        extracted_products = extract_product_details(raw_products, all_fields_for_direct_run)
        save_results(search_keyword_input, extracted_products, all_fields_for_direct_run)
        print("\nScript finished.")
