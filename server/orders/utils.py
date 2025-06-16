# orders/utils.py
from decimal import Decimal
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)

def calculate_platform_commission(amount, commission_rate=None):
    """
    Calculate platform commission based on amount and rate
    
    Args:
        amount: Order amount (Decimal or float)
        commission_rate: Commission percentage (default from settings)
    
    Returns:
        Decimal: Commission amount
    """
    if commission_rate is None:
        commission_rate = getattr(settings, 'DEFAULT_COMMISSION_RATE', 15.0)
    
    amount = Decimal(str(amount))
    commission_rate = Decimal(str(commission_rate))
    
    commission = (amount * commission_rate) / 100
    return commission.quantize(Decimal('0.01'))

def calculate_vendor_earnings(amount, commission_rate=None):
    """
    Calculate vendor earnings after platform commission
    
    Args:
        amount: Order amount (Decimal or float)
        commission_rate: Commission percentage (default from settings)
    
    Returns:
        Decimal: Vendor earnings after commission
    """
    amount = Decimal(str(amount))
    commission = calculate_platform_commission(amount, commission_rate)
    earnings = amount - commission
    return earnings.quantize(Decimal('0.01'))

def calculate_tax(amount, tax_rate=None):
    """
    Calculate tax amount based on amount and rate
    
    Args:
        amount: Taxable amount (Decimal or float)
        tax_rate: Tax percentage (default from settings)
    
    Returns:
        Decimal: Tax amount
    """
    if tax_rate is None:
        tax_rate = getattr(settings, 'DEFAULT_TAX_RATE', 16.0)  # 16% VAT in Kenya
    
    amount = Decimal(str(amount))
    tax_rate = Decimal(str(tax_rate))
    
    tax = (amount * tax_rate) / 100
    return tax.quantize(Decimal('0.01'))

def calculate_order_totals(subtotal, shipping_fee=0, discount_amount=0, tax_rate=None):
    """
    Calculate complete order totals including tax
    
    Args:
        subtotal: Order subtotal
        shipping_fee: Shipping cost
        discount_amount: Discount applied
        tax_rate: Tax percentage
    
    Returns:
        dict: Dictionary with tax_amount, total_amount
    """
    subtotal = Decimal(str(subtotal))
    shipping_fee = Decimal(str(shipping_fee))
    discount_amount = Decimal(str(discount_amount))
    
    # Calculate tax on subtotal (before shipping and discounts)
    tax_amount = calculate_tax(subtotal, tax_rate)
    
    # Calculate final total
    total_amount = subtotal + tax_amount + shipping_fee - discount_amount
    
    return {
        'tax_amount': tax_amount.quantize(Decimal('0.01')),
        'total_amount': total_amount.quantize(Decimal('0.01'))
    }

