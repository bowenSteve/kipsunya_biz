# products/views.py - Complete CRUD operations
from rest_framework import generics, filters, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from .models import Product, Category
from .serializers import ProductSerializer, CategorySerializer

# Existing read-only views
class AllProductsView(generics.ListAPIView):
    """
    API endpoint that returns all products with filtering, searching, and ordering capabilities.
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    filterset_fields = ['category', 'in_stock', 'featured', 'is_active']
    search_fields = ['name', 'description', 'category__name']
    ordering_fields = ['price', 'created_at', 'name', 'stock_quantity']
    ordering = ['-created_at']

    def get_queryset(self):
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

# NEW: Product CRUD Operations
class ProductListCreateView(generics.ListCreateAPIView):
    """
    List products or create new product (for vendors)
    GET: List all products
    POST: Create new product (vendors only)
    """
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'in_stock', 'featured', 'is_active']
    search_fields = ['name', 'description', 'category__name']
    ordering_fields = ['price', 'created_at', 'name', 'stock_quantity']
    ordering = ['-created_at']

    def get_permissions(self):
        """
        Allow anyone to read, but only authenticated users to create
        """
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        queryset = Product.objects.select_related('category')
        
        # If user is authenticated and is a vendor, show only their products
        if user.is_authenticated and hasattr(user, 'role') and user.role == 'vendor':
            queryset = queryset.filter(vendor=user)
        
        return queryset

    def perform_create(self, serializer):
        """
        Set the vendor to the current user when creating a product
        """
        # Auto-generate slug if not provided
        name = serializer.validated_data.get('name')
        slug = serializer.validated_data.get('slug')
        
        if not slug:
            base_slug = slugify(name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
        
        serializer.save(vendor=self.request.user, slug=slug)

class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a product
    GET: Anyone can view
    PUT/PATCH: Only product owner (vendor) or admin
    DELETE: Only product owner (vendor) or admin
    """
    serializer_class = ProductSerializer
    lookup_field = 'id'

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        if self.request.method == 'GET':
            return Product.objects.select_related('category').filter(is_active=True)
        else:
            # For write operations, user can only access their own products
            user = self.request.user
            if hasattr(user, 'role') and user.role == 'admin':
                return Product.objects.select_related('category').all()
            else:
                return Product.objects.select_related('category').filter(vendor=user)

    def perform_update(self, serializer):
        """
        Update slug if name changed
        """
        instance = serializer.instance
        name = serializer.validated_data.get('name', instance.name)
        
        # Only update slug if name changed and no custom slug provided
        if name != instance.name and 'slug' not in serializer.validated_data:
            base_slug = slugify(name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exclude(id=instance.id).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            serializer.validated_data['slug'] = slug
        
        serializer.save()

# NEW: Category CRUD Operations
class CategoryListCreateView(generics.ListCreateAPIView):
    """
    List categories or create new category
    GET: Anyone can view
    POST: Only authenticated users (vendors/admins)
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        """
        Auto-generate slug if not provided
        """
        name = serializer.validated_data.get('name')
        slug = serializer.validated_data.get('slug')
        
        if not slug:
            base_slug = slugify(name)
            slug = base_slug
            counter = 1
            while Category.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
        
        serializer.save(slug=slug)

class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a category
    GET: Anyone can view
    PUT/PATCH/DELETE: Only admins or category creators
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = 'id'

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def perform_update(self, serializer):
        """
        Update slug if name changed
        """
        instance = serializer.instance
        name = serializer.validated_data.get('name', instance.name)
        
        if name != instance.name and 'slug' not in serializer.validated_data:
            base_slug = slugify(name)
            slug = base_slug
            counter = 1
            while Category.objects.filter(slug=slug).exclude(id=instance.id).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            serializer.validated_data['slug'] = slug
        
        serializer.save()

# Existing function-based views
@api_view(['GET'])
@permission_classes([AllowAny])
def all_products_simple(request):
    """
    Simple API endpoint that returns all products.
    """
    products = Product.objects.select_related('category').all()
    serializer = ProductSerializer(products, many=True, context={'request': request})
    
    return Response({
        'success': True,
        'count': len(serializer.data),
        'products': serializer.data
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def featured_products(request):
    """
    API endpoint that returns only featured products.
    """
    products = Product.objects.select_related('category').filter(featured=True, is_active=True)
    serializer = ProductSerializer(products, many=True, context={'request': request})
    
    return Response({
        'success': True,
        'count': len(serializer.data),
        'featured_products': serializer.data
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def product_by_id(request, id):
    """
    API endpoint that returns a single product by ID.
    """
    try:
        product = Product.objects.select_related('category').get(id=id, is_active=True)
        serializer = ProductSerializer(product, context={'request': request})
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

@api_view(['GET'])
@permission_classes([AllowAny])
def product_by_slug(request, slug):
    """
    API endpoint that returns a single product by slug.
    """
    try:
        product = Product.objects.select_related('category').get(slug=slug, is_active=True)
        serializer = ProductSerializer(product, context={'request': request})
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
@permission_classes([AllowAny])
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

# NEW: Vendor-specific endpoints
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def vendor_products(request):
    """
    Get all products for the current vendor
    """
    if not hasattr(request.user, 'role') or request.user.role != 'vendor':
        return Response({
            'error': 'Only vendors can access this endpoint'
        }, status=403)
    
    products = Product.objects.select_related('category').filter(vendor=request.user)
    serializer = ProductSerializer(products, many=True, context={'request': request})
    
    return Response({
        'success': True,
        'count': len(serializer.data),
        'products': serializer.data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_product(request):
    """
    Create a new product (vendors only)
    """
    if not hasattr(request.user, 'role') or request.user.role not in ['vendor', 'admin']:
        return Response({
            'error': 'Only vendors and admins can create products'
        }, status=403)
    
    serializer = ProductSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        # Auto-generate slug if not provided
        name = serializer.validated_data.get('name')
        slug = serializer.validated_data.get('slug')
        
        if not slug:
            base_slug = slugify(name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
        
        product = serializer.save(vendor=request.user, slug=slug)
        
        return Response({
            'success': True,
            'message': 'Product created successfully',
            'product': ProductSerializer(product, context={'request': request}).data
        }, status=201)
    
    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=400)

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_product(request, product_id):
    """
    Update a product (only owner or admin)
    """
    try:
        if hasattr(request.user, 'role') and request.user.role == 'admin':
            product = Product.objects.get(id=product_id)
        else:
            product = Product.objects.get(id=product_id, vendor=request.user)
    except Product.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Product not found or you do not have permission to edit it'
        }, status=404)
    
    partial = request.method == 'PATCH'
    serializer = ProductSerializer(product, data=request.data, partial=partial, context={'request': request})
    
    if serializer.is_valid():
        # Update slug if name changed
        name = serializer.validated_data.get('name', product.name)
        if name != product.name and 'slug' not in serializer.validated_data:
            base_slug = slugify(name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exclude(id=product.id).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            serializer.validated_data['slug'] = slug
        
        updated_product = serializer.save()
        
        return Response({
            'success': True,
            'message': 'Product updated successfully',
            'product': ProductSerializer(updated_product, context={'request': request}).data
        })
    
    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=400)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_product(request, product_id):
    """
    Delete a product (only owner or admin)
    """
    try:
        if hasattr(request.user, 'role') and request.user.role == 'admin':
            product = Product.objects.get(id=product_id)
        else:
            product = Product.objects.get(id=product_id, vendor=request.user)
    except Product.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Product not found or you do not have permission to delete it'
        }, status=404)
    
    product_name = product.name
    product.delete()
    
    return Response({
        'success': True,
        'message': f'Product "{product_name}" deleted successfully'
    })