#!/usr/bin/env python3
"""
Fix price data in database - correct the decimal separator issue
"""

import sys
sys.path.append('.')

from app import app
from models import db, Product, PriceHistory
from scraper import parse_price_string

def fix_price_data():
    """Fix all price data in the database"""
    
    with app.app_context():
        print('🔧 Korrigiere Preisdaten in der Datenbank')
        print('=' * 45)
        
        # Load original JSON data for reference
        import json
        try:
            with open('/home/hendrik-kaiser/aliexpress-scraper/results/aliexpress_filament_extracted.json', 'r') as f:
                original_data = json.load(f)
            
            # Create mapping from product_id to original prices
            price_mapping = {}
            for item in original_data:
                product_id = item.get('Product ID')
                if product_id:
                    price_mapping[str(product_id)] = {
                        'sale_price': item.get('Sale Price'),
                        'original_price': item.get('Original Price')
                    }
            
            print(f'📊 Gefunden: {len(price_mapping)} Produkte mit ursprünglichen Preisdaten')
            
        except Exception as e:
            print(f'❌ Fehler beim Laden der JSON-Daten: {e}')
            return
        
        # Fix all price history entries
        fixed_count = 0
        price_histories = PriceHistory.query.all()
        
        print(f'🔍 Überprüfe {len(price_histories)} Preishistorie-Einträge...')
        
        for price_history in price_histories:
            product = price_history.product
            if not product or not product.product_id:
                continue
                
            # Get original price strings
            original_prices = price_mapping.get(product.product_id)
            if not original_prices:
                continue
            
            # Parse correct prices
            correct_sale_price = parse_price_string(original_prices['sale_price'])
            correct_original_price = parse_price_string(original_prices['original_price'])
            
            # Check if prices need fixing (current price is much higher than expected)
            needs_fixing = False
            if (correct_sale_price and price_history.sale_price and 
                abs(price_history.sale_price - correct_sale_price) > 100):
                needs_fixing = True
                print(f'📝 {product.title[:50]}...')
                print(f'   Falsch: {price_history.sale_price} EUR -> Korrekt: {correct_sale_price} EUR')
                
                price_history.sale_price = correct_sale_price
                if correct_original_price:
                    price_history.original_price = correct_original_price
                
                fixed_count += 1
        
        if fixed_count > 0:
            print(f'\\n💾 Speichere Korrekturen...')
            db.session.commit()
            print(f'✅ {fixed_count} Preise korrigiert!')
        else:
            print('ℹ️ Keine Korrekturen nötig.')
        
        # Show some examples of corrected prices
        print(f'\\n🔍 Beispiele korrigierter SUNLU-Preise:')
        sunlu_products = Product.query.filter(Product.title.ilike('%sunlu%')).limit(3).all()
        
        for product in sunlu_products:
            current_price = product.get_current_price()
            if current_price:
                print(f'   {product.title[:50]}...')
                print(f'   Preis: {current_price.sale_price} {product.currency}')

if __name__ == "__main__":
    fix_price_data()