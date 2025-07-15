#!/usr/bin/env python3
"""
Debug script to examine HTML structure of AliExpress product pages
and find why variant detection is failing.
"""

from DrissionPage import ChromiumOptions, WebPage
import time
import re

def debug_product_html():
    """Debug the HTML structure of a specific product page"""
    
    # Product URL from the logs
    product_url = "https://www.aliexpress.com/item/1005008550127168.html"
    
    print(f"Debugging product: {product_url}")
    
    # Set up browser
    co = ChromiumOptions()
    co.headless()
    browser_page = WebPage(chromium_options=co)
    
    try:
        # Load the page
        print("Loading product page...")
        browser_page.get(product_url, timeout=30)
        
        # Wait for page to load
        print("Waiting for page content...")
        time.sleep(8)
        
        # Get HTML content
        page_html = browser_page.html
        print(f"HTML length: {len(page_html)}")
        
        # Search for data-sku-col elements
        print("\n=== SEARCHING FOR data-sku-col ===")
        
        # Pattern 1: Basic search
        sku_pattern = r'data-sku-col="([^"]*)"'
        sku_matches = re.findall(sku_pattern, page_html, re.IGNORECASE)
        print(f"Found {len(sku_matches)} data-sku-col attributes: {sku_matches}")
        
        # Pattern 2: More context
        context_pattern = r'<[^>]*data-sku-col="([^"]*)"[^>]*>[^<]*(?:<[^>]*>[^<]*)*<img[^>]*src="([^"]*)"[^>]*alt="([^"]*)"'
        context_matches = re.findall(context_pattern, page_html, re.IGNORECASE)
        print(f"Found {len(context_matches)} data-sku-col with images: {context_matches}")
        
        # Pattern 3: Find any div with sku-related classes
        div_pattern = r'<div[^>]*class="[^"]*sku[^"]*"[^>]*>(.*?)</div>'
        div_matches = re.findall(div_pattern, page_html, re.IGNORECASE | re.DOTALL)
        print(f"Found {len(div_matches)} divs with 'sku' in class")
        
        # Pattern 4: Look for specific classes we know exist
        known_class_pattern = r'<div[^>]*class="[^"]*sku-item--image--jMUnnGA[^"]*"[^>]*>(.*?)</div>'
        known_matches = re.findall(known_class_pattern, page_html, re.IGNORECASE | re.DOTALL)
        print(f"Found {len(known_matches)} divs with sku-item--image--jMUnnGA class")
        
        # Pattern 5: Just search for the user's exact example
        exact_pattern = r'<div[^>]*data-sku-col="[^"]*"[^>]*class="[^"]*sku-item--image--jMUnnGA[^"]*"[^>]*>(.*?)</div>'
        exact_matches = re.findall(exact_pattern, page_html, re.IGNORECASE | re.DOTALL)
        print(f"Found {len(exact_matches)} exact matches like user's example")
        
        # Save HTML to file for manual inspection
        with open('/tmp/debug_product.html', 'w', encoding='utf-8') as f:
            f.write(page_html)
        print("HTML saved to /tmp/debug_product.html")
        
        # Look for any images that might be variants
        print("\n=== SEARCHING FOR VARIANT IMAGES ===")
        img_pattern = r'<img[^>]*src="([^"]*)"[^>]*alt="([^"]*)"[^>]*>'
        img_matches = re.findall(img_pattern, page_html, re.IGNORECASE)
        
        variant_images = []
        for src, alt in img_matches:
            if any(keyword in alt.lower() for keyword in ['kg', 'color', 'pla', 'petg', 'tpu', 'black', 'white', 'red', 'blue', 'green']):
                variant_images.append((src, alt))
        
        print(f"Found {len(variant_images)} potential variant images:")
        for src, alt in variant_images[:10]:  # Show first 10
            print(f"  - {alt}: {src[:80]}...")
        
        # Try browser automation to find elements
        print("\n=== BROWSER AUTOMATION SEARCH ===")
        
        # Try different selectors
        selectors = [
            '[data-sku-col]',
            'div[data-sku-col]',
            '.sku-item--image--jMUnnGA',
            '[class*="sku-item"]',
            '[class*="sku"]'
        ]
        
        for selector in selectors:
            try:
                elements = browser_page.eles(selector, timeout=3)
                print(f"Selector '{selector}': Found {len(elements)} elements")
                
                for i, elem in enumerate(elements[:3]):  # Show first 3
                    try:
                        sku_col = elem.attr('data-sku-col')
                        class_name = elem.attr('class')
                        print(f"  Element {i+1}: data-sku-col='{sku_col}', class='{class_name}'")
                        
                        # Try to find image inside
                        img = elem.ele('img', timeout=1)
                        if img:
                            src = img.attr('src')
                            alt = img.attr('alt')
                            print(f"    Image: alt='{alt}', src='{src[:60]}...'")
                    except:
                        print(f"  Element {i+1}: Could not get attributes")
                        
            except Exception as e:
                print(f"Selector '{selector}': Error - {e}")
        
    except Exception as e:
        print(f"Error: {e}")
        
    finally:
        browser_page.quit()

if __name__ == "__main__":
    debug_product_html()