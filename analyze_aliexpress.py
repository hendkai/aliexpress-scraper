#!/usr/bin/env python3
"""
Live AliExpress Structure Analysis Tool
Analyzes the current state of AliExpress pages to improve scraping
"""

import json
import re
from DrissionPage import WebPage, ChromiumOptions
from urllib.parse import quote_plus
import time

def analyze_search_page(keyword="3d printer filament", headless=False):
    """
    Analyze AliExpress search page structure
    """
    print(f"\n{'='*80}")
    print(f"ANALYZING ALIEXPRESS SEARCH PAGE FOR: {keyword}")
    print(f"{'='*80}\n")

    # Set up browser
    co = ChromiumOptions()
    if headless:
        co.headless()
    co.set_user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36")
    co.set_argument('--disable-blink-features=AutomationControlled')

    browser = WebPage(chromium_options=co)
    browser.set.load_mode.eager()

    try:
        # Visit search page
        search_url = f'https://www.aliexpress.com/w/wholesale-{quote_plus(keyword)}.html'
        print(f"Visiting: {search_url}\n")
        browser.get(search_url, timeout=30)

        # Wait for dynamic content
        print("Waiting for page to load...")
        time.sleep(5)

        # Analysis 1: Check for product containers
        print("\n" + "="*80)
        print("ANALYSIS 1: Product Container Structure")
        print("="*80)

        # Try various product container selectors
        selectors_to_try = [
            '[class*="product"]',
            '[class*="item"]',
            '[data-product-id]',
            '[class*="card"]',
            'a[href*="/item/"]',
        ]

        for selector in selectors_to_try:
            elements = browser.eles(selector, timeout=2)
            print(f"\nSelector: {selector}")
            print(f"  Found: {len(elements)} elements")

            if elements and len(elements) > 0:
                # Analyze first element
                first_elem = elements[0]
                print(f"  First element tag: {first_elem.tag}")
                print(f"  First element classes: {first_elem.attr('class')}")

                # Look for data attributes
                attrs = first_elem.attrs
                data_attrs = {k: v for k, v in attrs.items() if k.startswith('data-')}
                if data_attrs:
                    print(f"  Data attributes found: {list(data_attrs.keys())[:5]}")

        # Analysis 2: Check for JSON data in page
        print("\n" + "="*80)
        print("ANALYSIS 2: JavaScript Data Structures")
        print("="*80)

        html = browser.html

        # Look for window.__INITIAL_STATE__
        initial_state_matches = re.findall(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', html, re.DOTALL)
        if initial_state_matches:
            print(f"\n✓ Found window.__INITIAL_STATE__ ({len(initial_state_matches)} matches)")
            try:
                state_data = json.loads(initial_state_matches[0])
                print(f"  Keys: {list(state_data.keys())[:10]}")

                # Deep dive into structure
                if 'data' in state_data:
                    print(f"  data keys: {list(state_data['data'].keys())[:10]}")
                if 'pageModule' in state_data:
                    print(f"  pageModule keys: {list(state_data['pageModule'].keys())[:10]}")
            except:
                print("  (Could not parse JSON)")
        else:
            print("\n✗ No window.__INITIAL_STATE__ found")

        # Look for runParams
        runparams_matches = re.findall(r'window\.runParams\s*=\s*({.*?});', html, re.DOTALL)
        if runparams_matches:
            print(f"\n✓ Found window.runParams ({len(runparams_matches)} matches)")
            try:
                params = json.loads(runparams_matches[0])
                print(f"  Keys: {list(params.keys())[:10]}")
            except:
                print("  (Could not parse JSON)")
        else:
            print("\n✗ No window.runParams found")

        # Analysis 3: Network requests analysis
        print("\n" + "="*80)
        print("ANALYSIS 3: Network Requests and API Calls")
        print("="*80)

        # Look for API endpoints in HTML
        api_patterns = [
            r'https://[^"\']*aliexpress[^"\']*\.json',
            r'https://[^"\']*api[^"\']*aliexpress',
            r'/api/[^"\']*',
        ]

        for pattern in api_patterns:
            matches = re.findall(pattern, html)
            unique_matches = list(set(matches))[:5]
            if unique_matches:
                print(f"\nPattern: {pattern}")
                for match in unique_matches:
                    print(f"  - {match}")

        # Analysis 4: Product data attributes
        print("\n" + "="*80)
        print("ANALYSIS 4: Product-Specific Data Attributes")
        print("="*80)

        # Find all elements with product-related data attributes
        product_data_patterns = [
            r'data-product-id="([^"]+)"',
            r'data-sku-id="([^"]+)"',
            r'data-spu-id="([^"]+)"',
            r'data-item-id="([^"]+)"',
        ]

        for pattern in product_data_patterns:
            matches = re.findall(pattern, html)
            unique = list(set(matches))[:5]
            if unique:
                print(f"\nPattern: {pattern}")
                print(f"  Found {len(matches)} total, {len(set(matches))} unique")
                print(f"  Examples: {unique}")

        # Analysis 5: Current API endpoint usage
        print("\n" + "="*80)
        print("ANALYSIS 5: Hardcoded API Endpoint Analysis")
        print("="*80)
        print("\nCurrent endpoint: https://www.aliexpress.com/fn/search-pc/index")
        print("Testing if this endpoint is still valid...")

        # Try to find references to this endpoint in the page
        if 'fn/search-pc/index' in html:
            print("✓ Endpoint reference found in page HTML")
        else:
            print("✗ Endpoint reference NOT found in page HTML (may be outdated)")

        # Look for alternative search endpoints
        search_endpoint_patterns = [
            r'https://[^"\']*search[^"\']*',
            r'/fn/[^"\']*',
        ]

        print("\nAlternative endpoints found:")
        for pattern in search_endpoint_patterns:
            matches = re.findall(pattern, html)
            unique = list(set(matches))[:5]
            for match in unique:
                if 'search' in match.lower():
                    print(f"  - {match}")

        # Save HTML for manual inspection
        debug_file = f"/home/hendrik/aliexpress-scraper/debug_search_page.html"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"\n✓ Full HTML saved to: {debug_file}")

        print("\n" + "="*80)
        print("SEARCH PAGE ANALYSIS COMPLETE")
        print("="*80)

    finally:
        browser.quit()

