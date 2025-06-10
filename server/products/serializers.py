from rest_framework import serializers
from .models import Product, Category

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description']

class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    is_available = serializers.ReadOnlyField()
    
    class Meta:
        model = Product
        fields = [
            'id',
            'name', 
            'description', 
            'category',
            'price', 
            'stock_quantity',
            'in_stock', 
            'is_available',
            'image_url', 
            'slug',
            'featured',
            'is_active',
            'created_at', 
            'updated_at'
        ]