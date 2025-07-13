#!/usr/bin/env python3
"""
Check database for products and variants
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import Product, db

with app.app_context():
    # Check products in database
    products = Product.query.all()
    print(f"Total products in database: {len(products)}")
    
    # Check for variants
    variant_products = Product.query.filter(Product.variant_title.isnot(None)).all()
    print(f"Products with variants: {len(variant_products)}")
    
    # Check SPU groupings
    spu_products = Product.query.filter(Product.spu_id.isnot(None)).all()
    print(f"Products with SPU IDs: {len(spu_products)}")
    
    print("\nSample products:")
    for i, product in enumerate(products[:10]):
        print(f"{i+1}. {product.title[:60]}...")
        print(f"   Variant: {product.variant_title}")
        print(f"   SPU ID: {product.spu_id}")
        print(f"   SKU ID: {product.sku_id}")
        print(f"   Tracked: {product.is_tracked}")
        print("-" * 60)
    
    # Check for grouped variants
    if spu_products:
        print("\nChecking SPU groups:")
        spu_groups = {}
        for product in spu_products:
            if product.spu_id not in spu_groups:
                spu_groups[product.spu_id] = []
            spu_groups[product.spu_id].append(product)
        
        print(f"Number of SPU groups: {len(spu_groups)}")
        for spu_id, variants in spu_groups.items():
            if len(variants) > 1:
                print(f"SPU {spu_id}: {len(variants)} variants")
                for variant in variants:
                    print(f"  - {variant.variant_title or 'No variant'}: {variant.title[:40]}...")