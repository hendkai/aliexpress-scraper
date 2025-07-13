#!/usr/bin/env python3
"""
Debug variant scraping
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import Product
from scraper import scrape_product_variants

def debug_logger(message):
    print(f"[DEBUG] {message}")

with app.app_context():
    # Test with product 182
    product = Product.query.get(182)
    if product:
        print(f"Testing variant scraping for product {product.id}:")
        print(f"Title: {product.title}")
        print(f"URL: {product.product_url}")
        print()
        
        try:
            print("Starting variant scraping...")
            variants = scrape_product_variants(product.product_url, debug_logger)
            
            print(f"\nResults:")
            print(f"Found {len(variants)} variants")
            
            for i, variant in enumerate(variants, 1):
                print(f"{i}. Variant: {variant.get('variant_title', 'Unknown')}")
                print(f"   Alt: {variant.get('sku_alt', 'No alt')}")
                print(f"   Image: {variant.get('image_url', 'No image')[:60]}...")
                print()
                
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("Product 182 not found")