# cart/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Cart, CartItem, SavedItem

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user_display', 'total_items', 'subtotal_display', 
        'created_at', 'updated_at', 'is_anonymous'
    ]
    list_filter = ['created_at', 'updated_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'session_id']
    readonly_fields = ['id', 'created_at', 'updated_at', 'total_items', 'subtotal']
    
    def user_display(self, obj):
        if obj.user:
            return format_html(
                '<strong>{}</strong><br><small>{}</small>',
                obj.user.get_full_name() or obj.user.email,
                obj.user.email
            )
        return format_html(
            '<em>Anonymous</em><br><small>Session: {}</small>',
            obj.session_id[:8] + '...' if obj.session_id else 'No session'
        )
    user_display.short_description = 'User'
    
    def subtotal_display(self, obj):
        return format_html('KES {:,.2f}', obj.subtotal)
    subtotal_display.short_description = 'Subtotal'
    
    def is_anonymous(self, obj):
        return obj.user is None
    is_anonymous.boolean = True
    is_anonymous.short_description = 'Anonymous'
    
    # Custom actions
    actions = ['clear_selected_carts', 'delete_empty_carts']
    
    def clear_selected_carts(self, request, queryset):
        total_items = 0
        for cart in queryset:
            items_count = cart.items.count()
            cart.clear()
            total_items += items_count
        
        self.message_user(
            request, 
            f'Cleared {total_items} items from {queryset.count()} carts.'
        )
    clear_selected_carts.short_description = "Clear selected carts"
    
    def delete_empty_carts(self, request, queryset):
        empty_carts = queryset.filter(items__isnull=True)
        count = empty_carts.count()
        empty_carts.delete()
        
        self.message_user(
            request, 
            f'Deleted {count} empty carts.'
        )
    delete_empty_carts.short_description = "Delete empty carts"

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ['id', 'total_price', 'added_at', 'updated_at']
    fields = [
        'product_name', 'vendor_name', 'unit_price', 'quantity', 
        'total_price', 'added_at'
    ]

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = [
        'product_name', 'cart_user', 'vendor_name', 'unit_price_display',
        'quantity', 'total_price_display', 'added_at'
    ]
    list_filter = ['added_at', 'updated_at', 'vendor']
    search_fields = [
        'product_name', 'cart__user__email', 'vendor__email',
        'cart__session_id'
    ]
    readonly_fields = [
        'id', 'total_price', 'added_at', 'updated_at'
    ]
    
    def cart_user(self, obj):
        if obj.cart.user:
            return obj.cart.user.email
        return f"Anonymous ({obj.cart.session_id[:8]}...)"
    cart_user.short_description = 'Cart User'
    
    def unit_price_display(self, obj):
        return format_html('KES {:,.2f}', obj.unit_price)
    unit_price_display.short_description = 'Unit Price'
    
    def total_price_display(self, obj):
        return format_html('KES {:,.2f}', obj.total_price)
    total_price_display.short_description = 'Total Price'

@admin.register(SavedItem)
class SavedItemAdmin(admin.ModelAdmin):
    list_display = [
        'product_name', 'user_display', 'vendor_name', 
        'unit_price_display', 'saved_at'
    ]
    list_filter = ['saved_at', 'vendor']
    search_fields = [
        'product_name', 'user__email', 'user__first_name', 
        'user__last_name', 'vendor__email'
    ]
    readonly_fields = ['id', 'saved_at']
    
    def user_display(self, obj):
        return format_html(
            '<strong>{}</strong><br><small>{}</small>',
            obj.user.get_full_name() or obj.user.email,
            obj.user.email
        )
    user_display.short_description = 'User'
    
    def unit_price_display(self, obj):
        return format_html('KES {:,.2f}', obj.unit_price)
    unit_price_display.short_description = 'Unit Price'
    
    # Custom actions
    actions = ['move_to_cart']
    
    def move_to_cart(self, request, queryset):
        moved_count = 0
        for saved_item in queryset:
            try:
                # Get or create cart for user
                cart, created = Cart.objects.get_or_create(user=saved_item.user)
                
                # Create cart item
                CartItem.objects.get_or_create(
                    cart=cart,
                    product_id=saved_item.product_id,
                    defaults={
                        'product_name': saved_item.product_name,
                        'product_description': saved_item.product_description,
                        'unit_price': saved_item.unit_price,
                        'product_image': saved_item.product_image,
                        'product_slug': saved_item.product_slug,
                        'vendor': saved_item.vendor,
                        'vendor_name': saved_item.vendor_name,
                        'quantity': 1
                    }
                )
                
                # Delete saved item
                saved_item.delete()
                moved_count += 1
                
            except Exception as e:
                self.message_user(
                    request, 
                    f'Error moving {saved_item.product_name}: {str(e)}',
                    level='ERROR'
                )
        
        if moved_count > 0:
            self.message_user(
                request, 
                f'Successfully moved {moved_count} items to cart.'
            )
    
    move_to_cart.short_description = "Move selected items to cart"

# Add CartItem inline to Cart admin
CartAdmin.inlines = [CartItemInline]