#!/usr/bin/env python3
"""
Improved AliExpress Scraper
Based on analysis of current AliExpress anti-bot systems and CSR architecture
"""

import time
import json
import os
from urllib.parse import quote_plus
from DrissionPage import WebPage, SessionPage, ChromiumOptions
from datetime import datetime, timedelta
from typing import Generator, Optional, Dict, List, Any
import re

# Constants
API_URL = 'https://www.aliexpress.com/fn/search-pc/index'
RESULTS_DIR = "results"
SESSION_CACHE_FILE = "session_cache.json"
CACHE_EXPIRATION_SECONDS = 30 * 60


def enhanced_browser_stealth(headless=False):
    """
    Enhanced browser configuration with better anti-detection

    Args:
        headless: If True, uses headless mode (may be detected)

    Returns:
        ChromiumOptions configured for stealth
    """
    co = ChromiumOptions()

    # CRITICAL: Don't use headless for session initialization
    # AliExpress detects headless browsers aggressively
    if headless:
        co.headless()

    # Core stealth features
    co.set_argument('--disable-blink-features=AutomationControlled')
    co.set_argument('--disable-web-security')
    co.set_argument('--disable-features=IsolateOrigins,site-per-process')
    co.set_argument('--disable-site-isolation-trials')

    # Window configuration
    co.set_argument('--window-size=1920,1080')
    co.set_argument('--start-maximized')

    # WebGL/Canvas fingerprinting bypass
    co.set_argument('--use-gl=swiftshader')
    co.set_argument('--enable-webgl')

    # Remove automation indicators
    co.set_argument('--excludeSwitches', 'enable-automation')
    co.set_pref('credentials_enable_service', False)
    co.set_pref('profile.password_manager_enabled', False)

    # Realistic user agent
    user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    co.set_user_agent(user_agent)

    return co


def wait_for_csr_data(browser_page, timeout=30, log_callback=print):
    """
    Wait for Client-Side Rendering data to fully load

    AliExpress uses CSR heavily, so we need to wait for JavaScript
    to populate the page with actual product data.

    Args:
        browser_page: DrissionPage WebPage instance
        timeout: Maximum wait time in seconds
        log_callback: Function for logging messages

    Returns:
        True if data loaded successfully, False otherwise
    """
    start_time = time.time()
    check_interval = 1

    log_callback("⏳ Waiting for CSR data to load...")

    indicators_found = set()

    while time.time() - start_time < timeout:
        html = browser_page.html

        # Check 1: Product images loaded
        if 'imagePathList' in html:
            indicators_found.add('images')

        # Check 2: Product title present
        try:
            title_selectors = [
                '[data-pl=product-title]',
                '.title--line-one--nU9Qtto',
                'h1[class*="title"]',
            ]
            for selector in title_selectors:
                title_elem = browser_page.ele(selector, timeout=0.5)
                if title_elem and title_elem.text.strip():
                    indicators_found.add('title')
                    break
        except:
            pass

        # Check 3: Price elements loaded
        try:
            price_selectors = [
                '[class*="price"]',
                '.price--currentPriceText--V8_y_b5',
                '.product-price-value',
            ]
            for selector in price_selectors:
                price_elem = browser_page.ele(selector, timeout=0.5)
                if price_elem and price_elem.text.strip():
                    indicators_found.add('price')
                    break
        except:
            pass

        # Check 4: SKU/Variant elements
        try:
            sku_elem = browser_page.ele('[data-sku-col]', timeout=0.5)
            if sku_elem:
                indicators_found.add('sku')
        except:
            pass

        # Success criteria: At least 2 indicators found
        if len(indicators_found) >= 2:
            log_callback(f"✓ CSR data loaded ({', '.join(indicators_found)})")
            return True

        log_callback(f"  Waiting... ({', '.join(indicators_found)})")
        time.sleep(check_interval)

    log_callback(f"⚠ Timeout waiting for CSR data (found: {', '.join(indicators_found)})")
    return False


def smart_wait_for_element(browser_page, selectors, timeout=20, log_callback=print):
    """
    Intelligently wait for multiple possible selectors

    Args:
        browser_page: DrissionPage WebPage instance
        selectors: List of CSS selectors to try
        timeout: Maximum wait time
        log_callback: Logging function

    Returns:
        Tuple of (element, selector_used) or (None, None)
    """
    start_time = time.time()
    check_interval = 0.5

    while time.time() - start_time < timeout:
        for selector in selectors:
            try:
                elem = browser_page.ele(selector, timeout=check_interval)
                if elem and elem.text.strip():
                    log_callback(f"  ✓ Found element with: {selector}")
                    return elem, selector
            except:
                continue

        time.sleep(check_interval)

    log_callback(f"  ✗ No element found from {len(selectors)} selectors")
    return None, None


