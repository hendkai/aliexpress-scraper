#!/usr/bin/env python3
"""
Separate file with improved variant detection and detailed logging
"""

import time
import re
from DrissionPage import WebPage, ChromiumOptions
import random

def scrape_variants_with_detailed_logging(product_url, log_callback):
    """
    Enhanced variant scraping with maximum anti-bot stealth and detailed logging
    """
    try:
        log_callback("=" * 60)
        log_callback("🔍 ENHANCED VARIANT SCRAPING WITH DETAILED LOGGING")
        log_callback("=" * 60)
        log_callback(f"📍 Target URL: {product_url}")
        
        # Extract product ID from URL
        url_match = re.search(r'/item/(\d+)\.html', product_url)
        base_product_id = url_match.group(1) if url_match else None
        
        if not base_product_id:
            log_callback("❌ ERROR: Could not extract product ID from URL")
            return []
        
        log_callback(f"🆔 Product ID: {base_product_id}")
        
        # MAXIMUM ANTI-BOT STEALTH CONFIGURATION
        log_callback("🛡️  ANTI-BOT: Configuring maximum stealth browser")
        co = ChromiumOptions()
        
        # CRITICAL: Don't block images or CSS - AliExpress detects this
        co.no_imgs(False)
        log_callback("✅ ANTI-BOT: Images enabled (critical for stealth)")
        
        # Use headless mode for server environment
        co.headless()  # Required for server deployment
        log_callback("✅ ANTI-BOT: Headless mode enabled for server environment")
        
        # Enhanced stealth user agent
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
        co.set_user_agent(user_agent)
        log_callback(f"✅ ANTI-BOT: User agent set: {user_agent[:50]}...")
        
        # Advanced anti-detection arguments
        stealth_args = [
            '--disable-blink-features=AutomationControlled',
            '--excludeSwitches=enable-automation',
            '--disable-extensions',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-web-security',
            '--window-size=1920,1080',
            '--start-maximized'
        ]
        
        for arg in stealth_args:
            co.set_argument(arg)
        
        log_callback(f"✅ ANTI-BOT: {len(stealth_args)} stealth arguments applied")
        
        # Stealth preferences
        stealth_prefs = {
            'credentials_enable_service': False,
            'profile.password_manager_enabled': False,
            'profile.default_content_setting_values.notifications': 2,
            'useAutomationExtension': False
        }
        
        for pref, value in stealth_prefs.items():
            co.set_pref(pref, value)
        
        log_callback(f"✅ ANTI-BOT: {len(stealth_prefs)} stealth preferences set")
        
        # Initialize browser
        log_callback("🚀 ANTI-BOT: Launching stealth browser...")
        browser_page = WebPage(chromium_options=co)
        browser_page.set.load_mode.eager()
        
        # Inject stealth JavaScript
        stealth_js = """
        // Remove webdriver property
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });
        
        // Mock chrome runtime
        window.chrome = {
            runtime: {}
        };
        
        // Mock plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
        });
        
        // Mock languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
        });
        """
        
        # Human-like behavior simulation
        log_callback("🤖 HUMAN SIMULATION: Adding random delays...")
        initial_delay = random.uniform(3, 8)
        log_callback(f"⏱️  HUMAN SIMULATION: Waiting {initial_delay:.1f}s before loading...")
        time.sleep(initial_delay)
        
        # Load the page
        log_callback("📥 LOADING: Fetching product page...")
        browser_page.get(product_url, timeout=30)
        
        # Execute stealth JavaScript
        try:
            browser_page.run_js(stealth_js)
            log_callback("✅ STEALTH: JavaScript injection successful")
        except Exception as e:
            log_callback(f"⚠️  STEALTH: JavaScript injection failed: {e}")
        
        # Human reading simulation
        reading_delay = random.uniform(5, 10)
        log_callback(f"📖 HUMAN SIMULATION: Simulating reading time ({reading_delay:.1f}s)...")
        time.sleep(reading_delay)
        
        # Human-like scrolling
        log_callback("📜 HUMAN SIMULATION: Performing human-like scrolling...")
        try:
            for i in range(3):
                scroll_amount = random.randint(200, 500)
                browser_page.scroll.down(scroll_amount)
                time.sleep(random.uniform(0.8, 2.0))
                log_callback(f"📜 SCROLL: Down {scroll_amount}px (step {i+1}/3)")
            
            # Scroll to variant section
            browser_page.scroll.to_half()
            time.sleep(random.uniform(2, 4))
            log_callback("📜 SCROLL: Positioned at page middle (variant section)")
            
        except Exception as e:
            log_callback(f"⚠️  SCROLL: Scrolling failed: {e}")
        
        # Wait for dynamic content with detailed progress
        log_callback("⏳ CONTENT LOADING: Waiting for dynamic content...")
        max_wait_time = 120  # 2 minutes maximum
        check_interval = 5   # Check every 5 seconds
        content_loaded = False
        
        for i in range(max_wait_time // check_interval):
            time.sleep(check_interval)
            
            # Check for various page readiness indicators
            indicators = []
            
            # Check for price elements
            try:
                price_elements = browser_page.eles('.price--currentPriceText--V8_y_b5, .product-price-value', timeout=1)
                if price_elements:
                    indicators.append(f"price({len(price_elements)})")
            except:
                pass
            
            # Check for variant elements
            try:
                variant_elements = browser_page.eles('[data-sku-col], .sku-item--image--jMUnnGA', timeout=1)
                if variant_elements:
                    indicators.append(f"variants({len(variant_elements)})")
            except:
                pass
            
            # Check for product content
            try:
                content_elements = browser_page.eles('.product-container, .product-detail', timeout=1)
                if content_elements:
                    indicators.append("content")
            except:
                pass
            
            # Check for images
            try:
                images = browser_page.eles('img[alt*="color"], img[alt*="Color"], img[alt*="kg"]', timeout=1)
                if images:
                    indicators.append(f"images({len(images)})")
            except:
                pass
            
            elapsed_time = (i + 1) * check_interval
            log_callback(f"⏳ LOADING ({elapsed_time}s): {', '.join(indicators) if indicators else 'waiting...'}")
            
            # Page is ready if we have variants
            if any("variants" in indicator for indicator in indicators):
                content_loaded = True
                log_callback(f"✅ CONTENT: Dynamic content loaded after {elapsed_time} seconds")
                break
            
            # Trigger additional loading every 30 seconds
            if elapsed_time % 30 == 0:
                log_callback(f"🔄 TRIGGER: Attempting to trigger more content loading...")
                try:
                    # Mouse movement simulation
                    browser_page.run_js("""
                        const event = new MouseEvent('mousemove', {
                            clientX: Math.random() * window.innerWidth,
                            clientY: Math.random() * window.innerHeight,
                            bubbles: true
                        });
                        document.dispatchEvent(event);
                    """)
                    
                    # Random scroll
                    if random.choice([True, False]):
                        browser_page.scroll.up(random.randint(100, 300))
                    else:
                        browser_page.scroll.down(random.randint(100, 300))
                    
                    time.sleep(2)
                except:
                    pass
        
        if not content_loaded:
            log_callback("⚠️  WARNING: Dynamic content may not be fully loaded!")
        
        # Additional wait for final rendering
        log_callback("⏱️  FINAL WAIT: Allowing time for final rendering...")
        time.sleep(8)
        
        # Extract HTML for analysis
        log_callback("📄 HTML EXTRACTION: Getting page HTML...")
        page_html = browser_page.html
        
        if not page_html:
            log_callback("❌ ERROR: No HTML content available")
            browser_page.quit()
            return []
        
        log_callback(f"📄 HTML: Content length: {len(page_html)} characters")
        
        # Save HTML for debugging
        debug_file = f"variant_debug_{base_product_id}.html"
        try:
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(page_html)
            log_callback(f"💾 DEBUG: HTML saved to {debug_file}")
        except Exception as e:
            log_callback(f"⚠️  DEBUG: Could not save HTML: {e}")
        
        # Detailed HTML analysis
        log_callback("🔍 HTML ANALYSIS: Analyzing page structure...")
        
        # Check for anti-bot indicators
        anti_bot_patterns = [
            r'robot', r'captcha', r'verification', r'blocked', 
            r'access denied', r'security check', r'please wait'
        ]
        
        anti_bot_found = []
        for pattern in anti_bot_patterns:
            if re.search(pattern, page_html, re.IGNORECASE):
                anti_bot_found.append(pattern)
        
        if anti_bot_found:
            log_callback(f"🚨 ANTI-BOT DETECTED: Found indicators: {', '.join(anti_bot_found)}")
        else:
            log_callback("✅ ANTI-BOT: No anti-bot indicators detected")
        
        # Check for content indicators
        content_patterns = [
            r'aliexpress', r'product', r'price', r'add.*cart', r'buy.*now'
        ]
        
        content_found = 0
        for pattern in content_patterns:
            if re.search(pattern, page_html, re.IGNORECASE):
                content_found += 1
        
        log_callback(f"📊 CONTENT: Found {content_found}/{len(content_patterns)} content indicators")
        
        if content_found < 2:
            log_callback("⚠️  WARNING: Page may not be properly loaded or is blocked")
        
        # Variant detection with multiple patterns
        log_callback("🔍 VARIANT DETECTION: Searching for variants...")
        
        variant_patterns = [
            r'data-sku-col="(14-[^"]*)"',  # Specific AliExpress pattern
            r'data-sku-col="([^"]*)"',     # General pattern
            r'sku-item--image--jMUnnGA',   # Class pattern
            r'sku-item--skus--StEhULs'     # Container pattern
        ]
        
        all_variants = []
        for i, pattern in enumerate(variant_patterns):
            matches = re.findall(pattern, page_html, re.IGNORECASE)
            log_callback(f"🔍 PATTERN {i+1}: '{pattern}' found {len(matches)} matches")
            if matches and i < 2:  # Only use SKU patterns for actual variants
                all_variants.extend(matches)
        
        # Remove duplicates
        unique_variants = list(dict.fromkeys(all_variants))
        log_callback(f"🎯 VARIANTS: Found {len(unique_variants)} unique variants: {unique_variants[:10]}")
        
        # Image analysis
        log_callback("🖼️  IMAGE ANALYSIS: Searching for variant images...")
        
        img_pattern = r'<img[^>]*src="([^"]+)"[^>]*alt="([^"]+)"[^>]*>'
        img_matches = re.findall(img_pattern, page_html, re.IGNORECASE)
        
        variant_keywords = [
            'pla', 'petg', 'tpu', 'black', 'white', 'red', 'blue', 'green', 
            'yellow', 'orange', 'purple', 'pink', 'kg', 'color', 'bk', 'wt'
        ]
        
        variant_images = []
        for src, alt in img_matches:
            if any(keyword in alt.lower() for keyword in variant_keywords):
                variant_images.append((src, alt))
        
        log_callback(f"🖼️  IMAGES: Found {len(variant_images)} variant images")
        for i, (src, alt) in enumerate(variant_images[:5]):
            log_callback(f"🖼️  IMAGE {i+1}: {alt} -> {src[:50]}...")
        
        # Create variant data
        variants = []
        for i, sku_col in enumerate(unique_variants):
            try:
                # Find matching image
                variant_image = None
                variant_alt = None
                
                if i < len(variant_images):
                    variant_image = variant_images[i][0]
                    variant_alt = variant_images[i][1]
                    
                    # Clean up image URL
                    if variant_image and not variant_image.startswith('http'):
                        if variant_image.startswith('//'):
                            variant_image = 'https:' + variant_image
                        else:
                            variant_image = 'https://' + variant_image
                
                # Extract variant name
                variant_name = variant_alt or f"Variant {sku_col}"
                
                # Create variant data
                variant_data = {
                    'sku_id': f"{base_product_id}_{sku_col}",
                    'product_id': base_product_id,
                    'variant_title': variant_name,
                    'image_url': variant_image,
                    'alt_text': variant_alt,
                    'sku_col': sku_col,
                    'source': 'detailed_logging_scraper'
                }
                
                variants.append(variant_data)
                log_callback(f"✅ VARIANT {i+1}: {variant_name} (SKU: {sku_col})")
                
            except Exception as e:
                log_callback(f"❌ ERROR processing variant {sku_col}: {e}")
                continue
        
        browser_page.quit()
        
        log_callback("=" * 60)
        if variants:
            log_callback(f"🎉 SUCCESS: Extracted {len(variants)} variants!")
            for i, variant in enumerate(variants):
                log_callback(f"🎯 VARIANT {i+1}: {variant['variant_title']} (SKU: {variant['sku_col']})")
        else:
            log_callback("❌ FAILURE: No variants found")
        log_callback("=" * 60)
        
        return variants
        
    except Exception as e:
        log_callback(f"💥 CRITICAL ERROR: {e}")
        try:
            browser_page.quit()
        except:
            pass
        return []

if __name__ == "__main__":
    # Test the improved variant detection
    test_url = "https://de.aliexpress.com/item/1005008204179129.html"
    
    def test_logger(msg):
        print(f"[TEST] {msg}")
    
    print("Testing improved variant detection...")
    variants = scrape_variants_with_detailed_logging(test_url, test_logger)
    print(f"Result: {len(variants)} variants found")