def analyze_product_page(product_id="1005008204179129", headless=False):
    """
    Analyze AliExpress product page structure for variant detection
    """
    print(f"\n{'='*80}")
    print(f"ANALYZING ALIEXPRESS PRODUCT PAGE: {product_id}")
    print(f"{'='*80}\n")

    co = ChromiumOptions()
    if headless:
        co.headless()
    co.set_user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36")
    co.set_argument('--disable-blink-features=AutomationControlled')

    browser = WebPage(chromium_options=co)
    browser.set.load_mode.eager()

    try:
        product_url = f"https://www.aliexpress.com/item/{product_id}.html"
        print(f"Visiting: {product_url}\n")
        browser.get(product_url, timeout=30)

        print("Waiting for dynamic content...")
        time.sleep(8)

        html = browser.html

        # Analysis 1: Variant selectors
        print("\n" + "="*80)
        print("ANALYSIS 1: Variant Selector Structure")
        print("="*80)

        variant_patterns = [
            (r'data-sku-col="([^"]+)"', 'data-sku-col'),
            (r'class="[^"]*sku-item[^"]*"', 'sku-item classes'),
            (r'class="[^"]*sku-property[^"]*"', 'sku-property classes'),
            (r'<div[^>]*class="[^"]*sku[^"]*"', 'SKU div elements'),
        ]

        for pattern, name in variant_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            print(f"\n{name}:")
            print(f"  Found: {len(matches)} matches")
            if matches:
                unique = list(set(matches))[:5]
                print(f"  Unique: {len(set(matches))}")
                print(f"  Examples: {unique}")

        # Analysis 2: Price selectors
        print("\n" + "="*80)
        print("ANALYSIS 2: Price Element Structure")
        print("="*80)

        price_patterns = [
            (r'class="[^"]*price[^"]*current[^"]*"', 'Current price classes'),
            (r'class="[^"]*price[^"]*original[^"]*"', 'Original price classes'),
            (r'class="[^"]*discount[^"]*"', 'Discount classes'),
        ]

        for pattern, name in price_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            print(f"\n{name}:")
            print(f"  Found: {len(matches)} matches")
            if matches:
                unique = list(set(matches))[:3]
                for cls in unique:
                    print(f"  - {cls}")

        # Analysis 3: JSON data in page
        print("\n" + "="*80)
        print("ANALYSIS 3: Product JSON Data")
        print("="*80)

        # Look for SKU component
        sku_component_pattern = r'skuComponent["\']?\s*:\s*({.*?})\s*[,}]'
        sku_matches = re.findall(sku_component_pattern, html, re.DOTALL)

        if sku_matches:
            print(f"\n✓ Found skuComponent data ({len(sku_matches)} matches)")
            try:
                sku_data = json.loads(sku_matches[0])
                print(f"  Keys: {list(sku_data.keys())}")

                if 'skuPriceList' in sku_data:
                    print(f"  skuPriceList: {len(sku_data['skuPriceList'])} variants")
                if 'productSKUPropertyList' in sku_data:
                    print(f"  productSKUPropertyList: {len(sku_data['productSKUPropertyList'])} properties")
            except:
                print("  (Could not parse SKU component JSON)")
        else:
            print("\n✗ No skuComponent found")

        # Look for product data
        product_data_patterns = [
            r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
            r'window\.runParams\s*=\s*({.*?});',
            r'data\.skuModule\s*=\s*({.*?});',
        ]

        for pattern in product_data_patterns:
            matches = re.findall(pattern, html, re.DOTALL)
            if matches:
                print(f"\n✓ Found pattern: {pattern[:50]}...")
                print(f"  Matches: {len(matches)}")

        # Save HTML for inspection
        debug_file = f"/home/hendrik/aliexpress-scraper/debug_product_{product_id}.html"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"\n✓ Full HTML saved to: {debug_file}")

        print("\n" + "="*80)
        print("PRODUCT PAGE ANALYSIS COMPLETE")
        print("="*80)

    finally:
        browser.quit()

def main():
    """Run all analyses"""
    print("\n" + "="*80)
    print("ALIEXPRESS SCRAPER IMPROVEMENT ANALYSIS")
    print("="*80)

    # Analyze search page
    analyze_search_page(keyword="3d printer filament", headless=True)

    # Wait between analyses
    time.sleep(3)

    # Analyze product page
    analyze_product_page(product_id="1005008204179129", headless=True)

    print("\n" + "="*80)
    print("ALL ANALYSES COMPLETE")
    print("="*80)
    print("\nReview the debug HTML files for detailed inspection:")
    print("  - debug_search_page.html")
    print("  - debug_product_*.html")
    print("\n")

if __name__ == "__main__":
    main()