def initialize_session_improved(keyword, headless=False, log_callback=print):
    """
    Improved session initialization with better anti-detection

    Args:
        keyword: Search keyword for initial page visit
        headless: Whether to use headless mode (False recommended)
        log_callback: Logging function

    Returns:
        Tuple of (cookies, user_agent)
    """
    log_callback(f"🔧 Initializing improved session for: '{keyword}'")

    # Check cache first
    if os.path.exists(SESSION_CACHE_FILE):
        try:
            with open(SESSION_CACHE_FILE, 'r') as f:
                cached_data = json.load(f)

            saved_timestamp = cached_data.get('timestamp', 0)
            current_timestamp = time.time()
            cache_age = current_timestamp - saved_timestamp

            if cache_age < CACHE_EXPIRATION_SECONDS:
                log_callback(f"✓ Using cached session (age: {int(cache_age)}s)")
                return cached_data['cookies'], cached_data['user_agent']
            else:
                log_callback(f"⚠ Cache expired (age: {int(cache_age)}s)")
        except Exception as e:
            log_callback(f"⚠ Cache read error: {e}")

    # Create fresh session
    log_callback("🌐 Creating fresh session with browser...")

    co = enhanced_browser_stealth(headless=headless)
    browser_page = WebPage(chromium_options=co)
    browser_page.set.load_mode.eager()

    try:
        search_url = f'https://www.aliexpress.com/w/wholesale-{quote_plus(keyword)}.html'
        log_callback(f"📡 Visiting: {search_url}")

        browser_page.get(search_url, timeout=30)

        # Wait for page to settle
        log_callback("⏳ Waiting for page to load...")
        time.sleep(5)

        # Extract session data
        fresh_cookies = browser_page.cookies().as_dict()
        fresh_user_agent = browser_page.user_agent

        log_callback(f"✓ Session created")
        log_callback(f"  User-Agent: {fresh_user_agent[:50]}...")
        log_callback(f"  Cookies: {len(fresh_cookies)} items")

        # Cache the session
        cache_content = {
            'timestamp': time.time(),
            'cookies': fresh_cookies,
            'user_agent': fresh_user_agent
        }

        try:
            with open(SESSION_CACHE_FILE, 'w') as f:
                json.dump(cache_content, f, indent=4)
            log_callback("✓ Session cached")
        except IOError as e:
            log_callback(f"⚠ Cache write error: {e}")

        return fresh_cookies, fresh_user_agent

    except Exception as e:
        log_callback(f"✗ Session initialization failed: {e}")
        raise

    finally:
        if browser_page:
            browser_page.quit()


def enhanced_variant_detection(browser_page, product_id, log_callback=print):
    """
    Multi-source approach to variant detection

    Tries multiple methods:
    1. CSR data from window._d_c_.DCData
    2. Dynamically rendered SKU elements
    3. API call for SKU data

    Args:
        browser_page: DrissionPage WebPage instance
        product_id: AliExpress product ID
        log_callback: Logging function

    Returns:
        List of variant dictionaries
    """
    variants = []

    # Method 1: Extract from window._d_c_.DCData
    log_callback("🔍 Method 1: Checking CSR data...")
    try:
        dc_data_script = """
        return window._d_c_ && window._d_c_.DCData
            ? JSON.stringify(window._d_c_.DCData)
            : null;
        """
        dc_data_json = browser_page.run_js(dc_data_script)

        if dc_data_json:
            dc_data = json.loads(dc_data_json)
            log_callback(f"  ✓ Found DCData: {list(dc_data.keys())}")

            # Extract image paths as variant indicators
            if 'imagePathList' in dc_data:
                image_list = dc_data['imagePathList']
                log_callback(f"  ✓ Found {len(image_list)} images")

                # Each image might represent a variant
                for idx, img_url in enumerate(image_list):
                    variants.append({
                        'sku_id': f"{product_id}_dcdata_{idx}",
                        'product_id': product_id,
                        'image_url': img_url,
                        'variant_title': f"Variant {idx + 1}",
                        'source': 'dcdata_images'
                    })
    except Exception as e:
        log_callback(f"  ✗ DCData extraction failed: {e}")

    # Method 2: Dynamically rendered SKU elements
    log_callback("🔍 Method 2: Checking SKU elements...")
    try:
        time.sleep(3)  # Give time for rendering

        sku_selectors = [
            '[data-sku-col]',
            '.sku-item--image--jMUnnGA',
            '[class*="sku-item"]',
        ]

        for selector in sku_selectors:
            elements = browser_page.eles(selector, timeout=2)
            if elements:
                log_callback(f"  ✓ Found {len(elements)} SKU elements with: {selector}")

                for idx, elem in enumerate(elements[:20]):  # Limit to 20
                    try:
                        img = elem.ele('img', timeout=1)
                        if img:
                            variants.append({
                                'sku_id': elem.attr('data-sku-col') or f"{product_id}_sku_{idx}",
                                'product_id': product_id,
                                'image_url': img.attr('src'),
                                'variant_title': img.attr('alt') or f"Variant {idx + 1}",
                                'source': 'sku_elements'
                            })
                    except:
                        continue
                break
    except Exception as e:
        log_callback(f"  ✗ SKU element extraction failed: {e}")

    # Deduplicate
    unique_variants = {}
    for variant in variants:
        sku_id = variant.get('sku_id')
        if sku_id and sku_id not in unique_variants:
            unique_variants[sku_id] = variant

    result = list(unique_variants.values())
    log_callback(f"✓ Total unique variants found: {len(result)}")

    return result


