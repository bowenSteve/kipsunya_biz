import pandas as pd
import os
import random
from decimal import Decimal, InvalidOperation
from django.utils.text import slugify

from products.models import Category, Product
from authentication.models import UserProfile
from django.contrib.auth.models import User
from django.conf import settings

# --- SCRIPT INPUTS ---
# The path to your CSV file, relative to the Django project's BASE_DIR
# Make sure this filename is correct!
CSV_FILE_PATH = os.path.join(settings.BASE_DIR, 'csv/jumia_home-office-appliances_with_details.csv')

def clean_price_to_decimal(price_str):
    """
    Cleans a price string like 'KSh 8,180' and converts it to a Decimal.
    Returns None if the string is invalid.
    """
    if not isinstance(price_str, str) or price_str == 'N/A':
        return None
    try:
        cleaned_str = price_str.replace('KSh', '').replace(',', '').strip()
        return Decimal(cleaned_str)
    except (InvalidOperation, ValueError):
        return None

def run():
    """
    Main function to run the seeding process.
    This will be executed by `python manage.py runscript seed2`.
    """
    print('--- Starting Seeding Process ---')

    # 1. CREATE VENDORS
    # ==============================================================
    print('\nStep 1: Setting up Vendors...')
    vendors_data = [
        {'username': 'vendor_electronics', 'email': 'electronics@kipsunya.com', 'first_name': 'John', 'last_name': 'Mwangi', 'profile': {'role': 'vendor', 'phone': '+254712345678', 'business_name': 'Mwangi Electronics Store', 'business_type': 'Electronics & Gadgets', 'business_verified': True}},
        {'username': 'vendor_drinks', 'email': 'drinks@kipsunya.com', 'first_name': 'Sarah', 'last_name': 'Wanjiku', 'profile': {'role': 'vendor', 'phone': '+254723456789', 'business_name': 'Wanjiku Premium Beverages', 'business_type': 'Alcoholic Beverages', 'business_verified': True}},
        {'username': 'vendor_kitchen', 'email': 'kitchen@kipsunya.com', 'first_name': 'Peter', 'last_name': 'Kiprotich', 'profile': {'role': 'vendor', 'phone': '+254734567890', 'business_name': 'Kiprotich Kitchen Supplies', 'business_type': 'Kitchen & Home Appliances', 'business_verified': True}}
    ]
    vendors = {}
    for data in vendors_data:
        profile_data = data.pop('profile')
        user, _ = User.objects.get_or_create(username=data['username'], defaults=data)
        UserProfile.objects.get_or_create(user=user, defaults=profile_data)
        vendors[data['username']] = user
    print(f'✓ {len(vendors)} vendors are set up.')

    # 2. CREATE CATEGORIES
    # ==============================================================
    print('\nStep 2: Setting up Categories...')
    categories_data = [
        {'name': 'Smartphones', 'slug': 'smartphones', 'description': 'Latest smartphones and mobile devices'},
        {'name': 'Electronics', 'slug': 'electronics', 'description': 'Soundbars, TVs, and other electronics'}, # <-- ADDED ELECTRONICS
        {'name': 'Drinks', 'slug': 'drinks', 'description': 'Premium alcoholic beverages'},
        {'name': 'Kitchen Ware', 'slug': 'kitchen-ware', 'description': 'Essential kitchen utensils and appliances'}
    ]
    categories = {}
    for data in categories_data:
        category, _ = Category.objects.get_or_create(name=data['name'], defaults={'slug': data['slug'], 'description': data['description']})
        categories[data['name']] = category
    print(f'✓ {len(categories)} categories are set up.')

    # 3. SEED PRODUCTS FROM CSV FILE
    # ==============================================================
    print(f'\nStep 3: Seeding Products from CSV file: {CSV_FILE_PATH}')
    
    try:
        df = pd.read_csv(CSV_FILE_PATH).fillna('') # Use fillna to avoid errors on missing data
    except FileNotFoundError:
        print(f"❌ ERROR: The file '{CSV_FILE_PATH}' was not found.")
        print("Please make sure the CSV file is in the root directory of your project.")
        return

    # *** NEW: Create a mapping from CSV category to DB category and vendor ***
    category_mapping = {
        'Home & Office': {
            'category': categories['Kitchen Ware'],
            'vendor': vendors['vendor_kitchen']
        },
        'Electronics': {
            'category': categories['Electronics'],
            'vendor': vendors['vendor_electronics']
        },
        # You can add more mappings here for other CSV files
        # 'Phones & Tablets': {
        #     'category': categories['Smartphones'],
        #     'vendor': vendors['vendor_electronics']
        # }
    }

    # Initialize counters for the final summary
    total_created = 0
    total_updated = 0
    total_skipped = 0

    # Loop through our mapping to process each category group
    for csv_category_name, mapping_info in category_mapping.items():
        print(f"\n-- Processing category: '{csv_category_name}' --")
        
        # Filter the DataFrame for the current category
        category_df = df[df['Category'] == csv_category_name]
        
        if category_df.empty:
            print("  No products found for this category in the CSV. Skipping.")
            continue
            
        db_category = mapping_info['category']
        db_vendor = mapping_info['vendor']
        
        created_count = 0
        updated_count = 0
        skipped_count = 0

        for index, row in category_df.iterrows():
            price = clean_price_to_decimal(row['Price'])
            if price is None or price <= 0:
                skipped_count += 1
                continue

            description = f"{row.get('Product Details', '')}\n\n--- SPECIFICATIONS ---\n\n{row.get('Specifications', '')}"
            unique_slug = slugify(row['Name'])

            product_data = {
                'name': row['Name'],
                'description': description.strip(),
                'category': db_category,
                'vendor': db_vendor,
                'price': price,
                'stock_quantity': random.randint(5, 50),
                'in_stock': True,
                'image_url': row.get('Image URL', ''),
                'featured': random.choice([True, False]),
                'is_active': True,
            }

            product, created = Product.objects.update_or_create(
                slug=unique_slug,
                defaults=product_data
            )

            if created:
                created_count += 1
            else:
                updated_count += 1
        
        print(f"  ✓ Finished. Created: {created_count}, Updated: {updated_count}, Skipped: {skipped_count}")
        total_created += created_count
        total_updated += updated_count
        total_skipped += skipped_count

    # 4. FINAL SUMMARY
    # ==============================================================
    print('\n' + '='*60)
    print('--- Seeding Process Completed ---')
    print(f'Products from CSV processed: {total_created + total_updated + total_skipped}')
    print(f'  - Total Created: {total_created}')
    print(f'  - Total Updated: {total_updated}')
    print(f'  - Total Skipped (invalid data): {total_skipped}')
    print('')
    print(f'Total Products in DB: {Product.objects.count()}')
    print(f'Total Categories in DB: {Category.objects.count()}')
    print('='*60)