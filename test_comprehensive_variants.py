#!/usr/bin/env python3
"""
Comprehensive test for variant detection across different product types
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scraper import extract_variant_from_title

# Test different product categories
test_cases = {
    "Processors/Hardware": [
        "Mini PC Intel N100 16GB DDR5 RAM 512GB SSD",
        "AMD Ryzen 5 5600G Desktop Computer",
        "Intel Core i7-12700K Processor",
        "NAS Alder Lake N100 / Twin Lake N150 Motherboard",
        "Celeron N4000 Mini Computer",
        "Ryzen 9 7950X Gaming PC",
    ],
    
    "3D Printer Filament": [
        "25M PLA 3D Printer Filament High Quality",
        "96M PLA Filament 1.75mm Premium Grade",
        "150M PLA 3D Printing Material Strong",
        "1kg PETG Filament Professional Quality",
        "500g TPU Flexible Filament Red",
        "250g Wood PLA Natural Brown",
        "2kg ABS Filament Black Industrial Grade",
        "10kg PLA Filament Bulk Pack White",
    ],
    
    "Colors/Clothing": [
        "T-Shirt Cotton Men's XL Size Blue Color",
        "Smartphone Case Clear Transparent TPU Cover",
        "LED Strip Light 5M White 12V Waterproof",
        "Bluetooth Speaker Portable Black Wireless",
        "Gaming Mouse Red RGB Backlight",
        "Laptop Bag Navy Blue Professional",
        "Phone Case Pink Glitter Sparkle",
        "Headphones Silver Metallic Finish",
    ],
    
    "Electronics/Power": [
        "Power Bank 10000mAh Portable Charger",
        "USB Cable 60W Fast Charging",
        "Battery 18650 3000mAh Li-ion",
        "Charger 65W USB-C Power Adapter",
        "Solar Panel 100W Monocrystalline",
        "Inverter 12V to 220V 500W",
        "LED Bulb 15W E27 Warm White",
    ],
    
    "Measurements/Sizes": [
        "Drill Bit Set 10mm 15mm 20mm Professional",
        "Screwdriver Set 2.5mm 3.0mm 4.0mm",
        "Cable 2m USB-C to Lightning",
        "Antenna 433MHz 5dBi SMA Male",
        "Pipe Fitting 1/2 inch NPT Thread",
        "Wire 18AWG 100ft Electrical Cable",
        "Tubing 8mm OD 6mm ID Silicone",
    ],
    
    "Mixed Variants": [
        "PLA+ Filament 1.75mm 1kg Red Color Enhanced Formula",
        "N100 Mini PC 16GB RAM Black Case WiFi6",
        "Ryzen 7 Gaming PC 32GB DDR5 RGB White",
        "PETG Filament 2kg Transparent Clear 1.75mm",
        "Power Bank 20000mAh Black USB-C PD 100W",
        "LED Strip 5M RGB 12V Waterproof Remote Control",
    ]
}

print("Comprehensive Variant Detection Test")
print("=" * 80)

for category, titles in test_cases.items():
    print(f"\n{category.upper()}:")
    print("-" * 60)
    
    for title in titles:
        variant = extract_variant_from_title(title)
        print(f"Title: {title}")
        print(f"Variant: {variant}")
        print()

# Test some edge cases
print("\nEDGE CASES:")
print("-" * 60)

edge_cases = [
    "Generic Product No Variants",
    "Multiple Colors Red Blue Green Available",
    "Size M L XL Choose Your Size",
    "1.75mm 3.0mm Diameter Options",
    "PLA ABS PETG Material Choice",
    "N100 N150 N200 Processor Selection",
]

for title in edge_cases:
    variant = extract_variant_from_title(title)
    print(f"Title: {title}")
    print(f"Variant: {variant}")
    print()

print("Test completed!")