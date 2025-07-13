#!/usr/bin/env python3
"""
Test variant grouping functionality
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import Product, db

with app.app_context():
    # Test with product 182
    product = Product.query.get(182)
    if product:
        print(f"Testing variant grouping for product {product.id}:")
        print(f"Title: {product.title}")
        print(f"Variant: {product.variant_title}")
        print(f"Current SPU: {product.spu_id}")
        print()
        
        # Get all related products
        base_title = product.get_base_title()
        related_products = Product.query.filter(
            Product.title.contains(base_title.split()[0]),  # Same brand (e.g., JAYO)
            Product.is_active == True,
            Product.id != product.id  # Exclude self
        ).all()
        
        print(f"Found {len(related_products)} related products")
        
        # Filter to find products that are likely variants
        potential_variants = []
        
        for related in related_products:
            # Check if it's from same product line
            product_words = set(base_title.lower().split())
            related_words = set(related.get_base_title().lower().split())
            
            # Must have significant overlap in title words
            common_words = product_words & related_words
            if len(common_words) >= 3:  # At least 3 words in common
                # Check if they have different variants
                if related.variant_title and related.variant_title != product.variant_title:
                    potential_variants.append(related)
        
        print(f"Found {len(potential_variants)} potential variants:")
        
        for i, variant in enumerate(potential_variants[:10], 1):  # Show first 10
            print(f"{i}. ID: {variant.id}")
            print(f"   Title: {variant.title[:60]}...")
            print(f"   Variant: {variant.variant_title}")
            print(f"   SPU: {variant.spu_id}")
            print()
            
        if len(potential_variants) > 10:
            print(f"... and {len(potential_variants) - 10} more")
            
    else:
        print("Product 182 not found")