# orders/models.py
from django.db import models
from django.contrib.auth.models import User  # Use Django's built-in User
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid

# DO NOT define a User model here - use Django's built-in User

class Order(models.Model):
    ORDER_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('mpesa', 'M-Pesa'),
        ('credit_card', 'Credit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash_on_delivery', 'Cash on Delivery'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=50, unique=True, editable=False)
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    
    # Order details
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    
    # Payment details
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_status = models.CharField(max_length=20, default='pending')
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    
    # Shipping details
    shipping_address = models.TextField()
    shipping_city = models.CharField(max_length=100)
    shipping_country = models.CharField(max_length=100, default='Kenya')
    shipping_phone = models.CharField(max_length=20)
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    
    # Special instructions
    notes = models.TextField(blank=True, null=True)
    special_instructions = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(blank=True, null=True)
    shipped_at = models.DateTimeField(blank=True, null=True)
    delivered_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['order_number']),
            models.Index(fields=['created_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Order {self.order_number} - {self.customer.email}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)

    def generate_order_number(self):
        """Generate unique order number"""
        import datetime
        now = datetime.datetime.now()
        base = f"ORD-{now.year}-{now.month:02d}"
        
        # Get the last order number for this month
        last_order = Order.objects.filter(
            order_number__startswith=base
        ).order_by('-order_number').first()
        
        if last_order:
            last_number = int(last_order.order_number.split('-')[-1])
            new_number = last_number + 1
        else:
            new_number = 1000
            
        return f"{base}-{new_number}"

    @property
    def total_items(self):
        """Get total number of items in the order"""
        return sum(item.quantity for item in self.items.all())

    @property
    def vendor_earnings(self):
        """Calculate total vendor earnings (after platform commission)"""
        return sum(item.vendor_earnings for item in self.items.all())

    def get_vendors(self):
        """Get all vendors involved in this order"""
        return User.objects.filter(
            sold_items__order=self
        ).distinct()


class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    # product = models.ForeignKey('products.Product', on_delete=models.CASCADE)  # Uncomment when you have products app
    vendor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sold_items')
    
    # Item details at time of purchase
    product_name = models.CharField(max_length=255)
    product_description = models.TextField(blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    total_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    
    # Commission and earnings
    commission_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=15.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    platform_commission = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    vendor_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Product snapshot data
    product_image = models.URLField(blank=True, null=True)
    product_sku = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order', 'vendor']),
            models.Index(fields=['vendor', 'created_at']),
        ]

    def __str__(self):
        return f"{self.product_name} x{self.quantity} - {self.order.order_number}"

    def save(self, *args, **kwargs):
        # Calculate totals
        self.total_price = self.unit_price * self.quantity
        self.platform_commission = (self.total_price * self.commission_rate) / 100
        self.vendor_earnings = self.total_price - self.platform_commission
        
        super().save(*args, **kwargs)


class OrderStatusHistory(models.Model):
    """Track order status changes"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    previous_status = models.CharField(max_length=20, blank=True, null=True)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Order status histories"

    def __str__(self):
        return f"{self.order.order_number}: {self.previous_status} → {self.new_status}"


class OrderRefund(models.Model):
    REFUND_STATUS_CHOICES = [
        ('requested', 'Requested'),
        ('approved', 'Approved'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    ]
    
    REFUND_REASON_CHOICES = [
        ('defective', 'Defective Product'),
        ('not_as_described', 'Not as Described'),
        ('wrong_item', 'Wrong Item Received'),
        ('damaged', 'Damaged in Shipping'),
        ('change_of_mind', 'Change of Mind'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='refunds')
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, null=True, blank=True)
    
    # Refund details
    refund_number = models.CharField(max_length=50, unique=True, editable=False)
    status = models.CharField(max_length=20, choices=REFUND_STATUS_CHOICES, default='requested')
    reason = models.CharField(max_length=20, choices=REFUND_REASON_CHOICES)
    description = models.TextField()
    
    # Amounts
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    processing_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_refund_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    
    # Tracking
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='requested_refunds')
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_refunds')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Refund {self.refund_number} - {self.order.order_number}"

    def save(self, *args, **kwargs):
        if not self.refund_number:
            self.refund_number = self.generate_refund_number()
        self.net_refund_amount = self.refund_amount - self.processing_fee
        super().save(*args, **kwargs)

    def generate_refund_number(self):
        """Generate unique refund number"""
        import datetime
        now = datetime.datetime.now()
        base = f"REF-{now.year}-{now.month:02d}"
        
        last_refund = OrderRefund.objects.filter(
            refund_number__startswith=base
        ).order_by('-refund_number').first()
        
        if last_refund:
            last_number = int(last_refund.refund_number.split('-')[-1])
            new_number = last_number + 1
        else:
            new_number = 1000
            
        return f"{base}-{new_number}"