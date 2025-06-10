# server/seed.py
from products.models import Category, Product
from decimal import Decimal

print('Starting to seed phone products...')

# Create or get the Smartphones category
smartphone_category, created = Category.objects.get_or_create(
    name='Smartphones',
    defaults={
        'slug': 'smartphones',
        'description': 'Latest smartphones and mobile devices'
    }
)

if created:
    print(f'Created category: {smartphone_category.name}')
else:
    print(f'Using existing category: {smartphone_category.name}')

# Phone products data
phones_data = [
    {
        'name': 'Vivo Y400 Pro',
        'slug': 'vivo-y400-pro',
        'description': '''The Vivo Y400 Pro features a stunning 6.77" AMOLED display with 120Hz refresh rate and 1300 nits peak brightness. 
Powered by Android 15 with Funtouch 15, it offers 8GB RAM and 128GB/256GB storage options. 
The device boasts a 50MP main camera with f/1.8 aperture and a 2MP depth sensor. 
With a 5500mAh battery and 90W fast charging, this phone delivers exceptional performance and battery life.
Key specs: 162g weight, 7.5mm thickness, IP65 dust/water resistance, Nano-SIM support.''',
        'category': smartphone_category,
        'price': Decimal('399.99'),
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
        'category': smartphone_category,
        'price': Decimal('299.00'),
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
        'category': smartphone_category,
        'price': Decimal('409.00'),
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
        'category': smartphone_category,
        'price': Decimal('199.99'),
        'stock_quantity': 25,
        'in_stock': True,
        'image_url': 'https://fdn2.gsmarena.com/vv/pics/motorola/motorola-moto-g45-5g-1.jpg',
        'featured': False,
        'is_active': True,
    },
]

# Create products
created_count = 0
updated_count = 0

for phone_data in phones_data:
    product, created = Product.objects.get_or_create(
        slug=phone_data['slug'],
        defaults=phone_data
    )
    
    if created:
        created_count += 1
        print(f'✓ Created: {product.name} - ${product.price}')
    else:
        # Update existing product with new data
        for key, value in phone_data.items():
            if key != 'slug':  # Don't update the slug
                setattr(product, key, value)
        product.save()
        updated_count += 1
        print(f'✓ Updated: {product.name} - ${product.price}')

# Summary
print('='*50)
print('Seeding completed successfully!')
print(f'Products created: {created_count}')
print(f'Products updated: {updated_count}')
print(f'Total products: {Product.objects.count()}')
print(f'Categories: {Category.objects.count()}')
print('='*50)