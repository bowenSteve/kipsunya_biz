# orders/views.py
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q, Sum, Count, Avg, F
from django.utils import timezone
from django.http import HttpResponse
from datetime import datetime, timedelta
from decimal import Decimal
import csv
import json

from .models import Order, OrderItem, OrderStatusHistory, OrderRefund
from .serializers import (
    OrderSerializer, OrderCreateSerializer, OrderDetailSerializer,
    OrderItemSerializer, OrderStatusHistorySerializer, OrderRefundSerializer
)
from .permissions import IsCustomerOrVendor, IsVendorOwner
from .utils import calculate_platform_commission, send_order_notification


class OrderPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class OrderListCreateView(generics.ListCreateAPIView):
    """
    List orders for customers/vendors or create new order
    GET: List orders based on user role
    POST: Create new order (customers only)
    """
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = OrderPagination
    
    def get_queryset(self):
        user = self.request.user
        queryset = Order.objects.select_related('customer').prefetch_related(
            'items__vendor', 'status_history', 'refunds'
        )
        # Role-based filtering
        if user.role == 'customer':
            queryset = queryset.filter(customer=user)
        elif user.role == 'vendor':
            # Vendors see orders that contain their products
            queryset = queryset.filter(items__vendor=user).distinct()
        elif user.role == 'admin':
            # Admins see all orders
            pass
        else:
            queryset = queryset.none()
        
        # Apply filters
        status_filter = self.request.query_params.get('status')
        if status_filter and status_filter != 'all':
            queryset = queryset.filter(status=status_filter)
        
        date_filter = self.request.query_params.get('date_filter')
        if date_filter and date_filter != 'all':
            queryset = self._apply_date_filter(queryset, date_filter)
        
        search = self.request.query_params.get('search')
        if search:
            queryset = self._apply_search_filter(queryset, search)
        
        # Custom date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                queryset = queryset.filter(
                    created_at__date__gte=start.date(),
                    created_at__date__lte=end.date()
                )
            except ValueError:
                pass
        
        return queryset.order_by('-created_at')
    
    def _apply_date_filter(self, queryset, date_filter):
        """Apply date-based filtering"""
        now = timezone.now()
        
        if date_filter == 'today':
            return queryset.filter(created_at__date=now.date())
        elif date_filter == 'week':
            week_ago = now - timedelta(days=7)
            return queryset.filter(created_at__gte=week_ago)
        elif date_filter == 'month':
            month_ago = now - timedelta(days=30)
            return queryset.filter(created_at__gte=month_ago)
        elif date_filter == '3months':
            three_months_ago = now - timedelta(days=90)
            return queryset.filter(created_at__gte=three_months_ago)
        elif date_filter == 'year':
            year_ago = now - timedelta(days=365)
            return queryset.filter(created_at__gte=year_ago)
        
        return queryset
    
    def _apply_search_filter(self, queryset, search):
        """Apply search filtering"""
        return queryset.filter(
            Q(order_number__icontains=search) |
            Q(customer__first_name__icontains=search) |
            Q(customer__last_name__icontains=search) |
            Q(customer__email__icontains=search) |
            Q(items__product_name__icontains=search) |
            Q(tracking_number__icontains=search)
        ).distinct()
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return OrderCreateSerializer
        return OrderSerializer
    
    def list(self, request, *args, **kwargs):
        """Override list to include summary data"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            summary_data = self._get_summary_data(queryset, request.user)
            
            response = self.get_paginated_response(serializer.data)
            response.data['summary'] = summary_data
            return response
        
        serializer = self.get_serializer(queryset, many=True)
        summary_data = self._get_summary_data(queryset, request.user)
        
        return Response({
            'orders': serializer.data,
            'summary': summary_data
        })
    
    def _get_summary_data(self, queryset, user):
        """Calculate summary data based on user role"""
        summary = {
            'total_orders': queryset.count(),
            'total_revenue': 0,
            'total_earnings': 0,
            'commission_paid': 0,
            'status_breakdown': {}
        }
        
        if user.role == 'vendor':
            # Vendor-specific calculations
            vendor_items = OrderItem.objects.filter(
                order__in=queryset, vendor=user
            )
            
            aggregates = vendor_items.aggregate(
                total_revenue=Sum('total_price'),
                total_earnings=Sum('vendor_earnings'),
                commission_paid=Sum('platform_commission')
            )
            
            summary.update({
                'total_revenue': float(aggregates['total_revenue'] or 0),
                'total_earnings': float(aggregates['total_earnings'] or 0),
                'commission_paid': float(aggregates['commission_paid'] or 0),
            })
        
        elif user.role in ['customer', 'admin']:
            # Customer or admin calculations
            aggregates = queryset.aggregate(
                total_revenue=Sum('total_amount')
            )
            summary['total_revenue'] = float(aggregates['total_revenue'] or 0)
        
        # Status breakdown for all users
        status_breakdown = queryset.values('status').annotate(
            count=Count('id')
        ).order_by('status')
        
        summary['status_breakdown'] = {
            item['status']: item['count'] for item in status_breakdown
        }
        
        return summary
    
    def perform_create(self, serializer):
        """Create order with proper calculations"""
        if self.request.user.role != 'customer':
            raise PermissionError("Only customers can create orders")
        
        order = serializer.save(customer=self.request.user)
        
        # Send order confirmation email
        try:
            send_order_notification(order, 'created')
        except Exception as e:
            print(f"Failed to send order notification: {e}")


class OrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete order
    GET: View order details
    PUT/PATCH: Update order (limited fields)
    DELETE: Cancel order (if allowed)
    """
    serializer_class = OrderDetailSerializer
    permission_classes = [permissions.IsAuthenticated, IsCustomerOrVendor]
    
    def get_queryset(self):
        user = self.request.user
        queryset = Order.objects.select_related('customer').prefetch_related(
            'items__vendor', 'status_history__changed_by', 'refunds'
        )
        
        if user.role == 'customer':
            return queryset.filter(customer=user)
        elif user.role == 'vendor':
            return queryset.filter(items__vendor=user).distinct()
        elif user.role == 'admin':
            return queryset
        else:
            return queryset.none()
    
    def perform_update(self, serializer):
        """Handle order updates with business logic"""
        order = self.get_object()
        old_status = order.status
        
        # Save the order
        updated_order = serializer.save()
        
        # If status changed, create history entry
        if 'status' in serializer.validated_data and old_status != updated_order.status:
            OrderStatusHistory.objects.create(
                order=updated_order,
                previous_status=old_status,
                new_status=updated_order.status,
                changed_by=self.request.user,
                notes=self.request.data.get('status_notes', '')
            )
            
            # Send status update notification
            try:
                send_order_notification(updated_order, 'status_updated')
            except Exception as e:
                print(f"Failed to send status notification: {e}")
    
    def perform_destroy(self, instance):
        """Cancel order instead of deleting"""
        if instance.status in ['delivered', 'cancelled', 'refunded']:
            raise PermissionError("Cannot cancel this order")
        
        instance.status = 'cancelled'
        instance.save()
        
        # Create status history
        OrderStatusHistory.objects.create(
            order=instance,
            previous_status=instance.status,
            new_status='cancelled',
            changed_by=self.request.user,
            notes='Order cancelled by user'
        )


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def update_order_status(request, order_id):
    """
    Update order status (vendors and admins only)
    PUT /api/orders/{order_id}/status/
    """
    order = get_object_or_404(Order, id=order_id)
    user = request.user
    
    # Permission check
    if user.role == 'vendor':
        if not order.items.filter(vendor=user).exists():
            return Response(
                {'error': 'You do not have permission to update this order'}, 
                status=status.HTTP_403_FORBIDDEN
            )
    elif user.role not in ['admin']:
        return Response(
            {'error': 'Only vendors and admins can update order status'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    new_status = request.data.get('status')
    notes = request.data.get('notes', '')
    tracking_number = request.data.get('tracking_number')
    
    # Validate status
    valid_statuses = [choice[0] for choice in Order.ORDER_STATUS_CHOICES]
    if new_status not in valid_statuses:
        return Response(
            {'error': 'Invalid status', 'valid_statuses': valid_statuses}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Business logic validation
    if not _can_update_status(order.status, new_status):
        return Response(
            {'error': f'Cannot change status from {order.status} to {new_status}'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Create status history
    OrderStatusHistory.objects.create(
        order=order,
        previous_status=order.status,
        new_status=new_status,
        changed_by=user,
        notes=notes
    )
    
    # Update order
    old_status = order.status
    order.status = new_status
    
    # Update timestamps and tracking
    now = timezone.now()
    if new_status == 'confirmed' and old_status != 'confirmed':
        order.confirmed_at = now
    elif new_status == 'shipped' and old_status != 'shipped':
        order.shipped_at = now
        if tracking_number:
            order.tracking_number = tracking_number
    elif new_status == 'delivered' and old_status != 'delivered':
        order.delivered_at = now
    
    order.save()
    
    # Send notification
    try:
        send_order_notification(order, 'status_updated')
    except Exception as e:
        print(f"Failed to send notification: {e}")
    
    serializer = OrderDetailSerializer(order)
    return Response(serializer.data)


def _can_update_status(current_status, new_status):
    """Validate status transition rules"""
    transitions = {
        'pending': ['confirmed', 'cancelled'],
        'confirmed': ['processing', 'cancelled'],
        'processing': ['shipped', 'cancelled'],
        'shipped': ['delivered', 'cancelled'],
        'delivered': ['refunded'],
        'cancelled': [],
        'refunded': []
    }
    
    return new_status in transitions.get(current_status, [])


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def vendor_orders_summary(request):
    """
    Get vendor orders summary and analytics
    GET /api/orders/vendor/summary/
    """
    if request.user.role != 'vendor':
        return Response(
            {'error': 'Only vendors can access this endpoint'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    vendor = request.user
    
    # Get date range
    date_filter = request.query_params.get('date_filter', 'month')
    now = timezone.now()
    
    start_date = _get_start_date(date_filter, now)
    
    # Get vendor orders in date range
    vendor_orders = Order.objects.filter(
        items__vendor=vendor,
        created_at__gte=start_date
    ).distinct()
    
    vendor_items = OrderItem.objects.filter(
        vendor=vendor,
        order__created_at__gte=start_date
    )
    
    # Calculate metrics
    metrics = vendor_items.aggregate(
        total_revenue=Sum('total_price'),
        total_earnings=Sum('vendor_earnings'),
        commission_paid=Sum('platform_commission'),
        total_items_sold=Sum('quantity'),
        avg_order_value=Avg('total_price')
    )
    
    # Status breakdown
    status_breakdown = vendor_orders.values('status').annotate(
        count=Count('id'),
        revenue=Sum('total_amount')
    ).order_by('status')
    
    # Top products
    top_products = vendor_items.values('product_name').annotate(
        quantity_sold=Sum('quantity'),
        revenue=Sum('total_price')
    ).order_by('-quantity_sold')[:5]
    
    # Daily sales (last 30 days)
    daily_sales = vendor_items.filter(
        order__created_at__gte=now - timedelta(days=30)
    ).extra(
        select={'day': 'date(order__created_at)'}
    ).values('day').annotate(
        orders=Count('order', distinct=True),
        revenue=Sum('total_price')
    ).order_by('day')
    
    # Recent orders
    recent_orders = vendor_orders.order_by('-created_at')[:5]
    recent_orders_data = OrderSerializer(recent_orders, many=True).data
    
    return Response({
        'summary': {
            'total_orders': vendor_orders.count(),
            'total_revenue': float(metrics['total_revenue'] or 0),
            'total_earnings': float(metrics['total_earnings'] or 0),
            'commission_paid': float(metrics['commission_paid'] or 0),
            'total_items_sold': int(metrics['total_items_sold'] or 0),
            'avg_order_value': float(metrics['avg_order_value'] or 0),
        },
        'status_breakdown': list(status_breakdown),
        'top_products': list(top_products),
        'daily_sales': list(daily_sales),
        'recent_orders': recent_orders_data,
        'date_range': {
            'start': start_date.isoformat(),
            'end': now.isoformat(),
            'filter': date_filter
        }
    })


def _get_start_date(date_filter, now):
    """Get start date based on filter"""
    if date_filter == 'today':
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif date_filter == 'week':
        return now - timedelta(days=7)
    elif date_filter == 'month':
        return now - timedelta(days=30)
    elif date_filter == '3months':
        return now - timedelta(days=90)
    elif date_filter == 'year':
        return now - timedelta(days=365)
    else:
        return now - timedelta(days=30)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def customer_order_stats(request):
    """
    Get customer order statistics
    GET /api/orders/customer/stats/
    """
    if request.user.role != 'customer':
        return Response(
            {'error': 'Only customers can access this endpoint'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    customer = request.user
    orders = Order.objects.filter(customer=customer)
    
    # Calculate stats
    stats = orders.aggregate(
        total_orders=Count('id'),
        total_spent=Sum('total_amount'),
        avg_order_value=Avg('total_amount')
    )
    
    # Status breakdown
    status_breakdown = orders.values('status').annotate(
        count=Count('id')
    ).order_by('status')
    
    # Monthly spending (last 12 months)
    twelve_months_ago = timezone.now() - timedelta(days=365)
    monthly_spending = orders.filter(
        created_at__gte=twelve_months_ago
    ).extra(
        select={'month': 'strftime("%%Y-%%m", created_at)'}
    ).values('month').annotate(
        total=Sum('total_amount'),
        orders=Count('id')
    ).order_by('month')
    
    # Favorite vendors (by order count)
    favorite_vendors = OrderItem.objects.filter(
        order__customer=customer
    ).values(
        'vendor__first_name', 'vendor__last_name', 'vendor__email'
    ).annotate(
        order_count=Count('order', distinct=True),
        total_spent=Sum('total_price')
    ).order_by('-order_count')[:5]
    
    return Response({
        'stats': {
            'total_orders': stats['total_orders'] or 0,
            'total_spent': float(stats['total_spent'] or 0),
            'avg_order_value': float(stats['avg_order_value'] or 0),
        },
        'status_breakdown': list(status_breakdown),
        'monthly_spending': list(monthly_spending),
        'favorite_vendors': list(favorite_vendors),
    })


class OrderRefundListCreateView(generics.ListCreateAPIView):
    """
    List and create order refunds
    GET: List user's refunds
    POST: Create refund request
    """
    serializer_class = OrderRefundSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        if user.role == 'customer':
            return OrderRefund.objects.filter(requested_by=user)
        elif user.role == 'vendor':
            return OrderRefund.objects.filter(
                order__items__vendor=user
            ).distinct()
        elif user.role == 'admin':
            return OrderRefund.objects.all()
        else:
            return OrderRefund.objects.none()
    
    def perform_create(self, serializer):
        """Create refund request"""
        order_id = self.request.data.get('order')
        order = get_object_or_404(Order, id=order_id)
        
        # Validate customer owns the order
        if order.customer != self.request.user:
            raise PermissionError("You can only request refunds for your own orders")
        
        # Validate order can be refunded
        if order.status not in ['delivered']:
            raise ValueError("Only delivered orders can be refunded")
        
        serializer.save(requested_by=self.request.user)


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def process_refund(request, refund_id):
    """
    Process refund request (admins only)
    PUT /api/orders/refunds/{refund_id}/process/
    """
    if request.user.role != 'admin':
        return Response(
            {'error': 'Only admins can process refunds'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    refund = get_object_or_404(OrderRefund, id=refund_id)
    new_status = request.data.get('status')
    notes = request.data.get('notes', '')
    
    if new_status not in ['approved', 'rejected', 'completed']:
        return Response(
            {'error': 'Invalid status'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    refund.status = new_status
    refund.processed_by = request.user
    refund.processed_at = timezone.now()
    refund.save()
    
    # If approved and order should be marked as refunded
    if new_status == 'completed':
        refund.order.status = 'refunded'
        refund.order.save()
    
    serializer = OrderRefundSerializer(refund)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def export_orders(request):
    """
    Export orders to CSV
    GET /api/orders/export/?format=csv&date_filter=month
    """
    user = request.user
    export_format = request.query_params.get('format', 'csv')
    
    # Get filtered orders using the same logic as OrderListCreateView
    view = OrderListCreateView()
    view.request = request
    queryset = view.get_queryset()
    
    if export_format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="orders_{timezone.now().strftime("%Y%m%d")}.csv"'
        
        writer = csv.writer(response)
        
        # Write headers
        if user.role == 'vendor':
            headers = [
                'Order Number', 'Customer Name', 'Customer Email', 'Status',
                'Total Amount', 'Your Earnings', 'Commission', 'Created At',
                'Items', 'Tracking Number'
            ]
        else:
            headers = [
                'Order Number', 'Status', 'Total Amount', 'Payment Method',
                'Created At', 'Items', 'Tracking Number'
            ]
        
        writer.writerow(headers)
        
        # Write data
        for order in queryset:
            items_list = ', '.join([
                f"{item.product_name} (x{item.quantity})" 
                for item in order.items.all()
            ])
            
            if user.role == 'vendor':
                # Calculate vendor-specific earnings for this order
                vendor_items = order.items.filter(vendor=user)
                earnings = sum(item.vendor_earnings for item in vendor_items)
                commission = sum(item.platform_commission for item in vendor_items)
                
                writer.writerow([
                    order.order_number,
                    order.customer.get_full_name() or order.customer.email,
                    order.customer.email,
                    order.get_status_display(),
                    order.total_amount,
                    earnings,
                    commission,
                    order.created_at.strftime('%Y-%m-%d %H:%M'),
                    items_list,
                    order.tracking_number or ''
                ])
            else:
                writer.writerow([
                    order.order_number,
                    order.get_status_display(),
                    order.total_amount,
                    order.get_payment_method_display(),
                    order.created_at.strftime('%Y-%m-%d %H:%M'),
                    items_list,
                    order.tracking_number or ''
                ])
        
        return response
    
    else:
        return Response({'error': 'Invalid export format'}, status=400)


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def bulk_status_update(request):
    """
    Bulk update order statuses (vendors and admins only)
    PUT /api/orders/bulk/status-update/
    """
    if request.user.role not in ['vendor', 'admin']:
        return Response(
            {'error': 'Only vendors and admins can bulk update orders'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    order_ids = request.data.get('order_ids', [])
    new_status = request.data.get('status')
    notes = request.data.get('notes', '')
    
    if not order_ids or not new_status:
        return Response(
            {'error': 'order_ids and status are required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate status
    valid_statuses = [choice[0] for choice in Order.ORDER_STATUS_CHOICES]
    if new_status not in valid_statuses:
        return Response(
            {'error': 'Invalid status'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get orders the user can modify
    orders = Order.objects.filter(id__in=order_ids)
    
    if request.user.role == 'vendor':
        orders = orders.filter(items__vendor=request.user).distinct()
    
    updated_orders = []
    failed_orders = []
    
    for order in orders:
        try:
            if _can_update_status(order.status, new_status):
                # Create status history
                OrderStatusHistory.objects.create(
                    order=order,
                    previous_status=order.status,
                    new_status=new_status,
                    changed_by=request.user,
                    notes=f"Bulk update: {notes}" if notes else "Bulk status update"
                )
                
                # Update order
                old_status = order.status
                order.status = new_status
                
                # Update timestamps
                now = timezone.now()
                if new_status == 'confirmed' and old_status != 'confirmed':
                    order.confirmed_at = now
                elif new_status == 'shipped' and old_status != 'shipped':
                    order.shipped_at = now
                elif new_status == 'delivered' and old_status != 'delivered':
                    order.delivered_at = now
                
                order.save()
                updated_orders.append(order.order_number)
                
            else:
                failed_orders.append({
                    'order_number': order.order_number,
                    'reason': f'Cannot change from {order.status} to {new_status}'
                })
                
        except Exception as e:
            failed_orders.append({
                'order_number': order.order_number,
                'reason': str(e)
            })
    
    return Response({
        'updated_orders': updated_orders,
        'failed_orders': failed_orders,
        'summary': {
            'total_processed': len(order_ids),
            'successful': len(updated_orders),
            'failed': len(failed_orders)
        }
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def order_tracking(request, order_id):
    """
    Get order tracking information
    GET /api/orders/{order_id}/tracking/
    """
    order = get_object_or_404(Order, id=order_id)
    user = request.user
    
    # Permission check
    if user.role == 'customer' and order.customer != user:
        return Response(
            {'error': 'You can only track your own orders'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    elif user.role == 'vendor' and not order.items.filter(vendor=user).exists():
        return Response(
            {'error': 'You can only track orders containing your products'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get status history
    status_history = OrderStatusHistory.objects.filter(
        order=order
    ).select_related('changed_by').order_by('created_at')
    
    tracking_data = {
        'order_number': order.order_number,
        'current_status': order.status,
        'tracking_number': order.tracking_number,
        'estimated_delivery': None,  # You can implement this based on your logic
        'status_history': [
            {
                'status': history.new_status,
                'timestamp': history.created_at,
                'notes': history.notes,
                'changed_by': history.changed_by.get_full_name() if history.changed_by else None
            }
            for history in status_history
        ],
        'shipping_address': order.shipping_address,
        'carrier_info': {
            'name': 'Default Carrier',  # You can expand this
            'tracking_url': f'https://track.example.com/{order.tracking_number}' if order.tracking_number else None
        }
    }
    
    return Response(tracking_data)


@api_view(['GET'])
def track_by_number(request, tracking_number):
    """
    Track order by tracking number (public endpoint)
    GET /api/orders/tracking/{tracking_number}/
    """
    try:
        order = Order.objects.get(tracking_number=tracking_number)
    except Order.DoesNotExist:
        return Response(
            {'error': 'Invalid tracking number'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Return limited public tracking info
    return Response({
        'order_number': order.order_number,
        'status': order.status,
        'tracking_number': order.tracking_number,
        'last_updated': order.updated_at,
        'estimated_delivery': None,  # Implement based on your logic
    })


class OrderItemListView(generics.ListAPIView):
    """
    List order items
    GET /api/orders/{order_id}/items/
    """
    serializer_class = OrderItemSerializer
    permission_classes = [permissions.IsAuthenticated, IsCustomerOrVendor]
    
    def get_queryset(self):
        order_id = self.kwargs['order_id']
        order = get_object_or_404(Order, id=order_id)
        
        # Check permissions
        user = self.request.user
        if user.role == 'customer' and order.customer != user:
            return OrderItem.objects.none()
        elif user.role == 'vendor':
            # Vendors only see their own items
            return OrderItem.objects.filter(order=order, vendor=user)
        elif user.role == 'admin':
            return OrderItem.objects.filter(order=order)
        
        return OrderItem.objects.none()


class OrderItemDetailView(generics.RetrieveUpdateAPIView):
    """
    Retrieve or update order item
    GET/PUT /api/orders/items/{item_id}/
    """
    serializer_class = OrderItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        queryset = OrderItem.objects.select_related('order', 'vendor')
        
        if user.role == 'customer':
            return queryset.filter(order__customer=user)
        elif user.role == 'vendor':
            return queryset.filter(vendor=user)
        elif user.role == 'admin':
            return queryset
        
        return queryset.none()


@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def order_notes(request, order_id):
    """
    Get or add notes to an order
    GET/POST /api/orders/{order_id}/notes/
    """
    order = get_object_or_404(Order, id=order_id)
    user = request.user
    
    # Permission check
    if user.role == 'customer' and order.customer != user:
        return Response(
            {'error': 'You can only access your own orders'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    elif user.role == 'vendor' and not order.items.filter(vendor=user).exists():
        return Response(
            {'error': 'You can only access orders containing your products'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    if request.method == 'GET':
        # Return existing notes
        notes = []
        if order.notes:
            notes.append({
                'type': 'order_note',
                'content': order.notes,
                'created_at': order.created_at,
                'created_by': 'System'
            })
        
        if order.special_instructions:
            notes.append({
                'type': 'special_instructions',
                'content': order.special_instructions,
                'created_at': order.created_at,
                'created_by': order.customer.get_full_name() or order.customer.email
            })
        
        # Add status history as notes
        status_history = OrderStatusHistory.objects.filter(
            order=order, notes__isnull=False
        ).exclude(notes='').select_related('changed_by')
        
        for history in status_history:
            notes.append({
                'type': 'status_note',
                'content': history.notes,
                'status': history.new_status,
                'created_at': history.created_at,
                'created_by': history.changed_by.get_full_name() if history.changed_by else 'System'
            })
        
        # Sort by creation date
        notes.sort(key=lambda x: x['created_at'])
        
        return Response({'notes': notes})
    
    elif request.method == 'POST':
        # Add new note via status history
        note_content = request.data.get('content')
        if not note_content:
            return Response(
                {'error': 'Note content is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create status history entry with note
        OrderStatusHistory.objects.create(
            order=order,
            previous_status=order.status,
            new_status=order.status,  # Same status, just adding note
            changed_by=user,
            notes=note_content
        )
        
        return Response({'message': 'Note added successfully'})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def order_analytics(request):
    """
    Get detailed analytics for orders
    GET /api/orders/analytics/?period=month&type=sales
    """
    user = request.user
    period = request.query_params.get('period', 'month')  # day, week, month, year
    analytics_type = request.query_params.get('type', 'sales')  # sales, customers, products
    
    now = timezone.now()
    start_date = _get_start_date(period, now)
    
    if user.role == 'vendor':
        orders = Order.objects.filter(
            items__vendor=user,
            created_at__gte=start_date
        ).distinct()
        items = OrderItem.objects.filter(
            vendor=user,
            order__created_at__gte=start_date
        )
    elif user.role == 'admin':
        orders = Order.objects.filter(created_at__gte=start_date)
        items = OrderItem.objects.filter(order__created_at__gte=start_date)
    else:
        orders = Order.objects.filter(
            customer=user,
            created_at__gte=start_date
        )
        items = OrderItem.objects.filter(
            order__customer=user,
            order__created_at__gte=start_date
        )
    
    analytics_data = {}
    
    if analytics_type == 'sales':
        # Sales analytics
        analytics_data = {
            'revenue_trend': _get_revenue_trend(orders, period),
            'status_distribution': _get_status_distribution(orders),
            'payment_methods': _get_payment_methods(orders),
            'avg_order_value': orders.aggregate(avg=Avg('total_amount'))['avg'] or 0,
            'conversion_rate': _get_conversion_rate(orders, period),
        }
    
    elif analytics_type == 'customers' and user.role in ['vendor', 'admin']:
        # Customer analytics
        analytics_data = {
            'new_customers': _get_new_customers(orders, period),
            'customer_segments': _get_customer_segments(orders),
            'repeat_customers': _get_repeat_customers(orders),
            'customer_lifetime_value': _get_customer_lifetime_value(orders),
        }
    
    elif analytics_type == 'products':
        # Product analytics
        analytics_data = {
            'top_products': _get_top_products(items),
            'product_performance': _get_product_performance(items, period),
            'category_sales': _get_category_sales(items),
            'inventory_turnover': _get_inventory_turnover(items),
        }
    
    return Response(analytics_data)


def _get_revenue_trend(orders, period):
    """Get revenue trend data"""
    if period == 'day':
        date_format = '%Y-%m-%d %H:00'
        truncate = 'hour'
    elif period == 'week':
        date_format = '%Y-%m-%d'
        truncate = 'day'
    elif period == 'month':
        date_format = '%Y-%m-%d'
        truncate = 'day'
    else:  # year
        date_format = '%Y-%m'
        truncate = 'month'
    
    trend_data = orders.extra(
        select={'period': f'strftime("{date_format}", created_at)'}
    ).values('period').annotate(
        revenue=Sum('total_amount'),
        orders=Count('id'),
        avg_order_value=Avg('total_amount')
    ).order_by('period')
    
    return list(trend_data)


def _get_status_distribution(orders):
    """Get order status distribution"""
    total_orders = orders.count()
    if total_orders == 0:
        return []
    
    return list(orders.values('status').annotate(
        count=Count('id'),
        percentage=Count('id') * 100.0 / total_orders,
        revenue=Sum('total_amount')
    ).order_by('status'))


def _get_payment_methods(orders):
    """Get payment method distribution"""
    return list(orders.values('payment_method').annotate(
        count=Count('id'),
        total_amount=Sum('total_amount'),
        avg_amount=Avg('total_amount')
    ).order_by('-count'))


def _get_conversion_rate(orders, period):
    """Calculate conversion rate (simplified)"""
    # This would typically involve tracking website visitors
    # For now, return a placeholder
    return {
        'rate': 2.5,  # 2.5% conversion rate
        'total_visitors': orders.count() * 40,  # Estimated
        'total_orders': orders.count()
    }


def _get_new_customers(orders, period):
    """Get new customer acquisition data"""
    # Get customers who made their first order in this period
    new_customer_orders = orders.filter(
        customer__orders__created_at__lte=F('created_at')
    ).values('customer').annotate(
        first_order=Count('customer')
    ).filter(first_order=1)
    
    return {
        'count': new_customer_orders.count(),
        'revenue': orders.filter(
            customer__in=[item['customer'] for item in new_customer_orders]
        ).aggregate(total=Sum('total_amount'))['total'] or 0
    }


def _get_customer_segments(orders):
    """Get customer segmentation data"""
    # Segment customers by order value
    segments = orders.values('customer').annotate(
        total_spent=Sum('total_amount'),
        order_count=Count('id')
    ).aggregate(
        high_value=Count('customer', filter=Q(total_spent__gte=10000)),
        medium_value=Count('customer', filter=Q(total_spent__gte=5000, total_spent__lt=10000)),
        low_value=Count('customer', filter=Q(total_spent__lt=5000))
    )
    
    return segments


def _get_repeat_customers(orders):
    """Get repeat customer data"""
    repeat_customers = orders.values('customer').annotate(
        order_count=Count('id')
    ).filter(order_count__gt=1)
    
    return {
        'count': repeat_customers.count(),
        'percentage': (repeat_customers.count() / orders.values('customer').distinct().count() * 100) if orders.exists() else 0,
        'avg_orders': repeat_customers.aggregate(avg=Avg('order_count'))['avg'] or 0
    }


def _get_customer_lifetime_value(orders):
    """Calculate customer lifetime value"""
    customer_values = orders.values('customer').annotate(
        lifetime_value=Sum('total_amount'),
        order_count=Count('id'),
        avg_order_value=Avg('total_amount')
    ).aggregate(
        avg_clv=Avg('lifetime_value'),
        max_clv=models.Max('lifetime_value'),
        min_clv=models.Min('lifetime_value')
    )
    
    return customer_values


def _get_top_products(items):
    """Get top selling products"""
    return list(items.values('product_name').annotate(
        quantity_sold=Sum('quantity'),
        revenue=Sum('total_price'),
        orders=Count('order', distinct=True),
        avg_price=Avg('unit_price')
    ).order_by('-quantity_sold')[:10])


def _get_product_performance(items, period):
    """Get product performance over time"""
    if period == 'day':
        date_format = '%Y-%m-%d'
    elif period == 'week':
        date_format = '%Y-W%W'
    elif period == 'month':
        date_format = '%Y-%m'
    else:  # year
        date_format = '%Y'
    
    performance = items.extra(
        select={'period': f'strftime("{date_format}", order__created_at)'}
    ).values('period', 'product_name').annotate(
        quantity=Sum('quantity'),
        revenue=Sum('total_price')
    ).order_by('period', '-revenue')[:50]  # Top 50 products per period
    
    return list(performance)


def _get_category_sales(items):
    """Get sales by product category"""
    # This would require a category field in your product model
    # For now, return a placeholder
    return [
        {'category': 'Kitchen Ware', 'revenue': 50000, 'quantity': 150},
        {'category': 'Electronics', 'revenue': 75000, 'quantity': 100},
        {'category': 'Tools', 'revenue': 30000, 'quantity': 80},
    ]


def _get_inventory_turnover(items):
    """Calculate inventory turnover metrics"""
    # This would require inventory data
    # Return simplified metrics
    return {
        'total_items_sold': items.aggregate(total=Sum('quantity'))['total'] or 0,
        'unique_products': items.values('product_name').distinct().count(),
        'avg_quantity_per_product': items.values('product_name').annotate(
            total_qty=Sum('quantity')
        ).aggregate(avg=Avg('total_qty'))['avg'] or 0
    }

