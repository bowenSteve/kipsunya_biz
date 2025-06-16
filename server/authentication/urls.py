# Create a new file: authentication/urls.py
from django.urls import path
from . import views
from .views import CustomTokenObtainPairView, CustomTokenRefreshView

urlpatterns = [
    # Authentication endpoints
    path('login/', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout, name='logout'),
    path('verify/', views.verify_token, name='verify_token'),
    path('refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    
    # User profile endpoints
    path('profile/', views.update_profile, name='update_profile'),
    
    # Alternative JWT endpoints (if you prefer class-based views)
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('upgrade-to-vendor/', views.upgrade_to_vendor, name='upgrade_to_vendor')
]

# Update your main server/urls.py to include authentication URLs
"""
# server/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('products.urls')),
    path('api/auth/', include('authentication.urls')),  # Add this line

]
"""