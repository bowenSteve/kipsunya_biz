from rest_framework import generics, filters
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Product, Category
from .serializers import ProductSerializer, CategorySerializer

class AllProductsView(generics.ListAPIView):
    """
    API endpoint that returns all products with filtering, searching, and ordering capabilities.
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # Filtering options
    filterset_fields = ['category', 'in_stock', 'featured', 'is_active']
    
    # Search functionality
    search_fields = ['name', 'description', 'category__name']
    
    # Ordering options
    ordering_fields = ['price', 'created_at', 'name', 'stock_quantity']
    ordering = ['-created_at']  # Default ordering by newest first

    def get_queryset(self):
        """
        Optionally restricts the returned products,
        by filtering against query parameters in the URL.
        """
        queryset = Product.objects.select_related('category')
        
        # Filter by availability
        available_only = self.request.query_params.get('available_only', None)
        if available_only is not None and available_only.lower() == 'true':
            queryset = queryset.filter(in_stock=True, stock_quantity__gt=0, is_active=True)
        
        # Filter by price range
        min_price = self.request.query_params.get('min_price', None)
        max_price = self.request.query_params.get('max_price', None)
        
        if min_price is not None:
            queryset = queryset.filter(price__gte=min_price)
        if max_price is not None:
            queryset = queryset.filter(price__lte=max_price)
            
        return queryset

# Alternative function-based view (simpler approach)
@api_view(['GET'])
def all_products_simple(request):
    """
    Simple API endpoint that returns all products.
    """
    products = Product.objects.select_related('category').all()
    serializer = ProductSerializer(products, many=True)
    
    return Response({
        'success': True,
        'count': len(serializer.data),
        'products': serializer.data
    })

# Additional endpoints you might need
@api_view(['GET'])
def featured_products(request):
    """
    API endpoint that returns only featured products.
    """
    products = Product.objects.select_related('category').filter(featured=True, is_active=True)
    serializer = ProductSerializer(products, many=True)
    
    return Response({
        'success': True,
        'count': len(serializer.data),
        'featured_products': serializer.data
    })

# UPDATED: Changed from slug to ID
@api_view(['GET'])
def product_by_id(request, id):
    """
    API endpoint that returns a single product by ID.
    """
    try:
        product = Product.objects.select_related('category').get(id=id, is_active=True)
        serializer = ProductSerializer(product)
        return Response({
            'success': True,
            'product': serializer.data
        })
    except Product.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Product not found'
        }, status=404)
    except ValueError:
        return Response({
            'success': False,
            'message': 'Invalid product ID'
        }, status=400)

# Keep the slug version if you want both options
@api_view(['GET'])
def product_by_slug(request, slug):
    """
    API endpoint that returns a single product by slug.
    """
    try:
        product = Product.objects.select_related('category').get(slug=slug, is_active=True)
        serializer = ProductSerializer(product)
        return Response({
            'success': True,
            'product': serializer.data
        })
    except Product.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Product not found'
        }, status=404)

@api_view(['GET'])
def categories(request):
    """
    API endpoint that returns all categories.
    """
    categories = Category.objects.all()
    serializer = CategorySerializer(categories, many=True)
    
    return Response({
        'success': True,
        'count': len(serializer.data),
        'categories': serializer.data
    })