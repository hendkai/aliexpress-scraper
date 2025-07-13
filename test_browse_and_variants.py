#!/usr/bin/env python3
"""
Test script for browse functionality and variant price extraction
"""

import sys
sys.path.append('.')

from scraper import parse_sku_attributes, extract_product_details
from models import db, Product, PriceHistory
from app import app

def test_price_parsing():
    """Test price extraction from different formats"""
    print("🧪 Testing Price Parsing")
    print("=" * 30)
    
    # Mock product data with various price formats
    test_products = [
        {
            'productId': '123',
            'prices': {
                'skuId': 'sku123',
                'salePrice': {'formattedPrice': '$19.99', 'currencyCode': 'USD'},
                'originalPrice': {'formattedPrice': '$29.99', 'currencyCode': 'USD'},
                'skuAttr': '14:173#Black;5:100014064#1kg'
            },
            'title': {'displayTitle': 'Test Product Black 1kg'},
            'image': {'imgUrl': '//example.com/image.jpg'},
            'store': {'storeName': 'Test Store', 'storeId': '456'},
            'trade': {'realTradeCount': 100},
            'evaluation': {'starRating': 4.5}
        },
        {
            'productId': '124',
            'prices': {
                'skuId': 'sku124',
                'salePrice': {'formattedPrice': '€15,50', 'currencyCode': 'EUR'},
                'originalPrice': {'formattedPrice': '€18,00', 'currencyCode': 'EUR'},
                'skuAttr': '14:365#White;5:100014065#500g'
            },
            'title': {'displayTitle': 'Test Product White 500g'},
        }
    ]
    
    fields = ['Product ID', 'SKU ID', 'Title', 'Variant Title', 'Sale Price', 'Original Price', 'Currency']
    
    for i, product in enumerate(test_products, 1):
        print(f"\n{i}. Testing product {product['productId']}:")
        extracted = extract_product_details([product], fields)
        
        if extracted:
            item = extracted[0]
            print(f"   Title: {item.get('Title', 'N/A')}")
            print(f"   Variant: {item.get('Variant Title', 'N/A')}")
            print(f"   Sale Price: {item.get('Sale Price', 'N/A')}")
            print(f"   Original Price: {item.get('Original Price', 'N/A')}")
            print(f"   Currency: {item.get('Currency', 'N/A')}")
        else:
            print("   ❌ No data extracted")

def test_sku_attribute_parsing():
    """Test SKU attribute parsing for variants"""
    print("\n\n🧪 Testing SKU Attribute Parsing")
    print("=" * 35)
    
    test_cases = [
        {
            'sku_attr': '14:173#Black;5:100014064#1kg',
            'properties': [
                {'skuPropertyId': '14', 'skuPropertyName': 'Color'},
                {'skuPropertyId': '5', 'skuPropertyName': 'Weight'}
            ]
        },
        {
            'sku_attr': '200007763:201336100#PLA;14:193#Blue;5:100014064#1.75mm',
            'properties': [
                {'skuPropertyId': '200007763', 'skuPropertyName': 'Material'},
                {'skuPropertyId': '14', 'skuPropertyName': 'Color'},
                {'skuPropertyId': '5', 'skuPropertyName': 'Diameter'}
            ]
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n{i}. SKU: {case['sku_attr']}")
        result = parse_sku_attributes(case['sku_attr'], case['properties'])
        print(f"   Parsed: {result}")

def test_browse_route():
    """Test browse route functionality"""
    print("\n\n🧪 Testing Browse Route")
    print("=" * 25)
    
    with app.test_client() as client:
        # Test basic browse page
        response = client.get('/browse')
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Browse page loads successfully")
            
            # Test with filters
            response = client.get('/browse?tracked_only=true&sort=price&order=asc')
            print(f"Filtered request status: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ Browse filters work correctly")
            else:
                print("❌ Browse filters failed")
        else:
            print("❌ Browse page failed to load")

def test_database_statistics():
    """Test database statistics for browse"""
    print("\n\n🧪 Testing Database Statistics")
    print("=" * 32)
    
    with app.app_context():
        stats = {
            'total_products': Product.query.filter_by(is_active=True).count(),
            'tracked_products': Product.query.filter_by(is_tracked=True, is_active=True).count(),
            'price_records': PriceHistory.query.count(),
        }
        
        print(f"Total Products: {stats['total_products']}")
        print(f"Tracked Products: {stats['tracked_products']}")
        print(f"Price Records: {stats['price_records']}")
        
        if stats['total_products'] > 0:
            # Test a sample product
            sample = Product.query.filter_by(is_active=True).first()
            if sample:
                print(f"\\nSample Product:")
                print(f"  Title: {sample.title[:50]}...")
                print(f"  Has Price: {'Yes' if sample.get_current_price() else 'No'}")
                print(f"  Is Tracked: {'Yes' if sample.is_tracked else 'No'}")
                print(f"  Variant: {sample.variant_title or 'None'}")

if __name__ == "__main__":
    print("🚀 Testing Browse & Variant Systems")
    print("=" * 40)
    
    test_price_parsing()
    test_sku_attribute_parsing()
    test_browse_route()
    test_database_statistics()
    
    print("\n\n✅ All tests completed!")
    print("\nNext steps:")
    print("1. Visit http://127.0.0.1:5000/browse to see the new browse page")
    print("2. Scrape some products to test the variant price extraction")
    print("3. Use the 'Find Variants' button on a product detail page")
    print("4. Check that prices are correctly saved in the database")