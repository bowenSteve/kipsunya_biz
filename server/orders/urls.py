# orders/urls.py
from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # Order CRUD operations
    path('', views.OrderListCreateView.as_view(), name='order-list-create'),
    path('<uuid:pk>/', views.OrderDetailView.as_view(), name='order-detail'),
    
    # Order status management
    path('<uuid:order_id>/status/', views.update_order_status, name='update-order-status'),
    
    # Vendor-specific endpoints
    path('vendor/summary/', views.vendor_orders_summary, name='vendor-summary'),
    
    # Customer-specific endpoints
    path('customer/stats/', views.customer_order_stats, name='customer-stats'),
    
    # Refund management
    path('refunds/', views.OrderRefundListCreateView.as_view(), name='refund-list-create'),
    path('refunds/<uuid:refund_id>/process/', views.process_refund, name='process-refund'),
    
    # Export and analytics
    path('export/', views.export_orders, name='export-orders'),
    path('analytics/', views.order_analytics, name='order-analytics'),
    
    # Bulk operations
    path('bulk/status-update/', views.bulk_status_update, name='bulk-status-update'),
    
    # Order tracking
    path('<uuid:order_id>/tracking/', views.order_tracking, name='order-tracking'),
    path('tracking/<str:tracking_number>/', views.track_by_number, name='track-by-number'),
    
    # Order items management
    path('<uuid:order_id>/items/', views.OrderItemListView.as_view(), name='order-items'),
    path('items/<uuid:item_id>/', views.OrderItemDetailView.as_view(), name='order-item-detail'),
    
    # Order notes and communication
    path('<uuid:order_id>/notes/', views.order_notes, name='order-notes'),
]