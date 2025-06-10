from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    # Main products endpoints
    path('all_products/', views.AllProductsView.as_view(), name='all_products'),
    path('all_products_simple/', views.all_products_simple, name='all_products_simple'),
    
    # Additional useful endpoints
    path('featured/', views.featured_products, name='featured_products'),
    path('categories/', views.categories, name='categories'),
    path('product/<slug:slug>/', views.product_by_slug, name='product_detail'),
]