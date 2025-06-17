# server/seed_with_vendors.py
from products.models import Category, Product
from authentication.models import UserProfile
from django.contrib.auth.models import User
from decimal import Decimal

print('Starting to seed products with vendors...')

# First, create vendor users
vendors_data = [
    {
        'username': 'vendor_electronics',
        'email': 'electronics@kipsunya.com',
        'first_name': 'John',
        'last_name': 'Mwangi',
        'profile': {
            'role': 'vendor',
            'phone': '+254712345678',
            'business_name': 'Mwangi Electronics Store',
            'business_type': 'Electronics & Gadgets',
            'business_verified': True
        }
    },
    {
        'username': 'vendor_drinks',
        'email': 'drinks@kipsunya.com',
        'first_name': 'Sarah',
        'last_name': 'Wanjiku',
        'profile': {
            'role': 'vendor',
            'phone': '+254723456789',
            'business_name': 'Wanjiku Premium Beverages',
            'business_type': 'Alcoholic Beverages',
            'business_verified': True
        }
    },
    {
        'username': 'vendor_kitchen',
        'email': 'kitchen@kipsunya.com',
        'first_name': 'Peter',
        'last_name': 'Kiprotich',
        'profile': {
            'role': 'vendor',
            'phone': '+254734567890',
            'business_name': 'Kiprotich Kitchen Supplies',
            'business_type': 'Kitchen & Home Appliances',
            'business_verified': True
        }
    }
]

# Create vendors
vendors = {}
for vendor_data in vendors_data:
    profile_data = vendor_data.pop('profile')
    
    # Create or get user
    user, created = User.objects.get_or_create(
        username=vendor_data['username'],
        defaults=vendor_data
    )
    
    if created:
        user.set_password('vendorpass123')
        user.save()
        print(f'✓ Created vendor: {user.get_full_name()}')
    else:
        print(f'✓ Using existing vendor: {user.get_full_name()}')
    
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

# Create categories
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
        print(f'✓ Created category: {category.name}')
    else:
        print(f'✓ Using existing category: {category.name}')

