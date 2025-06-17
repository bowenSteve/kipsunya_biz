# server/seed_with_vendors.py
from products.models import Category, Product
from authentication.models import UserProfile
from django.contrib.auth.models import User
from decimal import Decimal

print('Starting to seed products with vendors...')

# Create vendor users
vendors_data = [
    {
        'username': 'vendor1',
        'email': 'vendor1@kipsunya.com',
        'first_name': 'John',
        'last_name': 'Mwangi',
        'profile': {
            'role': 'vendor',
            'phone': '+254712345678',
            'business_name': 'Mwangi Electronics',
            'business_type': 'Electronics & Gadgets',
            'business_verified': True
        }
    },
    {
        'username': 'vendor2', 
        'email': 'vendor2@kipsunya.com',
        'first_name': 'Sarah',
        'last_name': 'Wanjiku',
        'profile': {
            'role': 'vendor',
            'phone': '+254723456789',
            'business_name': 'Wanjiku Beverages',
            'business_type': 'Alcoholic Beverages',
            'business_verified': True
        }
    },
    {
        'username': 'vendor3',
        'email': 'vendor3@kipsunya.com', 
        'first_name': 'Peter',
        'last_name': 'Kiprotich',
        'profile': {
            'role': 'vendor',
            'phone': '+254734567890',
            'business_name': 'Kiprotich Kitchen Supplies',
            'business_type': 'Kitchen & Home',
            'business_verified': True
        }
    }
]

# Create vendors
vendors = {}
for vendor_data in vendors_data:
    profile_data = vendor_data.pop('profile')
    user, created = User.objects.get_or_create(
        username=vendor_data['username'],
        defaults=vendor_data
    )
    
    if created:
        user.set_password('vendorpass123')
        user.save()
        print(f'Created vendor user: {user.get_full_name()}')
    
    # Create or update profile
    profile, profile_created = UserProfile.objects.get_or_create(
        user=user,
        defaults=profile_data
    )
    
    if not profile_created:
        for key, value in profile_data.items():
            setattr(profile, key, value)
        profile.save()
    
    vendors[vendor_data['username']] = user

# Create or get categories
categories_data = [
    {
        'name': 'Smartphones',
        'slug': 'smartphones',
        'description': 'Latest smartphones and mobile devices'
    },
    {
        'name': 'Drinks',
        'slug': 'drinks',
        'description': 'Premium alcoholic beverages including whiskey, gin, wine and spirits'
    },
    {
        'name': 'Kitchen Ware',
        'slug': 'kitchen-ware',
        'description': 'Essential kitchen utensils, cookware and appliances for modern cooking'
    }
]

categories = {}
for cat_data in categories_data:
    category, created = Category.objects.get_or_create(
        name=cat_data['name'],
        defaults={
            'slug': cat_data['slug'],
            'description': cat_data['description']
        }
    )
    categories[cat_data['name']] = category
    
    if created:
        print(f'Created category: {category.name}')

