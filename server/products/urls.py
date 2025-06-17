# products/urls.py - Complete CRUD URLs
from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    # READ-ONLY endpoints (public access)
    path('all_products/', views.AllProductsView.as_view(), name='all_products'),
    path('all_products_simple/', views.all_products_simple, name='all_products_simple'),
    path('featured/', views.featured_products, name='featured_products'),
    
    # Product detail endpoints (public read)
    path('products/<int:id>/', views.product_by_id, name='product_detail_by_id'),
    path('product/<slug:slug>/', views.product_by_slug, name='product_detail_by_slug'),
    
    # CRUD endpoints for products
    path('products/', views.ProductListCreateView.as_view(), name='product-list-create'),
    path('products/<int:id>/edit/', views.ProductDetailView.as_view(), name='product-detail'),
    
    # Function-based CRUD endpoints (alternative)
    path('vendor/products/', views.vendor_products, name='vendor-products'),
    path('products/create/', views.create_product, name='create-product'),
    path('products/<int:product_id>/update/', views.update_product, name='update-product'),
    path('products/<int:product_id>/delete/', views.delete_product, name='delete-product'),
    
    # Category endpoints
    path('categories/', views.CategoryListCreateView.as_view(), name='category-list-create'),
    path('categories/<int:id>/', views.CategoryDetailView.as_view(), name='category-detail'),
    
    # Legacy category endpoint (keeping for backward compatibility)
    path('categories/list/', views.categories, name='categories-list'),
]