from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal

class Category(models.Model):
    """Category model for organizing products"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    slug = models.SlugField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Product(models.Model):
    """Product model for e-commerce items"""
    
    # Basic product information
    name = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    
    # Pricing
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    # Stock management
    in_stock = models.BooleanField(default=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    
    # Images
    image_url = models.URLField(max_length=500, blank=True, null=True)
    
    # SEO and organization
    slug = models.SlugField(max_length=200, unique=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Additional fields for e-commerce
    is_active = models.BooleanField(default=True)
    featured = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category', 'in_stock']),
            models.Index(fields=['price']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return self.name
    
    @property
    def is_available(self):
        """Check if product is available for purchase"""
        return self.in_stock and self.stock_quantity > 0 and self.is_active
    
    def save(self, *args, **kwargs):
        """Auto-update in_stock based on stock_quantity"""
        if self.stock_quantity <= 0:
            self.in_stock = False
        super().save(*args, **kwargs)