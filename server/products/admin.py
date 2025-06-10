from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Product

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'product_count', 'created_at']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'description']
    list_filter = ['created_at']
    
    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Number of Products'

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name', 
        'category', 
        'price', 
        'stock_quantity',
        'in_stock',
        'in_stock_status', 
        'is_active',
        'featured',
        'created_at'
    ]
    
    list_filter = [
        'category', 
        'in_stock', 
        'is_active', 
        'featured',
        'created_at'
    ]
    
    search_fields = ['name', 'description', 'category__name']
    
    prepopulated_fields = {'slug': ('name',)}
    
    list_editable = ['price', 'stock_quantity', 'in_stock', 'is_active', 'featured']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'category')
        }),
        ('Pricing & Stock', {
            'fields': ('price', 'stock_quantity', 'in_stock')
        }),
        ('Media', {
            'fields': ('image_url',)
        }),
        ('Settings', {
            'fields': ('is_active', 'featured'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def in_stock_status(self, obj):
        """Display stock status with color coding"""
        if obj.is_available:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Available ({})</span>',
                obj.stock_quantity
            )
        elif obj.in_stock and obj.stock_quantity <= 0:
            return format_html(
                '<span style="color: orange; font-weight: bold;">⚠ Out of Stock</span>'
            )
        else:
            return format_html(
                '<span style="color: red; font-weight: bold;">✗ Not Available</span>'
            )
    
    in_stock_status.short_description = 'Stock Status'
    
    # Add actions for bulk operations
    actions = ['mark_as_featured', 'mark_as_not_featured', 'mark_as_out_of_stock']
    
    def mark_as_featured(self, request, queryset):
        updated = queryset.update(featured=True)
        self.message_user(request, f'{updated} products marked as featured.')
    mark_as_featured.short_description = "Mark selected products as featured"
    
    def mark_as_not_featured(self, request, queryset):
        updated = queryset.update(featured=False)
        self.message_user(request, f'{updated} products unmarked as featured.')
    mark_as_not_featured.short_description = "Remove featured status from selected products"
    
    def mark_as_out_of_stock(self, request, queryset):
        updated = queryset.update(in_stock=False, stock_quantity=0)
        self.message_user(request, f'{updated} products marked as out of stock.')
    mark_as_out_of_stock.short_description = "Mark selected products as out of stock"