def send_order_notification(order, notification_type, extra_context=None):
    """
    Send order-related email notifications
    
    Args:
        order: Order instance
        notification_type: Type of notification ('created', 'status_updated', etc.)
        extra_context: Additional context for email template
    """
    if not order.customer.email:
        logger.warning(f"No email address for customer in order {order.order_number}")
        return False
    
    try:
        # Email configurations
        email_configs = {
            'created': {
                'subject': f'Order Confirmation - {order.order_number}',
                'template': 'orders/emails/order_created.html',
                'text_template': 'orders/emails/order_created.txt'
            },
            'status_updated': {
                'subject': f'Order Update - {order.order_number}',
                'template': 'orders/emails/order_status_updated.html',
                'text_template': 'orders/emails/order_status_updated.txt'
            },
            'shipped': {
                'subject': f'Order Shipped - {order.order_number}',
                'template': 'orders/emails/order_shipped.html',
                'text_template': 'orders/emails/order_shipped.txt'
            },
            'delivered': {
                'subject': f'Order Delivered - {order.order_number}',
                'template': 'orders/emails/order_delivered.html',
                'text_template': 'orders/emails/order_delivered.txt'
            },
            'cancelled': {
                'subject': f'Order Cancelled - {order.order_number}',
                'template': 'orders/emails/order_cancelled.html',
                'text_template': 'orders/emails/order_cancelled.txt'
            }
        }
        
        config = email_configs.get(notification_type)
        if not config:
            logger.error(f"Unknown notification type: {notification_type}")
            return False
        
        # Prepare email context
        context = {
            'order': order,
            'customer': order.customer,
            'order_items': order.items.all(),
            'status_display': order.get_status_display(),
            'site_name': getattr(settings, 'SITE_NAME', 'Kipsunya Biz'),
            'site_url': getattr(settings, 'SITE_URL', 'http://localhost:3000'),
        }
        
        # Add extra context if provided
        if extra_context:
            context.update(extra_context)
        
        # Try to render HTML email, fall back to text
        try:
            html_message = render_to_string(config['template'], context)
        except:
            html_message = None
        
        try:
            text_message = render_to_string(config['text_template'], context)
        except:
            # Fallback text message
            text_message = _get_fallback_message(order, notification_type)
        
        # Send email
        send_mail(
            subject=config['subject'],
            message=text_message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@kipsunya.com'),
            recipient_list=[order.customer.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Email sent successfully for order {order.order_number} - {notification_type}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email for order {order.order_number}: {str(e)}")
        return False

def _get_fallback_message(order, notification_type):
    """
    Generate fallback text message when templates are not available
    """
    messages = {
        'created': f"""
Dear {order.customer.get_full_name() or order.customer.email},

Thank you for your order! Your order has been received and is being processed.

Order Details:
- Order Number: {order.order_number}
- Total Amount: KES {order.total_amount:,.2f}
- Status: {order.get_status_display()}

You can track your order status by logging into your account.

Thank you for shopping with us!

Best regards,
Kipsunya Biz Team
        """,
        
        'status_updated': f"""
Dear {order.customer.get_full_name() or order.customer.email},

Your order status has been updated.

Order Number: {order.order_number}
New Status: {order.get_status_display()}

You can view your order details by logging into your account.

Best regards,
Kipsunya Biz Team
        """,
        
        'shipped': f"""
Dear {order.customer.get_full_name() or order.customer.email},

Great news! Your order has been shipped.

Order Number: {order.order_number}
Tracking Number: {order.tracking_number or 'Will be provided soon'}

You can track your package using the tracking number above.

Best regards,
Kipsunya Biz Team
        """,
        
        'delivered': f"""
Dear {order.customer.get_full_name() or order.customer.email},

Your order has been delivered successfully!

Order Number: {order.order_number}

Thank you for shopping with us. We hope you're satisfied with your purchase.

Best regards,
Kipsunya Biz Team
        """,
        
        'cancelled': f"""
Dear {order.customer.get_full_name() or order.customer.email},

Your order has been cancelled as requested.

Order Number: {order.order_number}

If you have any questions, please don't hesitate to contact us.

Best regards,
Kipsunya Biz Team
        """
    }
    
    return messages.get(notification_type, f"Order {order.order_number} update - {notification_type}")

def send_vendor_notification(order, vendor, notification_type, extra_context=None):
    """
    Send notifications to vendors about orders containing their products
    
    Args:
        order: Order instance
        vendor: Vendor user instance
        notification_type: Type of notification
        extra_context: Additional context for email
    """
    if not vendor.email:
        logger.warning(f"No email address for vendor {vendor.id} in order {order.order_number}")
        return False
    
    try:
        vendor_items = order.items.filter(vendor=vendor)
        vendor_earnings = sum(item.vendor_earnings for item in vendor_items)
        
        subject_map = {
            'new_order': f'New Order Received - {order.order_number}',
            'order_cancelled': f'Order Cancelled - {order.order_number}',
            'payment_received': f'Payment Received - {order.order_number}'
        }
        
        message_map = {
            'new_order': f"""
Dear {vendor.get_full_name() or vendor.email},

You have received a new order!

Order Details:
- Order Number: {order.order_number}
- Customer: {order.customer.get_full_name() or order.customer.email}
- Your Items: {vendor_items.count()} items
- Your Earnings: KES {vendor_earnings:,.2f}

Please log into your vendor dashboard to manage this order.

Best regards,
Kipsunya Biz Team
            """,
            
            'order_cancelled': f"""
Dear {vendor.get_full_name() or vendor.email},

Order {order.order_number} has been cancelled.

This order contained {vendor_items.count()} of your items.

Best regards,
Kipsunya Biz Team
            """,
            
            'payment_received': f"""
Dear {vendor.get_full_name() or vendor.email},

Payment has been received for order {order.order_number}.

Your earnings: KES {vendor_earnings:,.2f} (after commission)

Payment will be processed according to your payout schedule.

Best regards,
Kipsunya Biz Team
            """
        }
        
        subject = subject_map.get(notification_type, f'Order Update - {order.order_number}')
        message = message_map.get(notification_type, f'Order {order.order_number} update')
        
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@kipsunya.com'),
            recipient_list=[vendor.email],
            fail_silently=False,
        )
        
        logger.info(f"Vendor email sent successfully for order {order.order_number} - {notification_type}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send vendor email for order {order.order_number}: {str(e)}")
        return False

def generate_order_number():
    """
    Generate unique order number
    This is a backup function in case the model method fails
    """
    import datetime
    from .models import Order
    
    now = datetime.datetime.now()
    base = f"ORD-{now.year}-{now.month:02d}"
    
    # Get the last order number for this month
    last_order = Order.objects.filter(
        order_number__startswith=base
    ).order_by('-order_number').first()
    
    if last_order:
        try:
            last_number = int(last_order.order_number.split('-')[-1])
            new_number = last_number + 1
        except (ValueError, IndexError):
            new_number = 1000
    else:
        new_number = 1000
        
    return f"{base}-{new_number}"

def validate_order_status_transition(current_status, new_status):
    """
    Validate if status transition is allowed
    
    Args:
        current_status: Current order status
        new_status: Desired new status
    
    Returns:
        bool: True if transition is valid
    """
    valid_transitions = {
        'pending': ['confirmed', 'cancelled'],
        'confirmed': ['processing', 'cancelled'],
        'processing': ['shipped', 'cancelled'],
        'shipped': ['delivered', 'cancelled'],
        'delivered': ['refunded'],
        'cancelled': [],
        'refunded': []
    }
    
    return new_status in valid_transitions.get(current_status, [])

def get_order_status_color(status):
    """
    Get color code for order status (for frontend)
    
    Args:
        status: Order status string
    
    Returns:
        dict: Color information
    """
    status_colors = {
        'pending': {'color': '#d97706', 'bg': '#fef3c7', 'text': 'text-yellow-800'},
        'confirmed': {'color': '#059669', 'bg': '#d1fae5', 'text': 'text-green-800'},
        'processing': {'color': '#4f46e5', 'bg': '#ede9fe', 'text': 'text-indigo-800'},
        'shipped': {'color': '#7c3aed', 'bg': '#f3e8ff', 'text': 'text-purple-800'},
        'delivered': {'color': '#059669', 'bg': '#dcfce7', 'text': 'text-green-800'},
        'cancelled': {'color': '#dc2626', 'bg': '#fee2e2', 'text': 'text-red-800'},
        'refunded': {'color': '#6b7280', 'bg': '#f3f4f6', 'text': 'text-gray-800'}
    }
    
    return status_colors.get(status, status_colors['pending'])

def format_currency(amount, currency='KES'):
    """
    Format currency amount for display
    
    Args:
        amount: Amount to format
        currency: Currency code
    
    Returns:
        str: Formatted currency string
    """
    if amount is None:
        return f"{currency} 0.00"
    
    try:
        amount = float(amount)
        return f"{currency} {amount:,.2f}"
    except (ValueError, TypeError):
        return f"{currency} 0.00"