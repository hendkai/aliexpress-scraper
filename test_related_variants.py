#!/usr/bin/env python3
"""
Test the related variants functionality
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import Product, db

with app.app_context():
    # Test product 331
    product = Product.query.get(331)
    if product:
        print(f"Testing product 331:")
        print(f"Title: {product.title}")
        print(f"Variant: {product.variant_title}")
        print()
        
        related_variants = product.get_related_variants()
        print(f"Found {len(related_variants)} related variants:")
        
        for i, variant in enumerate(related_variants, 1):
            print(f"{i}. ID: {variant.id}")
            print(f"   Title: {variant.title[:60]}...")
            print(f"   Variant: {variant.variant_title}")
            print(f"   Image: {variant.image_url[:50]}..." if variant.image_url else "   Image: None")
            print(f"   Tracked: {variant.is_tracked}")
            print()
    else:
        print("Product 331 not found")