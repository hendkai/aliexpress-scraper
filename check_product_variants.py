#!/usr/bin/env python3
"""
Check specific product variants
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import Product, db

with app.app_context():
    # Check product 331
    product = Product.query.get(331)
    if product:
        print(f"Main Product (ID: {product.id}):")
        print(f"Title: {product.title}")
        print(f"Variant: {product.variant_title}")
        print(f"SPU ID: {product.spu_id}")
        print(f"SKU ID: {product.sku_id}")
        print(f"Image: {product.image_url}")
        print(f"Tracked: {product.is_tracked}")
        print()
        
        # Get all variants
        variants = product.get_all_variants_including_self()
        print(f"Total variants (including self): {len(variants)}")
        
        for i, variant in enumerate(variants, 1):
            print(f"{i}. Variant ID: {variant.id}")
            print(f"   Title: {variant.title}")
            print(f"   Variant: {variant.variant_title}")
            print(f"   SPU ID: {variant.spu_id}")
            print(f"   SKU ID: {variant.sku_id}")
            print(f"   Image: {variant.image_url}")
            print(f"   Tracked: {variant.is_tracked}")
            print()
    else:
        print("Product 331 not found")
        
    # Check if there are products with the same base title
    if product:
        base_title = product.get_base_title()
        print(f"Base title: {base_title}")
        
        # Search for products with similar titles
        similar_products = Product.query.filter(
            Product.title.contains(base_title.split()[0])
        ).all()
        
        print(f"Similar products found: {len(similar_products)}")
        for similar in similar_products:
            if similar.id != product.id:
                print(f"- ID: {similar.id}, Variant: {similar.variant_title}, Title: {similar.title[:60]}...")