# cart/views.py
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Sum, Count
from django.contrib.auth.models import User
from decimal import Decimal
import uuid
from django.utils import timezone

from .models import Cart, CartItem, SavedItem
from products.models import Product
from orders.models import Order, OrderItem
from .serializers import (
    CartSerializer, CartItemSerializer, CartItemCreateSerializer,
    CartSummarySerializer, SavedItemSerializer, SavedItemCreateSerializer,
    CartQuantityUpdateSerializer, CartToOrderSerializer, BulkCartActionSerializer
)

def get_or_create_cart(request):
    """Get or create cart for user (authenticated or anonymous)"""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        return cart
    else:
        # Handle anonymous users with session
        session_id = request.session.session_key
        if not session_id:
            request.session.create()
            session_id = request.session.session_key
        
        cart, created = Cart.objects.get_or_create(session_id=session_id)
        return cart

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_cart(request):
    """
    Get user's cart with all items
    GET /api/cart/
    """
    cart = get_or_create_cart(request)
    serializer = CartSerializer(cart)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def cart_summary(request):
    """
    Get cart summary (lightweight)
    GET /api/cart/summary/
    """
    cart = get_or_create_cart(request)
    serializer = CartSummarySerializer(cart)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def add_to_cart(request):
    """
    Add item to cart or update quantity if exists
    POST /api/cart/add/
    Body: {"product_id": 1, "quantity": 2}
    """
    serializer = CartItemCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    product_id = serializer.validated_data['product_id']
    quantity = serializer.validated_data['quantity']
    
    try:
        # Get product details
        product = Product.objects.select_related('category').get(
            id=product_id, is_active=True
        )
        
        if not product.is_available:
            return Response(
                {'error': 'Product is not available'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check stock
        if quantity > product.stock_quantity:
            return Response(
                {'error': f'Only {product.stock_quantity} items available in stock'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cart = get_or_create_cart(request)
        
        # Check if item already exists in cart
        try:
            cart_item = CartItem.objects.get(cart=cart, product_id=product_id)
            # Update quantity
            new_quantity = cart_item.quantity + quantity
            
            # Check total quantity against stock
            if new_quantity > product.stock_quantity:
                return Response(
                    {'error': f'Cannot add {quantity} more. Only {product.stock_quantity - cart_item.quantity} more available'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            cart_item.quantity = new_quantity
            cart_item.save()
            
            message = f'Updated quantity to {new_quantity}'
            
        except CartItem.DoesNotExist:
            # Create new cart item
            # For vendor, we'll assume products have a vendor field or use a default
            # Since your current Product model doesn't have vendor, we'll use the first admin user
            # You should modify this based on your actual product-vendor relationship
            vendor = User.objects.filter(is_superuser=True).first()
            if not vendor:
                vendor = User.objects.first()
            
            cart_item = CartItem.objects.create(
                cart=cart,
                product_id=product.id,
                product_name=product.name,
                product_description=product.description,
                unit_price=product.price,
                product_image=product.image_url,
                product_slug=product.slug,
                vendor=vendor,
                vendor_name=vendor.get_full_name() or vendor.email,
                quantity=quantity
            )
            
            message = f'Added {quantity} item(s) to cart'
        
        # Return updated cart item
        item_serializer = CartItemSerializer(cart_item)
        
        return Response({
            'message': message,
            'cart_item': item_serializer.data,
            'cart_summary': CartSummarySerializer(cart).data
        }, status=status.HTTP_200_OK)
        
    except Product.DoesNotExist:
        return Response(
            {'error': 'Product not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': 'Failed to add item to cart'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['PUT'])
@permission_classes([permissions.AllowAny])
def update_cart_item(request, item_id):
    """
    Update cart item quantity
    PUT /api/cart/items/{item_id}/
    Body: {"quantity": 3}
    """
    cart = get_or_create_cart(request)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
    
    serializer = CartQuantityUpdateSerializer(
        data=request.data, 
        context={'cart_item': cart_item}
    )
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    new_quantity = serializer.validated_data['quantity']
    old_quantity = cart_item.quantity
    
    cart_item.quantity = new_quantity
    cart_item.save()
    
    item_serializer = CartItemSerializer(cart_item)
    
    return Response({
        'message': f'Updated quantity from {old_quantity} to {new_quantity}',
        'cart_item': item_serializer.data,
        'cart_summary': CartSummarySerializer(cart).data
    })

@api_view(['DELETE'])
@permission_classes([permissions.AllowAny])
def remove_cart_item(request, item_id):
    """
    Remove item from cart
    DELETE /api/cart/items/{item_id}/
    """
    cart = get_or_create_cart(request)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
    
    product_name = cart_item.product_name
    cart_item.delete()
    
    return Response({
        'message': f'Removed {product_name} from cart',
        'cart_summary': CartSummarySerializer(cart).data
    })

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def clear_cart(request):
    """
    Clear all items from cart
    POST /api/cart/clear/
    """
    cart = get_or_create_cart(request)
    items_count = cart.items.count()
    cart.clear()
    
    return Response({
        'message': f'Removed {items_count} items from cart',
        'cart_summary': CartSummarySerializer(cart).data
    })

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def save_for_later(request, item_id):
    """
    Move cart item to saved items
    POST /api/cart/items/{item_id}/save/
    """
    cart = get_or_create_cart(request)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
    
    # Create or update saved item
    saved_item, created = SavedItem.objects.get_or_create(
        user=request.user,
        product_id=cart_item.product_id,
        defaults={
            'product_name': cart_item.product_name,
            'product_description': cart_item.product_description,
            'unit_price': cart_item.unit_price,
            'product_image': cart_item.product_image,
            'product_slug': cart_item.product_slug,
            'vendor': cart_item.vendor,
            'vendor_name': cart_item.vendor_name,
        }
    )
    
    # Remove from cart
    product_name = cart_item.product_name
    cart_item.delete()
    
    return Response({
        'message': f'Saved {product_name} for later',
        'saved_item': SavedItemSerializer(saved_item).data,
        'cart_summary': CartSummarySerializer(cart).data
    })

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_saved_items(request):
    """
    Get user's saved items
    GET /api/cart/saved/
    """
    saved_items = SavedItem.objects.filter(user=request.user)
    serializer = SavedItemSerializer(saved_items, many=True)
    
    return Response({
        'saved_items': serializer.data,
        'count': saved_items.count()
    })

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def move_to_cart(request, saved_item_id):
    """
    Move saved item to cart
    POST /api/cart/saved/{saved_item_id}/move/
    Body: {"quantity": 1} (optional, defaults to 1)
    """
    saved_item = get_object_or_404(SavedItem, id=saved_item_id, user=request.user)
    quantity = request.data.get('quantity', 1)
    
    # Validate quantity
    if quantity <= 0:
        return Response(
            {'error': 'Quantity must be greater than 0'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Check if product still exists and is available
        product = Product.objects.get(id=saved_item.product_id, is_active=True)
        
        if not product.is_available or quantity > product.stock_quantity:
            return Response(
                {'error': 'Product is no longer available or insufficient stock'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cart = get_or_create_cart(request)
        
        # Check if item already exists in cart
        try:
            cart_item = CartItem.objects.get(cart=cart, product_id=saved_item.product_id)
            # Update quantity
            new_quantity = cart_item.quantity + quantity
            
            if new_quantity > product.stock_quantity:
                return Response(
                    {'error': f'Cannot add {quantity} more. Only {product.stock_quantity - cart_item.quantity} more available'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            cart_item.quantity = new_quantity
            cart_item.save()
            
        except CartItem.DoesNotExist:
            # Create new cart item
            cart_item = CartItem.objects.create(
                cart=cart,
                product_id=saved_item.product_id,
                product_name=saved_item.product_name,
                product_description=saved_item.product_description,
                unit_price=product.price,  # Use current price
                product_image=saved_item.product_image,
                product_slug=saved_item.product_slug,
                vendor=saved_item.vendor,
                vendor_name=saved_item.vendor_name,
                quantity=quantity
            )
        
        # Remove from saved items
        product_name = saved_item.product_name
        saved_item.delete()
        
        return Response({
            'message': f'Moved {product_name} to cart',
            'cart_item': CartItemSerializer(cart_item).data,
            'cart_summary': CartSummarySerializer(cart).data
        })
        
    except Product.DoesNotExist:
        return Response(
            {'error': 'Product no longer exists'}, 
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def remove_saved_item(request, saved_item_id):
    """
    Remove saved item
    DELETE /api/cart/saved/{saved_item_id}/
    """
    saved_item = get_object_or_404(SavedItem, id=saved_item_id, user=request.user)
    product_name = saved_item.product_name
    saved_item.delete()
    
    return Response({
        'message': f'Removed {product_name} from saved items'
    })

# Final fix for cart/views.py - Replace convert_cart_to_order function

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def convert_cart_to_order(request):
    """
    Convert cart to order - Final fix with proper Decimal handling
    POST /api/cart/checkout/
    """
    try:
        cart = get_or_create_cart(request)
        
        if not cart.items.exists():
            return Response(
                {'error': 'Cart is empty'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get request data with defaults
        payment_method = request.data.get('payment_method', 'mpesa')
        shipping_address = request.data.get('shipping_address', 'Default Address')
        shipping_city = request.data.get('shipping_city', 'Nairobi')
        shipping_country = request.data.get('shipping_country', 'Kenya')
        shipping_phone = request.data.get('shipping_phone', '+254700000000')
        notes = request.data.get('notes', '')
        special_instructions = request.data.get('special_instructions', '')
        
        # Validate required fields
        if not shipping_address or shipping_address == 'Default Address':
            return Response(
                {'error': 'Shipping address is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not shipping_phone:
            return Response(
                {'error': 'Shipping phone is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                # Calculate totals - FIXED: Ensure all values are Decimal
                subtotal = Decimal('0.00')
                
                # Calculate subtotal from cart items
                for cart_item in cart.items.all():
                    item_total = Decimal(str(cart_item.unit_price)) * cart_item.quantity
                    subtotal += item_total
                
                # All calculations using Decimal
                tax_rate = Decimal('0.16')  # 16% VAT
                tax_amount = subtotal * tax_rate
                shipping_fee = Decimal('0.00')  # Free shipping
                discount_amount = Decimal('0.00')
                total_amount = subtotal + tax_amount + shipping_fee - discount_amount
                
                print(f"Order totals - Subtotal: {subtotal}, Tax: {tax_amount}, Total: {total_amount}")
                
                # Create order
                order = Order.objects.create(
                    customer=request.user,
                    payment_method=payment_method,
                    shipping_address=shipping_address,
                    shipping_city=shipping_city,
                    shipping_country=shipping_country,
                    shipping_phone=shipping_phone,
                    notes=notes,
                    special_instructions=special_instructions,
                    subtotal=subtotal,
                    tax_amount=tax_amount,
                    shipping_fee=shipping_fee,
                    discount_amount=discount_amount,
                    total_amount=total_amount
                )
                
                print(f"Order created with ID: {order.id}")
                
                # Create order items from cart items - FIXED: Proper Decimal handling
                for cart_item in cart.items.all():
                    # Ensure all numeric values are Decimal
                    unit_price = Decimal(str(cart_item.unit_price))
                    commission_rate = Decimal('15.00')  # Default commission rate
                    
                    # Calculate totals for this item
                    item_total_price = unit_price * cart_item.quantity
                    item_commission = (item_total_price * commission_rate) / Decimal('100')
                    item_vendor_earnings = item_total_price - item_commission
                    
                    # Create order item with pre-calculated values
                    order_item = OrderItem(
                        order=order,
                        vendor=cart_item.vendor,
                        product_name=cart_item.product_name,
                        product_description=cart_item.product_description or '',
                        unit_price=unit_price,
                        quantity=cart_item.quantity,
                        total_price=item_total_price,
                        commission_rate=commission_rate,
                        platform_commission=item_commission,
                        vendor_earnings=item_vendor_earnings,
                        product_image=cart_item.product_image,
                        product_sku=cart_item.product_slug,
                    )
                    
                    # Save without triggering save method calculations (since we pre-calculated)
                    order_item.save()
                    
                    print(f"Created order item: {order_item.product_name} x {order_item.quantity}")
                    
                    # Update product stock
                    try:
                        product = Product.objects.get(id=cart_item.product_id)
                        product.stock_quantity = max(0, product.stock_quantity - cart_item.quantity)
                        if product.stock_quantity <= 0:
                            product.in_stock = False
                        product.save()
                        print(f"Updated product {product.id} stock to {product.stock_quantity}")
                    except Product.DoesNotExist:
                        print(f"Product {cart_item.product_id} not found for stock update")
                        pass  # Product might have been deleted
                
                # Clear cart after successful order creation
                cart.clear()
                print("Cart cleared successfully")
                
                return Response({
                    'message': 'Order created successfully',
                    'order': {
                        'id': str(order.id),
                        'order_number': order.order_number,
                        'total_amount': float(order.total_amount),
                        'status': order.status,
                        'created_at': order.created_at.isoformat(),
                        'items_count': order.items.count()
                    }
                }, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            print(f"Error creating order: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': f'Failed to create order: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    except Exception as e:
        print(f"Error in checkout: {str(e)}")
        return Response(
            {'error': f'Checkout failed: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def bulk_cart_actions(request):
    """
    Perform bulk actions on cart items
    POST /api/cart/bulk/
    Body: {"action": "remove", "item_ids": ["uuid1", "uuid2"]}
    """
    serializer = BulkCartActionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    action = serializer.validated_data['action']
    item_ids = serializer.validated_data['item_ids']
    cart = get_or_create_cart(request)
    
    # Get cart items
    cart_items = CartItem.objects.filter(id__in=item_ids, cart=cart)
    
    if not cart_items.exists():
        return Response(
            {'error': 'No valid cart items found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    results = {'successful': [], 'failed': []}
    
    if action == 'remove':
        # Remove items from cart
        for item in cart_items:
            try:
                item_name = item.product_name
                item.delete()
                results['successful'].append({
                    'id': str(item.id),
                    'name': item_name,
                    'action': 'removed'
                })
            except Exception as e:
                results['failed'].append({
                    'id': str(item.id),
                    'error': str(e)
                })
    
    elif action == 'save_for_later':
        # Move items to saved items (authenticated users only)
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required for saving items'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        for item in cart_items:
            try:
                # Create or update saved item
                saved_item, created = SavedItem.objects.get_or_create(
                    user=request.user,
                    product_id=item.product_id,
                    defaults={
                        'product_name': item.product_name,
                        'product_description': item.product_description,
                        'unit_price': item.unit_price,
                        'product_image': item.product_image,
                        'product_slug': item.product_slug,
                        'vendor': item.vendor,
                        'vendor_name': item.vendor_name,
                    }
                )
                
                item_name = item.product_name
                item.delete()
                
                results['successful'].append({
                    'id': str(item.id),
                    'name': item_name,
                    'action': 'saved_for_later'
                })
            except Exception as e:
                results['failed'].append({
                    'id': str(item.id),
                    'error': str(e)
                })
    
    return Response({
        'message': f'Bulk {action} completed',
        'results': results,
        'cart_summary': CartSummarySerializer(cart).data
    })

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def cart_analytics(request):
    """
    Get cart analytics for the user
    GET /api/cart/analytics/
    """
    cart = get_or_create_cart(request)
    
    # Basic cart metrics
    cart_items = cart.items.all()
    
    analytics = {
        'cart_summary': {
            'total_items': cart.total_items,
            'unique_products': cart_items.count(),
            'subtotal': float(cart.subtotal),
            'total_amount': float(cart.total_amount),
        },
        'items_by_vendor': {},
        'price_breakdown': {
            'subtotal': float(cart.subtotal),
            'tax_amount': float(cart.subtotal * Decimal('0.16')),
            'shipping_fee': 0.00,
            'total': float(cart.total_amount),
        },
        'stock_warnings': []
    }
    
    # Group items by vendor
    for item in cart_items:
        vendor_name = item.vendor_name
        if vendor_name not in analytics['items_by_vendor']:
            analytics['items_by_vendor'][vendor_name] = {
                'items': 0,
                'total_value': 0.00
            }
        
        analytics['items_by_vendor'][vendor_name]['items'] += item.quantity
        analytics['items_by_vendor'][vendor_name]['total_value'] += float(item.total_price)
    
    # Check for stock warnings
    for item in cart_items:
        try:
            product = Product.objects.get(id=item.product_id)
            if item.quantity > product.stock_quantity:
                analytics['stock_warnings'].append({
                    'product_name': item.product_name,
                    'requested_quantity': item.quantity,
                    'available_quantity': product.stock_quantity,
                    'message': f'Only {product.stock_quantity} available for {item.product_name}'
                })
        except Product.DoesNotExist:
            analytics['stock_warnings'].append({
                'product_name': item.product_name,
                'message': f'{item.product_name} is no longer available'
            })
    
    return Response(analytics)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def merge_carts(request):
    """
    Merge anonymous cart with user cart on login
    POST /api/cart/merge/
    """
    if not request.user.is_authenticated:
        return Response(
            {'error': 'Authentication required'}, 
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    session_id = request.session.session_key
    if not session_id:
        return Response({'message': 'No anonymous cart to merge'})
    
    try:
        # Get anonymous cart
        anonymous_cart = Cart.objects.get(session_id=session_id, user=None)
    except Cart.DoesNotExist:
        return Response({'message': 'No anonymous cart found'})
    
    # Get or create user cart
    user_cart, created = Cart.objects.get_or_create(user=request.user)
    
    merged_items = 0
    skipped_items = []
    
    with transaction.atomic():
        for anon_item in anonymous_cart.items.all():
            try:
                # Check if item already exists in user cart
                user_item = CartItem.objects.get(
                    cart=user_cart, 
                    product_id=anon_item.product_id
                )
                # Merge quantities
                user_item.quantity += anon_item.quantity
                user_item.save()
                merged_items += 1
                
            except CartItem.DoesNotExist:
                # Move item to user cart
                anon_item.cart = user_cart
                anon_item.save()
                merged_items += 1
            
            except Exception as e:
                skipped_items.append({
                    'product_name': anon_item.product_name,
                    'error': str(e)
                })
        
        # Delete anonymous cart
        anonymous_cart.delete()
    
    return Response({
        'message': f'Successfully merged {merged_items} items',
        'merged_items': merged_items,
        'skipped_items': skipped_items,
        'cart_summary': CartSummarySerializer(user_cart).data
    })

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def validate_cart(request):
    """
    Validate cart items against current product availability and prices
    POST /api/cart/validate/
    """
    cart = get_or_create_cart(request)
    cart_items = cart.items.all()
    
    validation_results = {
        'valid': True,
        'issues': [],
        'updated_items': [],
        'removed_items': []
    }
    
    for item in cart_items:
        try:
            product = Product.objects.get(id=item.product_id)
            
            # Check if product is still active and available
            if not product.is_active or not product.is_available:
                validation_results['issues'].append({
                    'type': 'unavailable',
                    'product_name': item.product_name,
                    'message': f'{item.product_name} is no longer available'
                })
                validation_results['valid'] = False
                continue
            
            # Check stock quantity
            if item.quantity > product.stock_quantity:
                if product.stock_quantity > 0:
                    # Adjust quantity to available stock
                    item.quantity = product.stock_quantity
                    item.save()
                    
                    validation_results['updated_items'].append({
                        'product_name': item.product_name,
                        'new_quantity': product.stock_quantity,
                        'message': f'Quantity adjusted to {product.stock_quantity} (available stock)'
                    })
                    validation_results['valid'] = False
                else:
                    # Remove item - no stock available
                    validation_results['removed_items'].append({
                        'product_name': item.product_name,
                        'message': f'{item.product_name} is out of stock'
                    })
                    item.delete()
                    validation_results['valid'] = False
                    continue
            
            # Check if price has changed
            if item.unit_price != product.price:
                old_price = item.unit_price
                item.unit_price = product.price
                item.save()
                
                validation_results['updated_items'].append({
                    'product_name': item.product_name,
                    'price_change': {
                        'old_price': float(old_price),
                        'new_price': float(product.price)
                    },
                    'message': f'Price updated from {old_price} to {product.price}'
                })
                validation_results['valid'] = False
                
        except Product.DoesNotExist:
            # Product no longer exists
            validation_results['removed_items'].append({
                'product_name': item.product_name,
                'message': f'{item.product_name} no longer exists'
            })
            item.delete()
            validation_results['valid'] = False
    
    return Response({
        'validation': validation_results,
        'cart_summary': CartSummarySerializer(cart).data
    })

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def cart_recommendations(request):
    """
    Get product recommendations based on cart contents
    GET /api/cart/recommendations/
    """
    cart = get_or_create_cart(request)
    
    if not cart.items.exists():
        return Response({
            'recommendations': [],
            'message': 'Add items to cart to see recommendations'
        })
    
    # Get categories of items in cart
    cart_product_ids = [item.product_id for item in cart.items.all()]
    
    try:
        cart_products = Product.objects.filter(id__in=cart_product_ids)
        cart_categories = list(cart_products.values_list('category', flat=True).distinct())
        
        # Get recommended products from same categories (excluding cart items)
        recommendations = Product.objects.filter(
            category__in=cart_categories,
            is_active=True,
            is_available=True
        ).exclude(
            id__in=cart_product_ids
        ).order_by('-featured', '?')[:8]  # Random selection, featured first
        
        from products.serializers import ProductSerializer
        recommendations_data = ProductSerializer(recommendations, many=True).data
        
        return Response({
            'recommendations': recommendations_data,
            'message': f'Recommended products based on your cart items'
        })
        
    except Exception as e:
        return Response({
            'recommendations': [],
            'message': 'Unable to load recommendations'
        })

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def quick_add_to_cart(request):
    """
    Quick add multiple products to cart
    POST /api/cart/quick-add/
    Body: {"items": [{"product_id": 1, "quantity": 2}, {"product_id": 2, "quantity": 1}]}
    """
    items_data = request.data.get('items', [])
    
    if not items_data:
        return Response(
            {'error': 'No items provided'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    cart = get_or_create_cart(request)
    results = {'successful': [], 'failed': []}
    
    for item_data in items_data:
        try:
            product_id = item_data.get('product_id')
            quantity = item_data.get('quantity', 1)
            
            if not product_id:
                results['failed'].append({
                    'error': 'Product ID required',
                    'item': item_data
                })
                continue
            
            # Validate and add item (reuse add_to_cart logic)
            product = Product.objects.get(id=product_id, is_active=True)
            
            if not product.is_available or quantity > product.stock_quantity:
                results['failed'].append({
                    'product_id': product_id,
                    'product_name': product.name,
                    'error': 'Not available or insufficient stock'
                })
                continue
            
            # Get default vendor
            vendor = User.objects.filter(is_superuser=True).first()
            if not vendor:
                vendor = User.objects.first()
            
            # Add or update cart item
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product_id=product_id,
                defaults={
                    'product_name': product.name,
                    'product_description': product.description,
                    'unit_price': product.price,
                    'product_image': product.image_url,
                    'product_slug': product.slug,
                    'vendor': vendor,
                    'vendor_name': vendor.get_full_name() or vendor.email,
                    'quantity': quantity
                }
            )
            
            if not created:
                cart_item.quantity += quantity
                cart_item.save()
            
            results['successful'].append({
                'product_id': product_id,
                'product_name': product.name,
                'quantity': quantity,
                'action': 'created' if created else 'updated'
            })
            
        except Product.DoesNotExist:
            results['failed'].append({
                'product_id': item_data.get('product_id'),
                'error': 'Product not found'
            })
        except Exception as e:
            results['failed'].append({
                'item': item_data,
                'error': str(e)
            })
    
    return Response({
        'message': f'Added {len(results["successful"])} items to cart',
        'results': results,
        'cart_summary': CartSummarySerializer(cart).data
    })

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def cart_item_detail(request, item_id):
    """
    Get detailed information about a cart item
    GET /api/cart/items/{item_id}/detail/
    """
    cart = get_or_create_cart(request)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
    
    # Get current product information
    try:
        current_product = Product.objects.get(id=cart_item.product_id)
        product_available = current_product.is_available
        current_price = current_product.price
        current_stock = current_product.stock_quantity
        price_changed = current_price != cart_item.unit_price
    except Product.DoesNotExist:
        product_available = False
        current_price = cart_item.unit_price
        current_stock = 0
        price_changed = False
    
    item_data = CartItemSerializer(cart_item).data
    item_data.update({
        'product_status': {
            'available': product_available,
            'current_price': float(current_price),
            'price_changed': price_changed,
            'current_stock': current_stock,
            'stock_sufficient': current_stock >= cart_item.quantity
        }
    })
    
    return Response(item_data)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def apply_cart_discount(request):
    """
    Apply discount code to cart (placeholder for future implementation)
    POST /api/cart/discount/
    Body: {"code": "SAVE10"}
    """
    discount_code = request.data.get('code', '').strip().upper()
    cart = get_or_create_cart(request)
    
    if not discount_code:
        return Response(
            {'error': 'Discount code is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Placeholder discount logic - you can implement your own discount system
    discount_codes = {
        'SAVE10': {'type': 'percentage', 'value': 10, 'description': '10% off your order'},
        'FLAT50': {'type': 'fixed', 'value': 50, 'description': 'KES 50 off your order'},
        'FREESHIP': {'type': 'shipping', 'value': 0, 'description': 'Free shipping'},
    }
    
    if discount_code not in discount_codes:
        return Response(
            {'error': 'Invalid discount code'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    discount = discount_codes[discount_code]
    subtotal = cart.subtotal
    
    if discount['type'] == 'percentage':
        discount_amount = subtotal * (Decimal(discount['value']) / 100)
    elif discount['type'] == 'fixed':
        discount_amount = min(Decimal(discount['value']), subtotal)
    else:  # shipping discount
        discount_amount = Decimal('0.00')  # Would be shipping fee in real implementation
    
    # In a real implementation, you'd save this to a CartDiscount model
    # For now, just return the calculated values
    
    return Response({
        'message': f'Discount "{discount_code}" applied successfully',
        'discount': {
            'code': discount_code,
            'description': discount['description'],
            'amount': float(discount_amount),
            'type': discount['type']
        },
        'cart_totals': {
            'subtotal': float(subtotal),
            'discount_amount': float(discount_amount),
            'tax_amount': float((subtotal - discount_amount) * Decimal('0.16')),
            'total_amount': float((subtotal - discount_amount) * Decimal('1.16'))
        }
    })

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def cart_shipping_options(request):
    """
    Get available shipping options for cart
    GET /api/cart/shipping/
    """
    cart = get_or_create_cart(request)
    
    if not cart.items.exists():
        return Response({
            'shipping_options': [],
            'message': 'Cart is empty'
        })
    
    # Placeholder shipping options - implement your own logic
    shipping_options = [
        {
            'id': 'standard',
            'name': 'Standard Delivery',
            'description': '3-5 business days',
            'price': 0.00,
            'estimated_days': '3-5'
        },
        {
            'id': 'express',
            'name': 'Express Delivery',
            'description': '1-2 business days',
            'price': 200.00,
            'estimated_days': '1-2'
        },
        {
            'id': 'overnight',
            'name': 'Overnight Delivery',
            'description': 'Next business day',
            'price': 500.00,
            'estimated_days': '1'
        }
    ]
    
    return Response({
        'shipping_options': shipping_options,
        'cart_weight': 0.5,  # kg - calculate based on products
        'delivery_address': 'Nairobi, Kenya'  # Get from user profile or session
    })

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def estimate_cart_total(request):
    """
    Estimate cart total with shipping and discounts
    POST /api/cart/estimate/
    Body: {"shipping_option": "express", "discount_code": "SAVE10"}
    """
    cart = get_or_create_cart(request)
    shipping_option = request.data.get('shipping_option', 'standard')
    discount_code = request.data.get('discount_code', '').strip().upper()
    
    subtotal = cart.subtotal
    
    # Calculate shipping
    shipping_rates = {
        'standard': Decimal('0.00'),
        'express': Decimal('200.00'),
        'overnight': Decimal('500.00')
    }
    shipping_fee = shipping_rates.get(shipping_option, Decimal('0.00'))
    
    # Calculate discount
    discount_amount = Decimal('0.00')
    if discount_code:
        discount_codes = {
            'SAVE10': {'type': 'percentage', 'value': 10},
            'FLAT50': {'type': 'fixed', 'value': 50},
            'FREESHIP': {'type': 'shipping', 'value': 0},
        }
        
        if discount_code in discount_codes:
            discount = discount_codes[discount_code]
            if discount['type'] == 'percentage':
                discount_amount = subtotal * (Decimal(discount['value']) / 100)
            elif discount['type'] == 'fixed':
                discount_amount = min(Decimal(discount['value']), subtotal)
            elif discount['type'] == 'shipping':
                shipping_fee = Decimal('0.00')
    
    # Calculate totals
    discounted_subtotal = subtotal - discount_amount
    tax_amount = discounted_subtotal * Decimal('0.16')  # 16% VAT
    total_amount = discounted_subtotal + tax_amount + shipping_fee
    
    return Response({
        'estimate': {
            'subtotal': float(subtotal),
            'discount_amount': float(discount_amount),
            'discounted_subtotal': float(discounted_subtotal),
            'tax_amount': float(tax_amount),
            'shipping_fee': float(shipping_fee),
            'total_amount': float(total_amount)
        },
        'applied_discount': discount_code if discount_code and discount_amount > 0 else None,
        'shipping_option': shipping_option,
        'items_count': cart.total_items
    })

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def save_cart_for_later(request):
    """
    Save entire cart for later (move all items to saved items)
    POST /api/cart/save-all/
    """
    cart = get_or_create_cart(request)
    cart_items = cart.items.all()
    
    if not cart_items.exists():
        return Response(
            {'error': 'Cart is empty'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    saved_count = 0
    failed_items = []
    
    with transaction.atomic():
        for item in cart_items:
            try:
                # Create or update saved item
                saved_item, created = SavedItem.objects.get_or_create(
                    user=request.user,
                    product_id=item.product_id,
                    defaults={
                        'product_name': item.product_name,
                        'product_description': item.product_description,
                        'unit_price': item.unit_price,
                        'product_image': item.product_image,
                        'product_slug': item.product_slug,
                        'vendor': item.vendor,
                        'vendor_name': item.vendor_name,
                    }
                )
                
                item.delete()
                saved_count += 1
                
            except Exception as e:
                failed_items.append({
                    'product_name': item.product_name,
                    'error': str(e)
                })
    
    return Response({
        'message': f'Saved {saved_count} items for later',
        'saved_count': saved_count,
        'failed_items': failed_items,
        'cart_summary': CartSummarySerializer(cart).data
    })

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def cart_health_check(request):
    """
    Health check for cart system
    GET /api/cart/health/
    """
    try:
        cart = get_or_create_cart(request)
        
        health_status = {
            'status': 'healthy',
            'cart_accessible': True,
            'cart_id': str(cart.id),
            'items_count': cart.items.count(),
            'user_authenticated': request.user.is_authenticated,
            'session_available': bool(request.session.session_key),
            'timestamp': timezone.now().isoformat()
        }
        
        # Check for any issues
        issues = []
        
        # Check for items with invalid products
        for item in cart.items.all():
            try:
                Product.objects.get(id=item.product_id, is_active=True)
            except Product.DoesNotExist:
                issues.append(f'Invalid product in cart: {item.product_name}')
        
        if issues:
            health_status['status'] = 'warning'
            health_status['issues'] = issues
        
        return Response(health_status)
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# Add this to your cart/views.py to debug the checkout issue

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def convert_cart_to_order(request):
    """
    Convert cart to order - Updated with better error handling
    POST /api/cart/checkout/
    """
    try:
        cart = get_or_create_cart(request)
        
        if not cart.items.exists():
            return Response(
                {'error': 'Cart is empty'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Debug: Print request data
        print(f"Checkout request data: {request.data}")
        
        # Validate required fields
        required_fields = ['payment_method', 'shipping_address', 'shipping_city', 'shipping_phone']
        for field in required_fields:
            if not request.data.get(field):
                return Response(
                    {'error': f'{field} is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        serializer = CartToOrderSerializer(data=request.data)
        if not serializer.is_valid():
            print(f"Serializer errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            with transaction.atomic():
                # Create order
                order_data = {
                    'customer': request.user,
                    'payment_method': serializer.validated_data['payment_method'],
                    'shipping_address': serializer.validated_data['shipping_address'],
                    'shipping_city': serializer.validated_data['shipping_city'],
                    'shipping_country': serializer.validated_data.get('shipping_country', 'Kenya'),
                    'shipping_phone': serializer.validated_data['shipping_phone'],
                    'notes': serializer.validated_data.get('notes', ''),
                    'special_instructions': serializer.validated_data.get('special_instructions', ''),
                    'subtotal': cart.subtotal,
                    'tax_amount': cart.subtotal * Decimal('0.16'),  # 16% VAT
                    'shipping_fee': Decimal('0.00'),  # Free shipping
                    'discount_amount': Decimal('0.00'),
                    'total_amount': cart.total_amount
                }
                
                print(f"Creating order with data: {order_data}")
                order = Order.objects.create(**order_data)
                
                # Create order items from cart items
                for cart_item in cart.items.all():
                    order_item_data = {
                        'order': order,
                        'vendor': cart_item.vendor,
                        'product_name': cart_item.product_name,
                        'product_description': cart_item.product_description,
                        'unit_price': cart_item.unit_price,
                        'quantity': cart_item.quantity,
                        'product_image': cart_item.product_image,
                        'product_sku': cart_item.product_slug,
                    }
                    
                    print(f"Creating order item: {order_item_data}")
                    OrderItem.objects.create(**order_item_data)
                    
                    # Update product stock
                    try:
                        product = Product.objects.get(id=cart_item.product_id)
                        product.stock_quantity -= cart_item.quantity
                        if product.stock_quantity <= 0:
                            product.in_stock = False
                        product.save()
                        print(f"Updated product {product.id} stock to {product.stock_quantity}")
                    except Product.DoesNotExist:
                        print(f"Product {cart_item.product_id} not found for stock update")
                        pass  # Product might have been deleted
                
                # Clear cart after successful order creation
                cart.clear()
                
                # Send order confirmation (you can implement this)
                # send_order_notification(order, 'created')
                
                from orders.serializers import OrderDetailSerializer
                order_serializer = OrderDetailSerializer(order)
                
                return Response({
                    'message': 'Order created successfully',
                    'order': order_serializer.data
                }, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            print(f"Error in order creation transaction: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': f'Failed to create order: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    except Exception as e:
        print(f"Error in convert_cart_to_order: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response(
            {'error': f'Checkout failed: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )