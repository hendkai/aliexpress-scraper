#!/usr/bin/env python3
"""
Test variant detection functionality
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scraper import extract_variant_from_title

# Test cases
test_titles = [
    # Hardware variants
    "NAS Alder Lake N100 / Twin Lake N150 Motherboard DDR5 SODIMM 4800 MHz",
    "Intel N100 Mini PC 16GB DDR5 RAM 512GB SSD",
    "AMD Ryzen 5 5600G Desktop Computer",
    
    # 3D Printer filament variants  
    "PLA 3D Printer Filament 1.75mm 1kg Black High Quality",
    "ABS 3D Printing Filament 1.75mm 1kg White Premium Grade",
    "PETG Filament 1.75mm 1kg Transparent Clear 3D Printer",
    "TPU Flexible Filament 1.75mm 0.5kg Red Soft Material",
    "PLA+ Enhanced Filament 1.75mm 1kg Blue Stronger Formula",
    "Wood PLA Filament 1.75mm 1kg Natural Brown 3D Printing",
    "Silk PLA Filament 1.75mm 1kg Gold Shiny Finish",
    
    # Color variants
    "Smartphone Case Clear Transparent TPU Cover",
    "LED Strip Light 5M White 12V Waterproof",
    "Bluetooth Speaker Portable Black Wireless",
    
    # Size variants
    "T-Shirt Cotton Men's XL Size Blue Color",
    "Drill Bit Set 10mm 15mm 20mm Professional",
    "Power Bank 10000mAh Portable Charger",
    
    # Multiple variants (should pick the highest priority)
    "PLA+ Filament 1.75mm 1kg Red Color Enhanced Formula",
    "N100 Mini PC 16GB RAM Black Case WiFi6",
]

print("Testing variant detection:")
print("=" * 60)

for title in test_titles:
    variant = extract_variant_from_title(title)
    print(f"Title: {title[:50]}...")
    print(f"Variant: {variant}")
    print("-" * 60)

print("\nTesting specific 3D printer filament examples:")
filament_titles = [
    "PLA+ 3D Printer Filament 1.75mm 1kg Spool Multiple Colors Available",
    "25M PLA 3D Printer Filament High Quality",
    "96M PLA Filament 1.75mm Premium Grade",
    "150M PLA 3D Printing Material Strong",
    "200M PLA Filament Professional Quality",
    "100M PLA 3D Printer Wire Premium",
    "50M PLA Filament 1.75mm Standard",
    "36M PLA 3D Printing Material Basic",
    "30M PLA Filament Entry Level",
    "10kg PLA Filament Bulk Pack",
    "5kg PETG Filament Industrial Grade",
    "1kg ABS Filament Professional",
    "500g TPU Flexible Filament",
    "250g Wood PLA Natural Brown",
]

for title in filament_titles:
    variant = extract_variant_from_title(title)
    print(f"Title: {title}")
    print(f"Detected variant: {variant}")
    print("-" * 40)