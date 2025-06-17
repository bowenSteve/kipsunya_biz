# cart/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Cart, CartItem, SavedItem

class CartItemSerializer(serializers.ModelSerializer):
    """Serializer for CartItem model"""
    total_price = serializers.ReadOnlyField()
    vendor_email = serializers.CharField(source='vendor.email', read_only=True)
    
    class Meta:
        model = CartItem
        fields = [
            'id', 'product_id', 'product_name', 'product_description', 
            'unit_price', 'product_image', 'product_slug', 'vendor', 
            'vendor_name', 'vendor_email', 'quantity', 'total_price',
            'added_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'total_price', 'vendor_name', 'vendor_email', 
            'added_at', 'updated_at'
        ]

class CartItemCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating cart items"""
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    
    class Meta:
        model = CartItem
        fields = ['product_id', 'quantity']
    
    def validate_product_id(self, value):
        """Validate that product exists and is available"""
        # Import here to avoid circular imports
        from products.models import Product
        
        try:
            product = Product.objects.get(id=value, is_active=True)
            if not product.is_available:
                raise serializers.ValidationError("Product is not available")
            return value
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found")
    
    def validate_quantity(self, value):
        """Validate quantity is positive"""
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0")
        return value

class CartSerializer(serializers.ModelSerializer):
    """Serializer for Cart model"""
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.ReadOnlyField()
    subtotal = serializers.ReadOnlyField()
    total_amount = serializers.ReadOnlyField()
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = Cart
        fields = [
            'id', 'user', 'user_email', 'total_items', 'subtotal', 
            'total_amount', 'created_at', 'updated_at', 'items'
        ]
        read_only_fields = [
            'id', 'user', 'user_email', 'total_items', 'subtotal', 
            'total_amount', 'created_at', 'updated_at'
        ]

class CartSummarySerializer(serializers.ModelSerializer):
    """Lightweight serializer for cart summary"""
    total_items = serializers.ReadOnlyField()
    subtotal = serializers.ReadOnlyField()
    total_amount = serializers.ReadOnlyField()
    
    class Meta:
        model = Cart
        fields = ['id', 'total_items', 'subtotal', 'total_amount', 'updated_at']

class SavedItemSerializer(serializers.ModelSerializer):
    """Serializer for SavedItem model"""
    vendor_email = serializers.CharField(source='vendor.email', read_only=True)
    
    class Meta:
        model = SavedItem
        fields = [
            'id', 'product_id', 'product_name', 'product_description',
            'unit_price', 'product_image', 'product_slug', 'vendor',
            'vendor_name', 'vendor_email', 'saved_at'
        ]
        read_only_fields = [
            'id', 'vendor_name', 'vendor_email', 'saved_at'
        ]

class SavedItemCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating saved items"""
    product_id = serializers.IntegerField()
    
    class Meta:
        model = SavedItem
        fields = ['product_id']
    
    def validate_product_id(self, value):
        """Validate that product exists"""
        from products.models import Product
        
        try:
            Product.objects.get(id=value, is_active=True)
            return value
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found")

class MoveToCartSerializer(serializers.Serializer):
    """Serializer for moving saved items to cart"""
    saved_item_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, default=1)
    
    def validate_saved_item_id(self, value):
        """Validate that saved item exists and belongs to user"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication required")
        
        try:
            saved_item = SavedItem.objects.get(id=value, user=request.user)
            return value
        except SavedItem.DoesNotExist:
            raise serializers.ValidationError("Saved item not found")

class CartQuantityUpdateSerializer(serializers.Serializer):
    """Serializer for updating cart item quantity"""
    quantity = serializers.IntegerField(min_value=1)
    
    def validate_quantity(self, value):
        """Validate quantity against product stock"""
        cart_item = self.context.get('cart_item')
        if cart_item:
            from products.models import Product
            try:
                product = Product.objects.get(id=cart_item.product_id)
                if value > product.stock_quantity:
                    raise serializers.ValidationError(
                        f"Only {product.stock_quantity} items available in stock"
                    )
            except Product.DoesNotExist:
                pass  # Product might have been deleted
        
        return value

class CartToOrderSerializer(serializers.Serializer):
    """Serializer for converting cart to order"""
    payment_method = serializers.ChoiceField(
        choices=[
            ('mpesa', 'M-Pesa'),
            ('credit_card', 'Credit Card'),
            ('bank_transfer', 'Bank Transfer'),
            ('cash_on_delivery', 'Cash on Delivery'),
        ]
    )
    shipping_address = serializers.CharField()
    shipping_city = serializers.CharField()
    shipping_country = serializers.CharField(default='Kenya')
    shipping_phone = serializers.CharField()
    notes = serializers.CharField(required=False, allow_blank=True)
    special_instructions = serializers.CharField(required=False, allow_blank=True)
    
    def validate_shipping_address(self, value):
        """Validate shipping address is not empty"""
        if not value.strip():
            raise serializers.ValidationError("Shipping address is required")
        return value.strip()
    
    def validate_shipping_phone(self, value):
        """Validate shipping phone is not empty"""
        if not value.strip():
            raise serializers.ValidationError("Shipping phone is required")
        return value.strip()

class BulkCartActionSerializer(serializers.Serializer):
    """Serializer for bulk cart actions"""
    ACTION_CHOICES = [
        ('remove', 'Remove Items'),
        ('save_for_later', 'Save for Later'),
        ('move_to_cart', 'Move to Cart'),
    ]
    
    action = serializers.ChoiceField(choices=ACTION_CHOICES)
    item_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False
    )
    
    def validate_item_ids(self, value):
        """Validate that item IDs exist and belong to user"""
        if len(value) > 50:  # Limit bulk operations
            raise serializers.ValidationError("Cannot process more than 50 items at once")
        return value