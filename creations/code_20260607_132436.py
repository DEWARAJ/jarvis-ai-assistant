file_path = "budget_laptops_brief.txt"

content = """Title: Top 3 Budget Laptops - Brief Summary (2024)

1. Acer Aspire 3 (A315-58)
- Price: ~$299-$399
- Processor: Intel Core i3-1115G4 or AMD Ryzen 3 5300U
- RAM: 8GB DDR4
- Storage: 256GB SSD
- Display: 15.6-inch Full HD (1920x1080)
- Battery Life: Up to 8 hours
- OS: Windows 11 Home
- Key Features: Lightweight (1.9kg), good build quality, reliable performance for everyday tasks
- Best For: Students and home users on a tight budget

2. Lenovo IdeaPad 1 (15ALC7)
- Price: ~$329-$449
- Processor: AMD Ryzen 5 5500U
- RAM: 8GB DDR4
- Storage: 256GB SSD
- Display: 15.6-inch Full HD IPS
- Battery Life: Up to 9 hours
- OS: Windows 11 Home
- Key Features: Slim design, good keyboard, Dolby Audio, fast AMD processor
- Best For: Budget-conscious users needing solid multitasking performance

3. HP 15-ef2xxx (HP 15 Laptop)
- Price: ~$349-$499
- Processor: AMD Ryzen 5 5625U
- RAM: 8GB DDR4
- Storage: 256GB SSD
- Display: 15.6-inch Full HD IPS Anti-Glare
- Battery Life: Up to 8.5 hours
- OS: Windows 11 Home
- Key Features: HP Fast Charge (50% in 45 min), reliable HP build, integrated AMD Radeon graphics
- Best For: General productivity and light multimedia use

Note: Prices are approximate and may vary by retailer and region. All models support Wi-Fi 6 and USB-C connectivity. Specifications may vary by configuration.
"""

with open(file_path, "w", encoding="utf-8") as file:
    file.write(content)

print(f"File '{file_path}' has been created successfully.")

with open(file_path, "r", encoding="utf-8") as file:
    print("\n--- File Contents ---")
    print(file.read())