# products/serializers.py - Updated for CRUD operations
from rest_framework import serializers
from django.utils.text import slugify
from .models import Product, Category

class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'product_count', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
    
    def get_product_count(self, obj):
        return obj.products.count()
    
    def validate_name(self, value):
        """Ensure category name is unique"""
        if self.instance:
            # If updating, exclude current instance from uniqueness check
            if Category.objects.filter(name__iexact=value).exclude(id=self.instance.id).exists():
                raise serializers.ValidationError("A category with this name already exists.")
        else:
            # If creating, check for uniqueness
            if Category.objects.filter(name__iexact=value).exists():
                raise serializers.ValidationError("A category with this name already exists.")
        return value

class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True, required=True)
    is_available = serializers.ReadOnlyField()
    
    # Vendor information fields - only for authenticated users
    vendor_name = serializers.SerializerMethodField()
    vendor_phone = serializers.SerializerMethodField()
    vendor_business = serializers.SerializerMethodField()
    vendor_id = serializers.SerializerMethodField()
    
    # Add total_sold for analytics (you may need to add this field to your model)
    total_sold = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id',
            'name', 
            'description', 
            'category',
            'category_id',
            'price', 
            'stock_quantity',
            'in_stock', 
            'is_available',
            'image_url', 
            'slug',
            'featured',
            'is_active',
            'created_at', 
            'updated_at',
            # Vendor fields
            'vendor_name',
            'vendor_phone', 
            'vendor_business',
            'vendor_id',
            'total_sold',
        ]
        read_only_fields = ['created_at', 'updated_at', 'slug']
    
    def get_vendor_name(self, obj):
        """Get vendor's full name - only for authenticated users"""
        request = self.context.get('request')
        if request and request.user.is_authenticated and obj.vendor:
            return obj.vendor.get_full_name() or obj.vendor.email
        return None
    
    def get_vendor_phone(self, obj):
        """Get vendor's phone number - only for authenticated users"""
        request = self.context.get('request')
        if request and request.user.is_authenticated and obj.vendor:
            try:
                return obj.vendor.profile.phone
            except:
                return None
        return None
    
    def get_vendor_business(self, obj):
        """Get vendor's business name - only for authenticated users"""
        request = self.context.get('request')
        if request and request.user.is_authenticated and obj.vendor:
            try:
                return obj.vendor.profile.business_name
            except:
                return None
        return None
    
    def get_vendor_id(self, obj):
        """Get vendor's ID - only for authenticated users"""
        request = self.context.get('request')
        if request and request.user.is_authenticated and obj.vendor:
            return obj.vendor.id
        return None
    
    def get_total_sold(self, obj):
        """Get total items sold - placeholder for now"""
        # You can implement this based on your order system
        # For now, return a random number for demo purposes
        import random
        return random.randint(0, 50)
    
    def validate_category_id(self, value):
        """Validate that the category exists"""
        try:
            Category.objects.get(id=value)
        except Category.DoesNotExist:
            raise serializers.ValidationError("Category does not exist.")
        return value
    
    def validate_price(self, value):
        """Validate price is positive"""
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than 0.")
        return value
    
    def validate_stock_quantity(self, value):
        """Validate stock quantity is not negative"""
        if value < 0:
            raise serializers.ValidationError("Stock quantity cannot be negative.")
        return value
    
    def validate_name(self, value):
        """Validate product name"""
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Product name must be at least 3 characters long.")
        
        # Check for uniqueness within the same vendor (if updating)
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            queryset = Product.objects.filter(name__iexact=value.strip(), vendor=request.user)
            if self.instance:
                queryset = queryset.exclude(id=self.instance.id)
            if queryset.exists():
                raise serializers.ValidationError("You already have a product with this name.")
        
        return value.strip()
    
    def create(self, validated_data):
        """Create product with auto-generated slug"""
        category_id = validated_data.pop('category_id')
        category = Category.objects.get(id=category_id)
        
        # Generate unique slug
        name = validated_data['name']
        base_slug = slugify(name)
        slug = base_slug
        counter = 1
        
        while Product.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        validated_data['slug'] = slug
        validated_data['category'] = category
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Update product, regenerate slug if name changed"""
        category_id = validated_data.pop('category_id', None)
        
        if category_id:
            category = Category.objects.get(id=category_id)
            validated_data['category'] = category
        
        # Check if name changed and regenerate slug
        new_name = validated_data.get('name')
        if new_name and new_name != instance.name:
            base_slug = slugify(new_name)
            slug = base_slug
            counter = 1
            
            while Product.objects.filter(slug=slug).exclude(id=instance.id).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            validated_data['slug'] = slug
        
        return super().update(instance, validated_data)

# Simple serializer for creating products (minimal fields)
class ProductCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'name',
            'description', 
            'category',
            'price',
            'stock_quantity',
            'image_url',
            'featured',
            'is_active'
        ]
    
    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than 0.")
        return value
    
    def validate_stock_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError("Stock quantity cannot be negative.")
        return value