# orders/permissions.py
from rest_framework import permissions

class IsCustomerOrVendor(permissions.BasePermission):
    """
    Permission to allow customers to view their orders
    and vendors to view orders containing their products
    """
    
    def has_permission(self, request, view):
        """Check if user is authenticated"""
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """Check if user can access this specific order"""
        user = request.user
        
        # Admin can access everything
        if user.is_superuser or getattr(user, 'role', None) == 'admin':
            return True
        
        # Customer can only access their own orders
        if getattr(user, 'role', None) == 'customer':
            return obj.customer == user
        
        # Vendor can access orders containing their products
        elif getattr(user, 'role', None) == 'vendor':
            return obj.items.filter(vendor=user).exists()
        
        # Default deny
        return False


class IsVendorOwner(permissions.BasePermission):
    """
    Permission for vendors to update orders containing their products
    """
    
    def has_permission(self, request, view):
        """Check if user is authenticated and is a vendor or admin"""
        if not (request.user and request.user.is_authenticated):
            return False
        
        user_role = getattr(request.user, 'role', None)
        return user_role in ['vendor', 'admin'] or request.user.is_superuser
    
    def has_object_permission(self, request, view, obj):
        """Check if vendor owns products in this order"""
        user = request.user
        
        # Admin can access everything
        if user.is_superuser or getattr(user, 'role', None) == 'admin':
            return True
        
        # Vendor can only modify orders containing their products
        if getattr(user, 'role', None) == 'vendor':
            return obj.items.filter(vendor=user).exists()
        
        return False


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to the owner of the object
        # or admin users
        if request.user.is_superuser:
            return True
        
        # Check if object has customer attribute (for orders)
        if hasattr(obj, 'customer'):
            return obj.customer == request.user
        
        # Check if object has user attribute (for profiles, etc.)
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # Check if object has requested_by attribute (for refunds)
        if hasattr(obj, 'requested_by'):
            return obj.requested_by == request.user
        
        return False


class IsVendorOrAdmin(permissions.BasePermission):
    """
    Permission to allow only vendors and admins
    """
    
    def has_permission(self, request, view):
        """Check if user is vendor or admin"""
        if not (request.user and request.user.is_authenticated):
            return False
        
        user_role = getattr(request.user, 'role', None)
        return user_role in ['vendor', 'admin'] or request.user.is_superuser


class IsAdminOnly(permissions.BasePermission):
    """
    Permission to allow only admin users
    """
    
    def has_permission(self, request, view):
        """Check if user is admin"""
        if not (request.user and request.user.is_authenticated):
            return False
        
        return getattr(request.user, 'role', None) == 'admin' or request.user.is_superuser


class IsCustomerOnly(permissions.BasePermission):
    """
    Permission to allow only customers
    """
    
    def has_permission(self, request, view):
        """Check if user is customer"""
        if not (request.user and request.user.is_authenticated):
            return False
        
        return getattr(request.user, 'role', None) == 'customer'


class CanViewOrder(permissions.BasePermission):
    """
    Permission for order viewing based on user role
    """
    
    def has_object_permission(self, request, view, obj):
        """Check if user can view this order"""
        user = request.user
        
        if not user.is_authenticated:
            return False
        
        # Admin can view everything
        if user.is_superuser or getattr(user, 'role', None) == 'admin':
            return True
        
        # Customer can view their own orders
        if getattr(user, 'role', None) == 'customer':
            return obj.customer == user
        
        # Vendor can view orders containing their products
        if getattr(user, 'role', None) == 'vendor':
            return obj.items.filter(vendor=user).exists()
        
        return False


class CanModifyOrder(permissions.BasePermission):
    """
    Permission for order modification based on user role and order status
    """
    
    def has_object_permission(self, request, view, obj):
        """Check if user can modify this order"""
        user = request.user
        
        if not user.is_authenticated:
            return False
        
        # Admin can modify everything
        if user.is_superuser or getattr(user, 'role', None) == 'admin':
            return True
        
        # Customers can only cancel their pending/confirmed orders
        if getattr(user, 'role', None) == 'customer' and obj.customer == user:
            # Only allow modification of certain fields and only for certain statuses
            if request.method == 'DELETE':  # Cancel order
                return obj.status in ['pending', 'confirmed']
            else:  # Update order
                return obj.status == 'pending'
        
        # Vendors can update status of orders containing their products
        if getattr(user, 'role', None) == 'vendor':
            return obj.items.filter(vendor=user).exists()
        
        return False


class CanProcessRefund(permissions.BasePermission):
    """
    Permission for processing refunds
    """
    
    def has_permission(self, request, view):
        """Only admins can process refunds"""
        if not (request.user and request.user.is_authenticated):
            return False
        
        return getattr(request.user, 'role', None) == 'admin' or request.user.is_superuser
    
    def has_object_permission(self, request, view, obj):
        """Check if user can process this refund"""
        user = request.user
        
        # Admin can process all refunds
        if user.is_superuser or getattr(user, 'role', None) == 'admin':
            return True
        
        return False


class CanRequestRefund(permissions.BasePermission):
    """
    Permission for requesting refunds
    """
    
    def has_permission(self, request, view):
        """Authenticated users can request refunds"""
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """Check if user can request refund for this order"""
        user = request.user
        
        # Admin can create refunds for any order
        if user.is_superuser or getattr(user, 'role', None) == 'admin':
            return True
        
        # Customer can only request refunds for their own delivered orders
        if getattr(user, 'role', None) == 'customer':
            return (obj.customer == user and 
                   obj.status == 'delivered')
        
        return False