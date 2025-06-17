# cart/urls.py
from django.urls import path
from . import views

app_name = 'cart'

urlpatterns = [
    # Cart management
    path('', views.get_cart, name='get_cart'),
    path('summary/', views.cart_summary, name='cart_summary'),
    path('add/', views.add_to_cart, name='add_to_cart'),
    path('quick-add/', views.quick_add_to_cart, name='quick_add_to_cart'),
    path('clear/', views.clear_cart, name='clear_cart'),
    path('validate/', views.validate_cart, name='validate_cart'),
    path('merge/', views.merge_carts, name='merge_carts'),
    path('health/', views.cart_health_check, name='cart_health_check'),
    
    # Cart item management
    path('items/<uuid:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('items/<uuid:item_id>/detail/', views.cart_item_detail, name='cart_item_detail'),
    path('items/<uuid:item_id>/remove/', views.remove_cart_item, name='remove_cart_item'),
    path('items/<uuid:item_id>/save/', views.save_for_later, name='save_for_later'),
    
    # Saved items management
    path('saved/', views.get_saved_items, name='get_saved_items'),
    path('saved/<uuid:saved_item_id>/move/', views.move_to_cart, name='move_to_cart'),
    path('saved/<uuid:saved_item_id>/remove/', views.remove_saved_item, name='remove_saved_item'),
    path('save-all/', views.save_cart_for_later, name='save_cart_for_later'),
    
    # Bulk operations
    path('bulk/', views.bulk_cart_actions, name='bulk_cart_actions'),
    
    # Checkout and ordering
    path('checkout/', views.convert_cart_to_order, name='convert_cart_to_order'),
    path('estimate/', views.estimate_cart_total, name='estimate_cart_total'),
    path('shipping/', views.cart_shipping_options, name='cart_shipping_options'),
    
    # Discounts and promotions
    path('discount/', views.apply_cart_discount, name='apply_cart_discount'),
    
    # Analytics and recommendations
    path('analytics/', views.cart_analytics, name='cart_analytics'),
    path('recommendations/', views.cart_recommendations, name='cart_recommendations'),
]