#!/usr/bin/env python3
"""
Test script for the new variant detection system.
Tests the real variant scraping functionality against the old system.
"""

import sys
sys.path.append('.')

from scraper import scrape_real_product_variants, parse_sku_attributes
from models import db, Product
from app import app

def test_variant_scraping():
    """Test variant scraping with a known product that has variants"""
    
    # Example product IDs that likely have variants (3D printer filament)
    test_product_ids = [
        "1005006033165462",  # JAYO 3D Printer Filament (likely has color variants)
        "1005004464775872",  # Another filament product
        "1005003648446476",  # Mini PC (likely has different processor variants)
    ]
    
    print("🧪 Testing New Variant Detection System")
    print("=" * 50)
    
    for i, product_id in enumerate(test_product_ids, 1):
        print(f"\n{i}. Testing Product ID: {product_id}")
        print("-" * 30)
        
        try:
            # Test the new variant scraping function
            variants = scrape_real_product_variants(product_id)
            
            if variants:
                print(f"✅ Found {len(variants)} real variants:")
                
                for j, variant in enumerate(variants, 1):
                    print(f"   {j}. SKU: {variant['sku_id']}")
                    print(f"      Variant: {variant.get('variant_title', 'N/A')}")
                    print(f"      Price: {variant.get('sale_price', 'N/A')}")
                    print(f"      Attributes: {variant.get('variant_attributes', {})}")
                    if variant.get('image_url'):
                        print(f"      Image: {variant['image_url'][:50]}...")
                    print()
            else:
                print("❌ No variants found")
                
        except Exception as e:
            print(f"❌ Error testing product {product_id}: {e}")
    
    print("\n" + "=" * 50)
    print("Test complete!")

def test_sku_parsing():
    """Test SKU attribute parsing"""
    print("\n🧪 Testing SKU Attribute Parsing")
    print("=" * 30)
    
    # Example SKU attribute strings from AliExpress
    test_cases = [
        "14:173,5:100014064#Black;14:365,200000463:100007326#2 Wheels",
        "14:29,5:100014065#White;200000124:100014066#1.75mm",
        "200007763:201336100#PLA;14:193#Blue;5:100014064#1kg",
    ]
    
    # Mock property list for testing
    mock_property_list = [
        {"skuPropertyId": "14", "skuPropertyName": "Color"},
        {"skuPropertyId": "5", "skuPropertyName": "Weight"},
        {"skuPropertyId": "200000463", "skuPropertyName": "Type"},
        {"skuPropertyId": "200000124", "skuPropertyName": "Diameter"},
        {"skuPropertyId": "200007763", "skuPropertyName": "Material"},
    ]
    
    for i, sku_attr in enumerate(test_cases, 1):
        print(f"\n{i}. Testing SKU: {sku_attr}")
        result = parse_sku_attributes(sku_attr, mock_property_list)
        print(f"   Parsed: {result}")

def compare_with_database():
    """Compare existing products in database to see variant grouping"""
    print("\n🧪 Checking Existing Products for Variant Patterns")
    print("=" * 50)
    
    with app.app_context():
        # Find products that might be variants of each other
        products = Product.query.filter_by(is_active=True).limit(20).all()
        
        print(f"Analyzing {len(products)} products...")
        
        # Group by product_id to see if we have variants
        product_groups = {}
        for product in products:
            if product.product_id:
                if product.product_id not in product_groups:
                    product_groups[product.product_id] = []
                product_groups[product.product_id].append(product)
        
        # Show groups with multiple variants
        variant_groups = {k: v for k, v in product_groups.items() if len(v) > 1}
        
        if variant_groups:
            print(f"\n✅ Found {len(variant_groups)} products with multiple variants:")
            for product_id, variants in variant_groups.items():
                print(f"\nProduct ID: {product_id}")
                for variant in variants:
                    print(f"  - SKU: {variant.sku_id} | Variant: {variant.variant_title} | Title: {variant.title[:50]}...")
        else:
            print("\n❌ No existing variant groups found in database")
            print("This is expected if you haven't used the new variant system yet.")

if __name__ == "__main__":
    test_sku_parsing()
    compare_with_database()
    
    # Only test live scraping if user confirms
    import time
    print("\n" + "⚠️" * 20)
    print("WARNING: The next test will make live requests to AliExpress!")
    print("This may take some time and should be used sparingly.")
    print("⚠️" * 20)
    
    response = input("\nDo you want to test live variant scraping? (y/N): ").strip().lower()
    if response == 'y':
        test_variant_scraping()
    else:
        print("Skipping live scraping test.")
    
    print("\n🎉 All tests completed!")
    print("\nNext steps:")
    print("1. Go to a product detail page in the web interface")
    print("2. Click 'Find Variants' to test the new functionality")
    print("3. Check if real variants are found and saved correctly")