def scrape_product_improved(product_url, headless=False, log_callback=print):
    """
    Improved product scraping with all best practices

    Args:
        product_url: URL of product page
        headless: Use headless mode (False recommended)
        log_callback: Logging function

    Returns:
        Dictionary with product data
    """
    log_callback(f"\n{'='*80}")
    log_callback(f"IMPROVED PRODUCT SCRAPING")
    log_callback(f"{'='*80}")
    log_callback(f"URL: {product_url}")

    # Extract product ID
    match = re.search(r'/item/(\d+)\.html', product_url)
    if not match:
        log_callback("✗ Could not extract product ID from URL")
        return {'success': False, 'error': 'Invalid URL'}

    product_id = match.group(1)
    log_callback(f"Product ID: {product_id}")

    # Setup browser
    co = enhanced_browser_stealth(headless=headless)
    browser = WebPage(chromium_options=co)
    browser.set.load_mode.eager()

    try:
        # Load page
        log_callback("\n📡 Loading product page...")
        start_time = time.time()
        browser.get(product_url, timeout=30)
        load_time = time.time() - start_time
        log_callback(f"✓ Page loaded in {load_time:.2f}s")

        # Wait for CSR data
        log_callback("\n⏳ Waiting for CSR data...")
        csr_loaded = wait_for_csr_data(browser, timeout=30, log_callback=log_callback)

        if not csr_loaded:
            log_callback("⚠ CSR data not fully loaded, continuing anyway...")

        # Extract title
        log_callback("\n📝 Extracting product details...")
        title_selectors = [
            '[data-pl=product-title]',
            '.title--line-one--nU9Qtto',
            'h1[class*="title"]',
        ]
        title_elem, title_selector = smart_wait_for_element(
            browser, title_selectors, timeout=10, log_callback=log_callback
        )
        title = title_elem.text.strip() if title_elem else None

        # Extract price
        price_selectors = [
            '.price--currentPriceText--V8_y_b5',
            '.product-price-value',
            '[class*="currentPrice"]',
            '[class*="price"][class*="current"]',
        ]
        price_elem, price_selector = smart_wait_for_element(
            browser, price_selectors, timeout=10, log_callback=log_callback
        )
        price = price_elem.text.strip() if price_elem else None

        # Extract variants
        log_callback("\n🎨 Detecting variants...")
        variants = enhanced_variant_detection(browser, product_id, log_callback=log_callback)

        # Compile result
        result = {
            'success': True,
            'product_id': product_id,
            'title': title,
            'price': price,
            'variants': variants,
            'variants_count': len(variants),
            'load_time': load_time,
            'csr_loaded': csr_loaded,
            'timestamp': datetime.utcnow().isoformat()
        }

        log_callback(f"\n{'='*80}")
        log_callback(f"✅ SCRAPING COMPLETE")
        log_callback(f"{'='*80}")
        log_callback(f"Title: {title[:60]}..." if title else "Title: None")
        log_callback(f"Price: {price}")
        log_callback(f"Variants: {len(variants)}")
        log_callback(f"{'='*80}\n")

        return result

    except Exception as e:
        log_callback(f"\n✗ Scraping failed: {e}")
        import traceback
        log_callback(traceback.format_exc())
        return {'success': False, 'error': str(e)}

    finally:
        browser.quit()


def test_improved_scraper():
    """
    Test the improved scraper
    """
    print("\n" + "="*80)
    print("TESTING IMPROVED ALIEXPRESS SCRAPER")
    print("="*80 + "\n")

    # Test 1: Session initialization
    print("TEST 1: Session Initialization")
    print("-" * 80)
    try:
        cookies, user_agent = initialize_session_improved(
            "3d printer filament",
            headless=False,  # Use visible browser for better success rate
            log_callback=print
        )
        print("✅ Session initialization successful\n")
    except Exception as e:
        print(f"❌ Session initialization failed: {e}\n")
        return

    # Test 2: Product scraping
    print("\nTEST 2: Product Scraping")
    print("-" * 80)
    test_url = "https://www.aliexpress.com/item/1005008204179129.html"

    result = scrape_product_improved(
        test_url,
        headless=False,  # Use visible browser
        log_callback=print
    )

    if result['success']:
        print("\n✅ Product scraping successful")

        # Save result
        output_file = "improved_scraper_test_result.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"✓ Result saved to: {output_file}")
    else:
        print(f"\n❌ Product scraping failed: {result.get('error')}")

    print("\n" + "="*80)
    print("TESTING COMPLETE")
    print("="*80 + "\n")


if __name__ == "__main__":
    test_improved_scraper()
