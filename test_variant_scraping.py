#!/usr/bin/env python3
"""
Test variant scraping functionality
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scraper import scrape_product_variants, extract_variant_from_sku_alt

# Test the alt text extraction
test_alts = [
    "PETG 2RD2BLBK",
    "PLAp 2BK2WTGY", 
    "PLAp 5TPMIX",
    "PLAp 5BK",
    "HS PLAp 2.0 5MIX-4",
    "HS PLAp 2.0 5MIX-3",
    "SILK BKWTSVRCLG",
    "PLAp SOSBLYMGSP",
    "PLAp GYRDBLFSYL",
    "SILK 2LG2RCSV",
    "PLA 2BK2WTGY",
    "PLA 2BK3WT",
    "PLA BKWTGYRDBL",
    "HS Matte PLA 5MIX-6",
    "HS Matte PLA 5MIX-5",
    "PETG RD2BL2WT",
    "HS PETG 2BK2WTGY",
    "HS PETG PKSBGNORRD",
    "PETG 5BK"
]

print("Testing variant extraction from SKU alt text:")
print("=" * 60)

for alt in test_alts:
    variant = extract_variant_from_sku_alt(alt)
    print(f"Alt: {alt:25} -> Variant: {variant}")

print("\n" + "=" * 60)
print("Now test with a real product URL...")

# Test with product 182's URL if we can construct it
from app import app
from models import Product

with app.app_context():
    product = Product.query.get(182)
    if product and product.product_url:
        print(f"Testing with product: {product.title[:60]}...")
        print(f"URL: {product.product_url}")
        
        # Note: This would require a browser to run in the actual environment
        print("(This would scrape the real variants in a live test)")
    else:
        print("Product 182 not found or no URL available")