# Products data with vendor assignments
products_data = [
    # SMARTPHONES - Vendor 1 (Electronics)
    {
        'name': 'Vivo Y400 Pro',
        'slug': 'vivo-y400-pro',
        'description': '''The Vivo Y400 Pro features a stunning 6.77" AMOLED display with 120Hz refresh rate and 1300 nits peak brightness. 
Powered by Android 15 with Funtouch 15, it offers 8GB RAM and 128GB/256GB storage options. 
The device boasts a 50MP main camera with f/1.8 aperture and a 2MP depth sensor. 
With a 5500mAh battery and 90W fast charging, this phone delivers exceptional performance and battery life.''',
        'category': categories['Smartphones'],
        'vendor': vendors['vendor1'],
        'price': Decimal('51999.00'),
        'stock_quantity': 15,
        'in_stock': True,
        'image_url': 'https://fdn2.gsmarena.com/vv/pics/vivo/vivo-y400-pro-1.jpg',
        'featured': True,
        'is_active': True,
    },
    {
        'name': 'Motorola Moto G86',
        'slug': 'motorola-moto-g86',
        'description': '''The Motorola Moto G86 comes with a 6.67" P-OLED display featuring 1B colors and 120Hz refresh rate.
Running Android 15 with a Mediatek Dimensity 7300 chipset, it offers 8GB/12GB RAM options and 256GB/512GB storage.
Photography enthusiasts will love the 50MP main camera with f/1.9 aperture, 25mm wide lens, dual pixel PDAF, and OIS.''',
        'category': categories['Smartphones'],
        'vendor': vendors['vendor1'],
        'price': Decimal('38870.00'),
        'stock_quantity': 8,
        'in_stock': True,
        'image_url': 'https://fdn2.gsmarena.com/vv/pics/motorola/motorola-moto-g86-1.jpg',
        'featured': False,
        'is_active': True,
    },
    
    # DRINKS - Vendor 2 (Beverages)
    {
        'name': 'Beefeater London Dry Gin - 750ml',
        'slug': 'beefeater-london-dry-gin-750ml',
        'description': '''Beefeater, the only international premium gin still produced in the heart of London.
To this day, Beefeater gin is produced to James Borrough's original 1863 recipe, including the unique process of steeping nine perfectly balanced botanicals for 24 hours.
Premium London Dry Gin with distinctive juniper flavor and smooth finish.''',
        'category': categories['Drinks'],
        'vendor': vendors['vendor2'],
        'price': Decimal('3200.00'),
        'stock_quantity': 20,
        'in_stock': True,
        'image_url': 'https://ke.jumia.is/unsafe/fit-in/500x500/filters:fill(white)/product/17/873585/1.jpg?8695',
        'featured': True,
        'is_active': True,
    },
    {
        'name': 'Jameson Irish Whiskey - 4.5 Litres',
        'slug': 'jameson-irish-whiskey-4-5-litres',
        'description': '''Jameson is the best-selling Irish whiskey in the world. Produced in our distillery in Midleton, County Cork.
Jameson's blended whiskeys are triple-distilled, resulting in exceptional smoothness.
This large 4.5-litre bottle is perfect for parties, events, or stocking up your home bar.''',
        'category': categories['Drinks'],
        'vendor': vendors['vendor2'],
        'price': Decimal('28000.00'),
        'stock_quantity': 6,
        'in_stock': True,
        'image_url': 'https://ke.jumia.is/unsafe/fit-in/500x500/filters:fill(white)/product/57/283585/1.jpg?4526',
        'featured': False,
        'is_active': True,
    },
    
    # KITCHEN WARE - Vendor 3 (Kitchen Supplies)
    {
        'name': '2Pcs Set Of Stainless Aluminum Sufuria No Lids + Free Gift',
        'slug': '2pcs-stainless-aluminum-sufuria-set',
        'description': '''This 2-Piece Cookware set is made of pure aluminum encapsulated in the base for fast and even heating.
Solid stainless steel riveted handles stay cool on the stove top, ensuring safe and comfortable cooking.
Ideal even for jiko or firewood cooking during outdoor cooking adventures and camping trips.''',
        'category': categories['Kitchen Ware'],
        'vendor': vendors['vendor3'],
        'price': Decimal('2500.00'),
        'stock_quantity': 30,
        'in_stock': True,
        'image_url': 'https://ke.jumia.is/unsafe/fit-in/500x500/filters:fill(white)/product/96/7343842/1.jpg?0140',
        'featured': True,
        'is_active': True,
    },
    {
        'name': 'Electric Meat Grinder - Cordless Home Cooking Machine',
        'slug': 'electric-meat-grinder-cordless',
        'description': '''Simple and convenient cordless food processor that's easy to use anywhere in your kitchen.
Press and hold the top button to start the motor, release to stop - you control the degree of food processing.
Can chop garlic, onions, meat, and other ingredients in just minutes with precision and consistency.''',
        'category': categories['Kitchen Ware'],
        'vendor': vendors['vendor3'],
        'price': Decimal('4200.00'),
        'stock_quantity': 12,
        'in_stock': True,
        'image_url': 'https://ke.jumia.is/unsafe/fit-in/500x500/filters:fill(white)/product/12/5588703/1.jpg?3118',
        'featured': True,
        'is_active': True,
    },
]

# Create products
created_count = 0
updated_count = 0

for product_data in products_data:
    product, created = Product.objects.get_or_create(
        slug=product_data['slug'],
        defaults=product_data
    )
    
    if created:
        created_count += 1
        vendor_name = product.vendor.get_full_name()
        print(f'✓ Created: {product.name} - KES {product.price} (Vendor: {vendor_name})')
    else:
        # Update existing product
        for key, value in product_data.items():
            if key != 'slug':
                setattr(product, key, value)
        product.save()
        updated_count += 1
        vendor_name = product.vendor.get_full_name()
        print(f'✓ Updated: {product.name} - KES {product.price} (Vendor: {vendor_name})')

print('='*60)
print('Seeding completed successfully!')
print(f'Vendors created: {len(vendors)}')
print(f'Products created: {created_count}')
print(f'Products updated: {updated_count}')
print(f'Total products: {Product.objects.count()}')
print('='*60)