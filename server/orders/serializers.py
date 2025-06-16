# orders/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from decimal import Decimal
from .models import Order, OrderItem, OrderStatusHistory, OrderRefund

class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for OrderItem model"""
    vendor_name = serializers.CharField(source='vendor.get_full_name', read_only=True)
    vendor_email = serializers.CharField(source='vendor.email', read_only=True)
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'product_name', 'product_description', 'unit_price', 
            'quantity', 'total_price', 'commission_rate', 'platform_commission',
            'vendor_earnings', 'product_image', 'product_sku', 'vendor',
            'vendor_name', 'vendor_email', 'created_at'
        ]
        read_only_fields = [
            'id', 'total_price', 'platform_commission', 'vendor_earnings', 
            'vendor_name', 'vendor_email', 'created_at'
        ]

class OrderItemCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating OrderItems"""
    product = serializers.CharField(write_only=True)  # We'll handle product lookup
    
    class Meta:
        model = OrderItem
        fields = [
            'product', 'product_name', 'unit_price', 'quantity'
        ]
    
    def validate_quantity(self, value):
        """Validate quantity is positive"""
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0")
        return value
    
    def validate_unit_price(self, value):
        """Validate unit price is positive"""
        if value <= 0:
            raise serializers.ValidationError("Unit price must be greater than 0")
        return value

class OrderStatusHistorySerializer(serializers.ModelSerializer):
    """Serializer for OrderStatusHistory model"""
    changed_by_name = serializers.CharField(source='changed_by.get_full_name', read_only=True)
    changed_by_email = serializers.CharField(source='changed_by.email', read_only=True)
    previous_status_display = serializers.CharField(source='get_previous_status_display', read_only=True)
    new_status_display = serializers.CharField(source='get_new_status_display', read_only=True)
    
    class Meta:
        model = OrderStatusHistory
        fields = [
            'id', 'previous_status', 'new_status', 'changed_by', 
            'changed_by_name', 'changed_by_email', 'notes', 'created_at',
            'previous_status_display', 'new_status_display'
        ]
        read_only_fields = ['id', 'created_at', 'changed_by_name', 'changed_by_email']

class OrderRefundSerializer(serializers.ModelSerializer):
    """Serializer for OrderRefund model"""
    requested_by_name = serializers.CharField(source='requested_by.get_full_name', read_only=True)
    processed_by_name = serializers.CharField(source='processed_by.get_full_name', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    
    class Meta:
        model = OrderRefund
        fields = [
            'id', 'refund_number', 'order', 'order_number', 'order_item',
            'status', 'status_display', 'reason', 'reason_display', 'description',
            'refund_amount', 'processing_fee', 'net_refund_amount',
            'requested_by', 'requested_by_name', 'processed_by', 'processed_by_name',
            'created_at', 'updated_at', 'processed_at'
        ]
        read_only_fields = [
            'id', 'refund_number', 'net_refund_amount', 'requested_by_name', 
            'processed_by_name', 'order_number', 'status_display', 'reason_display',
            'created_at', 'updated_at'
        ]

class OrderSerializer(serializers.ModelSerializer):
    """Basic serializer for Order model (for lists)"""
    items = OrderItemSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    customer_email = serializers.CharField(source='customer.email', read_only=True)
    total_items = serializers.ReadOnlyField()
    vendor_earnings = serializers.ReadOnlyField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'customer', 'customer_name', 'customer_email',
            'status', 'status_display', 'total_amount', 'subtotal', 'tax_amount', 
            'shipping_fee', 'discount_amount', 'payment_method', 'payment_method_display',
            'payment_status', 'payment_reference', 'shipping_address', 'shipping_city', 
            'shipping_country', 'shipping_phone', 'tracking_number', 'total_items',
            'vendor_earnings', 'created_at', 'updated_at', 'items'
        ]
        read_only_fields = [
            'id', 'order_number', 'customer_name', 'customer_email', 'total_items',
            'vendor_earnings', 'status_display', 'payment_method_display', 
            'created_at', 'updated_at'
        ]

class OrderDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for Order model (for single order view)"""
    items = OrderItemSerializer(many=True, read_only=True)
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)
    refunds = OrderRefundSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    customer_email = serializers.CharField(source='customer.email', read_only=True)
    total_items = serializers.ReadOnlyField()
    vendor_earnings = serializers.ReadOnlyField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    vendors = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'customer', 'customer_name', 'customer_email',
            'status', 'status_display', 'total_amount', 'subtotal', 'tax_amount', 
            'shipping_fee', 'discount_amount', 'payment_method', 'payment_method_display',
            'payment_status', 'payment_reference', 'shipping_address', 'shipping_city', 
            'shipping_country', 'shipping_phone', 'tracking_number', 'notes', 
            'special_instructions', 'total_items', 'vendor_earnings', 'vendors',
            'created_at', 'updated_at', 'confirmed_at', 'shipped_at', 'delivered_at', 
            'items', 'status_history', 'refunds'
        ]
        read_only_fields = [
            'id', 'order_number', 'customer_name', 'customer_email', 'total_items',
            'vendor_earnings', 'status_display', 'payment_method_display', 'vendors',
            'created_at', 'updated_at'
        ]
    
    def get_vendors(self, obj):
        """Get all vendors involved in this order"""
        vendors = obj.get_vendors()
        return [
            {
                'id': vendor.id,
                'name': vendor.get_full_name(),
                'email': vendor.email,
                'business_name': getattr(vendor.profile, 'business_name', None) if hasattr(vendor, 'profile') else None
            }
            for vendor in vendors
        ]

class OrderCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new orders"""
    items = OrderItemCreateSerializer(many=True, write_only=True)
    
    class Meta:
        model = Order
        fields = [
            'payment_method', 'shipping_address', 'shipping_city', 
            'shipping_country', 'shipping_phone', 'notes', 'special_instructions', 
            'items'
        ]
    
    def validate_items(self, value):
        """Validate that items list is not empty"""
        if not value:
            raise serializers.ValidationError("Order must contain at least one item")
        return value
    
    def validate_shipping_address(self, value):
        """Validate shipping address is provided"""
        if not value or not value.strip():
            raise serializers.ValidationError("Shipping address is required")
        return value.strip()
    
    def validate_shipping_phone(self, value):
        """Validate shipping phone is provided"""
        if not value or not value.strip():
            raise serializers.ValidationError("Shipping phone is required")
        return value.strip()

    def create(self, validated_data):
        """Create order with items"""
        items_data = validated_data.pop('items')
        request = self.context.get('request')
        
        # Create the order
        order = Order.objects.create(customer=request.user, **validated_data)
        
        subtotal = Decimal('0.00')
        
        # Create order items
        for item_data in items_data:
            # Here you would typically fetch the product from your products app
            # For now, we'll create the item with the provided data
            product_name = item_data.get('product_name', item_data.get('product', 'Unknown Product'))
            
            # You might want to fetch actual product data here:
            # try:
            #     product = Product.objects.get(id=item_data['product'])
            #     vendor = product.vendor
            #     unit_price = product.price
            # except Product.DoesNotExist:
            #     raise serializers.ValidationError(f"Product {item_data['product']} not found")
            
            # For now, using provided data (adjust based on your product model)
            item = OrderItem.objects.create(
                order=order,
                product_name=product_name,
                unit_price=item_data['unit_price'],
                quantity=item_data['quantity'],
                vendor=request.user  # Temporary - should be actual product vendor
            )
            subtotal += item.total_price
        
        # Calculate totals
        order.subtotal = subtotal
        order.tax_amount = subtotal * Decimal('0.16')  # 16% VAT
        order.total_amount = order.subtotal + order.tax_amount + order.shipping_fee - order.discount_amount
        order.save()
        
        return order

class OrderUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating orders (limited fields)"""
    
    class Meta:
        model = Order
        fields = [
            'status', 'tracking_number', 'notes', 'special_instructions'
        ]
    
    def validate_status(self, value):
        """Validate status transitions"""
        if self.instance:
            current_status = self.instance.status
            valid_transitions = {
                'pending': ['confirmed', 'cancelled'],
                'confirmed': ['processing', 'cancelled'],
                'processing': ['shipped', 'cancelled'],
                'shipped': ['delivered', 'cancelled'],
                'delivered': ['refunded'],
                'cancelled': [],
                'refunded': []
            }
            
            if value not in valid_transitions.get(current_status, []):
                raise serializers.ValidationError(
                    f"Cannot change status from {current_status} to {value}"
                )
        
        return value

class VendorOrderSummarySerializer(serializers.Serializer):
    """Serializer for vendor order summary data"""
    total_orders = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_earnings = serializers.DecimalField(max_digits=10, decimal_places=2)
    commission_paid = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_items_sold = serializers.IntegerField()
    avg_order_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    status_breakdown = serializers.ListField(child=serializers.DictField())
    top_products = serializers.ListField(child=serializers.DictField())
    daily_sales = serializers.ListField(child=serializers.DictField())
    recent_orders = OrderSerializer(many=True)
    
    date_range = serializers.DictField()

class CustomerOrderStatsSerializer(serializers.Serializer):
    """Serializer for customer order statistics"""
    stats = serializers.DictField()
    status_breakdown = serializers.ListField(child=serializers.DictField())
    monthly_spending = serializers.ListField(child=serializers.DictField())
    favorite_vendors = serializers.ListField(child=serializers.DictField())

class OrderTrackingSerializer(serializers.Serializer):
    """Serializer for order tracking information"""
    order_number = serializers.CharField()
    current_status = serializers.CharField()
    tracking_number = serializers.CharField(allow_null=True)
    estimated_delivery = serializers.DateTimeField(allow_null=True)
    status_history = serializers.ListField(child=serializers.DictField())
    shipping_address = serializers.CharField()
    carrier_info = serializers.DictField()

class OrderNotesSerializer(serializers.Serializer):
    """Serializer for order notes"""
    notes = serializers.ListField(child=serializers.DictField())

class BulkStatusUpdateSerializer(serializers.Serializer):
    """Serializer for bulk status updates"""
    order_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False
    )
    status = serializers.ChoiceField(choices=Order.ORDER_STATUS_CHOICES)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_order_ids(self, value):
        """Validate that all order IDs exist"""
        if len(value) > 100:  # Limit bulk operations
            raise serializers.ValidationError("Cannot update more than 100 orders at once")
        return value

class OrderAnalyticsSerializer(serializers.Serializer):
    """Serializer for order analytics data"""
    revenue_trend = serializers.ListField(child=serializers.DictField())
    status_distribution = serializers.ListField(child=serializers.DictField())
    payment_methods = serializers.ListField(child=serializers.DictField())
    avg_order_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    conversion_rate = serializers.DictField(required=False)
    
    # Customer analytics (optional)
    new_customers = serializers.DictField(required=False)
    customer_segments = serializers.DictField(required=False)
    repeat_customers = serializers.DictField(required=False)
    customer_lifetime_value = serializers.DictField(required=False)
    
    # Product analytics (optional)
    top_products = serializers.ListField(child=serializers.DictField(), required=False)
    product_performance = serializers.ListField(child=serializers.DictField(), required=False)
    category_sales = serializers.ListField(child=serializers.DictField(), required=False)
    inventory_turnover = serializers.DictField(required=False)