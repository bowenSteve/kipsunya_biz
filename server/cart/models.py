# cart/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid

class Cart(models.Model):
    """
    Cart model to store user's cart items
    Supports both authenticated users and anonymous sessions
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='cart')
    session_id = models.CharField(max_length=255, null=True, blank=True)  # For anonymous users
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['session_id']),
        ]
    
    def __str__(self):
        if self.user:
            return f"Cart for {self.user.email}"
        return f"Anonymous Cart {self.session_id}"
    @property
    def total_items(self):
        """Get total number of items in cart"""
        return sum(item.quantity for item in self.items.all())
    
    @property
    def subtotal(self):
        """Calculate cart subtotal - Fixed to return Decimal"""
        total = Decimal('0.00')
        for item in self.items.all():
            # Ensure unit_price is Decimal
            unit_price = Decimal(str(item.unit_price))
            item_total = unit_price * item.quantity
            total += item_total
        return total
    
    @property
    def total_amount(self):
        """Calculate total with tax and shipping - Fixed to use Decimal"""
        subtotal = self.subtotal
        tax_rate = Decimal('0.16')  # 16% VAT
        tax_amount = subtotal * tax_rate
        # You can add shipping calculation logic here
        shipping_fee = Decimal('0.00')  # Free shipping for now
        return subtotal + tax_amount + shipping_fee
    
    def clear(self):
        """Clear all items from cart"""
        self.items.all().delete()
    @property
    def total_items(self):
        """Get total number of items in cart"""
        return sum(item.quantity for item in self.items.all())
    
    @property
    def subtotal(self):
        """Calculate cart subtotal"""
        return sum(item.total_price for item in self.items.all())
    
    @property
    def total_amount(self):
        """Calculate total with tax and shipping"""
        subtotal = self.subtotal
        tax_rate = Decimal('0.16')  # 16% VAT
        tax_amount = subtotal * tax_rate
        # You can add shipping calculation logic here
        shipping_fee = Decimal('0.00')  # Free shipping for now
        return subtotal + tax_amount + shipping_fee
    
    def clear(self):
        """Clear all items from cart"""
        self.items.all().delete()


class CartItem(models.Model):
    """
    Individual items in the cart
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    
    # Product information (snapshot approach like orders)
    product_id = models.PositiveIntegerField()  # Reference to actual product
    product_name = models.CharField(max_length=255)
    product_description = models.TextField(blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    product_image = models.URLField(blank=True, null=True)
    product_slug = models.SlugField(max_length=200)
    
    # Vendor information
    vendor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart_items')
    vendor_name = models.CharField(max_length=255)
    
    # Cart item specifics
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-added_at']
        unique_together = ['cart', 'product_id']  # Prevent duplicate products in same cart
        indexes = [
            models.Index(fields=['cart', 'product_id']),
            models.Index(fields=['vendor', 'added_at']),
        ]
    
    def __str__(self):
        return f"{self.product_name} x{self.quantity} in {self.cart}"
    
    @property
    def total_price(self):
        """Calculate total price for this cart item"""
        return self.unit_price * self.quantity
    
    def save(self, *args, **kwargs):
        """Update cart's updated_at when item is saved"""
        super().save(*args, **kwargs)
        # Update cart timestamp
        self.cart.save()
    @property
    def total_price(self):
        """Calculate total price for this cart item - Fixed to return Decimal"""
        unit_price = Decimal(str(self.unit_price))
        return unit_price * self.quantity
    
    def save(self, *args, **kwargs):
        """Update cart's updated_at when item is saved"""
        super().save(*args, **kwargs)
        # Update cart timestamp
        self.cart.save()

class SavedItem(models.Model):
    """
    Items saved for later (wishlist functionality)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_items')
    
    # Product information
    product_id = models.PositiveIntegerField()
    product_name = models.CharField(max_length=255)
    product_description = models.TextField(blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    product_image = models.URLField(blank=True, null=True)
    product_slug = models.SlugField(max_length=200)
    
    # Vendor information
    vendor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_cart_items')
    vendor_name = models.CharField(max_length=255)
    
    saved_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-saved_at']
        unique_together = ['user', 'product_id']  # Prevent duplicate saved items
        indexes = [
            models.Index(fields=['user', 'saved_at']),
        ]
    
    def __str__(self):
        return f"Saved: {self.product_name} by {self.user.email}"