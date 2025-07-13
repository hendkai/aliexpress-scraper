#!/usr/bin/env python3
"""
Update existing products with variant information
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import Product, db
from scraper import extract_variant_from_title

def update_existing_products():
    """Update existing products with variant information"""
    with app.app_context():
        products = Product.query.all()
        updated_count = 0
        
        print(f"Updating {len(products)} products with variant information...")
        
        for product in products:
            # Extract variant from title
            variant_title = extract_variant_from_title(product.title)
            
            if variant_title and variant_title != product.variant_title:
                product.variant_title = variant_title
                updated_count += 1
                print(f"Updated: {product.title[:50]}... -> Variant: {variant_title}")
        
        # Commit changes
        db.session.commit()
        print(f"\nSuccessfully updated {updated_count} products with variant information")
        
        # Show some examples
        variant_products = Product.query.filter(Product.variant_title.isnot(None)).all()
        print(f"\nTotal products with variants: {len(variant_products)}")
        
        # Group by base title to find potential variant groups
        base_titles = {}
        for product in variant_products:
            base_title = product.get_base_title()
            if base_title not in base_titles:
                base_titles[base_title] = []
            base_titles[base_title].append(product)
        
        print(f"\nPotential variant groups:")
        for base_title, products in base_titles.items():
            if len(products) > 1:
                print(f"Base: {base_title[:50]}...")
                for product in products:
                    print(f"  - {product.variant_title}: {product.title[:40]}...")
                print()

if __name__ == "__main__":
    update_existing_products()