# All products data with vendor assignments
products_data = [
    # SMARTPHONES - Electronics Vendor
    {
        'name': 'Vivo Y400 Pro',
        'slug': 'vivo-y400-pro',
        'description': '''The Vivo Y400 Pro features a stunning 6.77" AMOLED display with 120Hz refresh rate and 1300 nits peak brightness. 
Powered by Android 15 with Funtouch 15, it offers 8GB RAM and 128GB/256GB storage options. 
The device boasts a 50MP main camera with f/1.8 aperture and a 2MP depth sensor. 
With a 5500mAh battery and 90W fast charging, this phone delivers exceptional performance and battery life.
Key specs: 162g weight, 7.5mm thickness, IP65 dust/water resistance, Nano-SIM support.''',
        'category': categories['Smartphones'],
        'vendor': vendors['vendor_electronics'],
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
        'description': '''The Motorola Moto G86 comes with a 6.67" P-OLED display featuring 1B colors and 120Hz refresh rate for smooth visuals.
Running Android 15 with a Mediatek Dimensity 7300 chipset, it offers 8GB/12GB RAM options and 256GB/512GB storage.
Photography enthusiasts will love the 50MP main camera with f/1.9 aperture, 25mm wide lens, dual pixel PDAF, and OIS.
The 5200mAh battery with 30W fast charging ensures all-day usage. Additional features include IP68/IP69 water resistance.
Expected release: July 2025. Dimensions: 161.2 x 74.7 x 7.8 mm, Weight: 185g.''',
        'category': categories['Smartphones'],
        'vendor': vendors['vendor_electronics'],
        'price': Decimal('38870.00'),
        'stock_quantity': 8,
        'in_stock': True,
        'image_url': 'https://fdn2.gsmarena.com/vv/pics/motorola/motorola-moto-g86-1.jpg',
        'featured': False,
        'is_active': True,
    },
    {
        'name': 'Motorola Edge 60',
        'slug': 'motorola-edge-60',
        'description': '''The Motorola Edge 60 features a premium 6.67" P-OLED display with 1B colors, 120Hz refresh rate, and HDR10+ support.
Released in April 2025, it runs Android 15 with up to 3 major Android upgrades guaranteed.
Powered by Mediatek Dimensity 7300/7400 chipset with options for 8GB/12GB RAM and 256GB/512GB storage.
Camera setup includes a 50MP main sensor with f/1.8, 24mm wide lens, multi-direction PDAF, and OIS.
The 5200mAh battery with 68W fast charging provides excellent battery life.
Build: Glass front (Gorilla Glass 7), plastic frame, plastic back. Weight: 179g.''',
        'category': categories['Smartphones'],
        'vendor': vendors['vendor_electronics'],
        'price': Decimal('53170.00'),
        'stock_quantity': 12,
        'in_stock': True,
        'image_url': 'https://fdn2.gsmarena.com/vv/pics/motorola/motorola-edge-60-1.jpg',
        'featured': True,
        'is_active': True,
    },
    {
        'name': 'Motorola Moto G45',
        'slug': 'motorola-moto-g45',
        'description': '''The Motorola Moto G45 offers excellent value with its 6.5" IPS LCD display and 120Hz refresh rate.
Released in August 2024, it features Android 14 and Qualcomm SM6375 Snapdragon 6s Gen 3 chipset.
Available in 4GB/8GB RAM variants with 128GB storage options and microSDXC expansion slot.
The camera system includes a 50MP main sensor with f/1.8 aperture and a 2MP macro lens.
Powered by a 5000mAh battery with 18W fast charging for reliable all-day performance.
Build: Glass front (Gorilla Glass 3), plastic frame, silicone polymer back. Weight: 183g.
Features water-repellent design and stereo speakers for enhanced multimedia experience.''',
        'category': categories['Smartphones'],
        'vendor': vendors['vendor_electronics'],
        'price': Decimal('25999.00'),
        'stock_quantity': 25,
        'in_stock': True,
        'image_url': 'https://fdn2.gsmarena.com/vv/pics/motorola/motorola-moto-g45-5g-1.jpg',
        'featured': False,
        'is_active': True,
    },
    
    # DRINKS - Drinks Vendor
    {
        'name': 'Beefeater London Dry Gin - 750ml',
        'slug': 'beefeater-london-dry-gin-750ml',
        'description': '''Beefeater, the only international premium gin still produced in the heart of London, and the world's most awarded gin, is the embodiment of The Spirit of London. 
To this day, Beefeater gin is produced to James Borrough's original 1863 recipe, including the unique process of steeping nine perfectly balanced botanicals for 24 hours. 
Part of the Pernod Ricard group since 2005, Beefeater is a modern, energetic and urban gin with 200 years of distilling heritage and a refreshingly modern take on today's tastes.
Premium London Dry Gin with distinctive juniper flavor and smooth finish. Perfect for cocktails or enjoying neat.''',
        'category': categories['Drinks'],
        'vendor': vendors['vendor_drinks'],
        'price': Decimal('3200.00'),
        'stock_quantity': 20,
        'in_stock': True,
        'image_url': 'https://ke.jumia.is/unsafe/fit-in/500x500/filters:fill(white)/product/17/873585/1.jpg?8695',
        'featured': True,
        'is_active': True,
    },
    {
        'name': 'The Glenlivet Founders Reserve 12 Years - 700ml',
        'slug': 'glenlivet-founders-reserve-12-years-700ml',
        'description': '''The Glenlivet Founders Reserve 12 Years is a premium single malt Scotch whisky that represents the perfect introduction to The Glenlivet range.
Aged for 12 years in traditional oak casks, this whisky offers a smooth and approachable flavor profile with notes of citrus, honey, and vanilla.
The Glenlivet distillery, founded in 1824, is renowned for producing exceptional single malt whiskies using traditional methods and the finest ingredients.
This expression showcases the classic Speyside character with its elegant balance and refined taste. Perfect for both whisky enthusiasts and newcomers alike.''',
        'category': categories['Drinks'],
        'vendor': vendors['vendor_drinks'],
        'price': Decimal('8500.00'),
        'stock_quantity': 12,
        'in_stock': True,
        'image_url': 'https://ke.jumia.is/unsafe/fit-in/500x500/filters:fill(white)/product/45/449969/1.jpg?2169',
        'featured': True,
        'is_active': True,
    },
    {
        'name': 'Jameson Irish Whiskey - 4.5 Litres',
        'slug': 'jameson-irish-whiskey-4-5-litres',
        'description': '''Jameson is the best-selling Irish whiskey in the world. Produced in our distillery in Midleton, County Cork, from malted and unmalted Irish barley.
Jameson's blended whiskeys are triple-distilled, resulting in exceptional smoothness that has made it a favorite worldwide.
The brand has been part of the Pernod Group since 1988 and continues to expand its acclaimed range to offer new taste experiences.
This large 4.5-litre bottle is perfect for parties, events, or stocking up your home bar. Features the signature smooth taste with hints of vanilla and honey.
Ideal for mixing cocktails or enjoying neat with friends and family.''',
        'category': categories['Drinks'],
        'vendor': vendors['vendor_drinks'],
        'price': Decimal('28000.00'),
        'stock_quantity': 6,
        'in_stock': True,
        'image_url': 'https://ke.jumia.is/unsafe/fit-in/500x500/filters:fill(white)/product/57/283585/1.jpg?4526',
        'featured': False,
        'is_active': True,
    },
    {
        'name': 'Seagrams Imperial Blue Whiskey - 750ml',
        'slug': 'seagrams-imperial-blue-whiskey-750ml',
        'description': '''Pernod Ricard has a unique portfolio of premium brands encompassing every major category of wine and spirits.
Seagrams Imperial Blue represents quality and craftsmanship in whiskey making, offering a smooth and refined drinking experience.
This premium whiskey features a rich amber color with complex flavors of oak, vanilla, and subtle spices.
Perfect for both casual drinking and special occasions, Imperial Blue delivers consistent quality and taste.
The 750ml bottle is ideal for home consumption and makes an excellent gift for whiskey enthusiasts.''',
        'category': categories['Drinks'],
        'vendor': vendors['vendor_drinks'],
        'price': Decimal('2800.00'),
        'stock_quantity': 18,
        'in_stock': True,
        'image_url': 'https://ke.jumia.is/unsafe/fit-in/500x500/filters:fill(white)/product/02/193585/1.jpg?9231',
        'featured': False,
        'is_active': True,
    },
    {
        'name': 'Jacob\'s Creek Classic Merlot 750ml',
        'slug': 'jacobs-creek-classic-merlot-750ml',
        'description': '''Jacob's Creek Classic Merlot is a premium red wine that showcases the best of Australian winemaking tradition.
This full-bodied wine features rich flavors of dark berries, plums, and subtle oak notes with a smooth, velvety finish.
Perfect for pairing with red meat, pasta dishes, or enjoying on its own during social gatherings.
Jacob's Creek wines are crafted using traditional winemaking techniques combined with modern innovation to deliver consistent quality.
The 750ml bottle is perfect for dinner parties, romantic evenings, or adding to your wine collection.''',
        'category': categories['Drinks'],
        'vendor': vendors['vendor_drinks'],
        'price': Decimal('1800.00'),
        'stock_quantity': 24,
        'in_stock': True,
        'image_url': 'https://ke.jumia.is/unsafe/fit-in/500x500/filters:fill(white)/product/80/283585/1.jpg?9069',
        'featured': False,
        'is_active': True,
    },
    
    # KITCHEN WARE - Kitchen Vendor
    {
        'name': '2Pcs Set Of Stainless Aluminum Sufuria No Lids + Free Gift',
        'slug': '2pcs-stainless-aluminum-sufuria-set',
        'description': '''This 2-Piece Cookware set is made of pure aluminum encapsulated in the base for fast and even heating and cooking performance.
Solid stainless steel riveted handles stay cool on the stove top, ensuring safe and comfortable cooking.
Ideal even for jiko or firewood cooking during outdoor cooking adventures and camping trips.
The durable construction ensures long-lasting performance while the aluminum core provides excellent heat distribution.
Easy to clean and maintain, these sufurias are perfect for everyday cooking needs. Comes with a free gift to enhance your cooking experience.''',
        'category': categories['Kitchen Ware'],
        'vendor': vendors['vendor_kitchen'],
        'price': Decimal('2500.00'),
        'stock_quantity': 30,
        'in_stock': True,
        'image_url': 'https://ke.jumia.is/unsafe/fit-in/500x500/filters:fill(white)/product/96/7343842/1.jpg?0140',
        'featured': True,
        'is_active': True,
    },
    {
        'name': 'Mateamoda 5 PCS Kitchenware Utensils Cookware Baking Set',
        'slug': 'mateamoda-5pcs-kitchenware-utensils-set',
        'description': '''Made from very safe food grade silicone, 100% BPA free for healthy cooking and food preparation.
Complete set contains: 1 Brush, 1 Whisk, 1 Leakage Shovel, 1 Big Scraper, 1 Small Scraper.
Hanging hole design allows convenient hanging storage when idle, saving valuable kitchen space.
The material is soft, does not deform or crack, and can be used for a long time without wear.
Adopts one-piece molding technology, making it easy to clean without concealing dirt. Heat resistant and dishwasher safe.
For first use, it is recommended to clean with hot water to remove any manufacturing odor.''',
        'category': categories['Kitchen Ware'],
        'vendor': vendors['vendor_kitchen'],
        'price': Decimal('1200.00'),
        'stock_quantity': 45,
        'in_stock': True,
        'image_url': 'https://ke.jumia.is/unsafe/fit-in/500x500/filters:fill(white)/product/01/538275/1.jpg?7415',
        'featured': False,
        'is_active': True,
    },
    {
        'name': 'Silicon Ice Cube Maker Tray',
        'slug': 'silicon-ice-cube-maker-tray',
        'description': '''Space Saving Ice Cube Maker that allows you to create a large number of ice cubes and store them inside the tray itself as you freeze.
Using our ice cube maker tray, you can save a ton of space in your freezer while keeping ice readily available.
It will quickly chill bottled beverages and is perfect for parties, gatherings, or daily use.
Simple design allows you to create up to 37 pieces of ice at a time with easy release mechanism.
Releasing ice from the tray is just as easy as pushing out the ice cubes from the sides. Made from food-grade silicone material.
Beat the heat with our premium silicone ice cube maker that's both practical and space-efficient.''',
        'category': categories['Kitchen Ware'],
        'vendor': vendors['vendor_kitchen'],
        'price': Decimal('800.00'),
        'stock_quantity': 60,
        'in_stock': True,
        'image_url': 'https://ke.jumia.is/unsafe/fit-in/500x500/filters:fill(white)/product/97/8119201/1.jpg?7783',
        'featured': False,
        'is_active': True,
    },
    {
        'name': 'Heavy Metal Manual Hand Juice Extractor Squeezer',
        'slug': 'heavy-metal-manual-juice-extractor',
        'description': '''Professional-grade manual juice extractor made from high-quality stainless steel for durability and performance.
Triangle guide nozzle with anti-dripping design ensures easy use and stable pouring without mess.
Great stability with foot design that makes the juicer easily and stably sit on the table without slipping.
Reasonable design features smooth lining and fine hole design for easy slag filtering and maximum juice extraction.
Energy-saving manual operation that's environmentally friendly and doesn't require electricity.
User-friendly handle design with comfortable grip makes juicing easier and more efficient.
Perfect for oranges, watermelons, lemons, and other citrus fruits. Hand wash only for long-term use.''',
        'category': categories['Kitchen Ware'],
        'vendor': vendors['vendor_kitchen'],
        'price': Decimal('3500.00'),
        'stock_quantity': 15,
        'in_stock': True,
        'image_url': 'https://ke.jumia.is/unsafe/fit-in/500x500/filters:fill(white)/product/41/8639882/1.jpg?9629',
        'featured': True,
        'is_active': True,
    },
    {
        'name': 'Electric Meat Grinder - Cordless Home Cooking Machine',
        'slug': 'electric-meat-grinder-cordless',
        'description': '''Simple and convenient cordless food processor that's easy to use anywhere in your kitchen.
Press and hold the top button to start the motor, release to stop - you control the degree of food processing.
Can chop garlic, onions, meat, and other ingredients in just minutes with precision and consistency.
Food-grade construction with stainless steel blades that cut food evenly from 360 degrees for uniform results.
Upper and lower blades ensure thorough processing while maintaining safety standards. Safe and odorless operation.
Easy to disassemble and clean with waterproof design that allows thorough cleaning and reuse.
USB rechargeable and portable - wireless design makes it perfect for travel, camping, or outdoor activities.
Multi-purpose functionality: chop garlic, onions, peppers, parsley, ginger, peanuts, and make baby food.''',
        'category': categories['Kitchen Ware'],
        'vendor': vendors['vendor_kitchen'],
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
category_counts = {'Smartphones': 0, 'Drinks': 0, 'Kitchen Ware': 0}

for product_data in products_data:
    product, created = Product.objects.get_or_create(
        slug=product_data['slug'],
        defaults=product_data
    )
    
    category_name = product_data['category'].name
    vendor_name = product_data['vendor'].get_full_name()
    
    if created:
        created_count += 1
        category_counts[category_name] += 1
        print(f'✓ Created: {product.name} - KES {product.price} ({category_name}) - Vendor: {vendor_name}')
    else:
        # Update existing product with new data
        for key, value in product_data.items():
            if key != 'slug':  # Don't update the slug
                setattr(product, key, value)
        product.save()
        updated_count += 1
        print(f'✓ Updated: {product.name} - KES {product.price} ({category_name}) - Vendor: {vendor_name}')

# Summary
print('='*60)
print('Seeding completed successfully!')
print(f'Vendors created: {len(vendors)}')
print(f'Products created: {created_count}')
print(f'Products updated: {updated_count}')
print(f'Total products in database: {Product.objects.count()}')
print('')
print('Vendors:')
for username, vendor in vendors.items():
    profile = vendor.profile
    product_count = vendor.products.count()
    print(f'  {vendor.get_full_name()} ({profile.business_name}) - {product_count} products')
    print(f'    Phone: {profile.phone}')
print('')
print('Products by category:')
for category_name, count in category_counts.items():
    total_in_category = Product.objects.filter(category__name=category_name).count()
    print(f'  {category_name}: {count} new, {total_in_category} total')
print('')
print(f'Total categories: {Category.objects.count()}')
print('='*60)