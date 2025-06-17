# authentication/views.py
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
import json
import logging

# Add these imports that were missing
from .models import UserProfile

# Set up logging
logger = logging.getLogger(__name__)

# Custom serializer for JWT tokens with user data
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Add custom claims
        token['email'] = user.email
        token['first_name'] = user.first_name
        token['last_name'] = user.last_name
        
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Add user data to response
        data['user'] = {
            'id': self.user.id,
            'email': self.user.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'username': self.user.username,
            'role': getattr(self.user, 'role', 'customer'),  # Add role if you have it
        }
        
        # Rename tokens to match frontend expectations
        data['accessToken'] = data.pop('access')
        data['refreshToken'] = data.pop('refresh')
        
        return data

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    Register a new user
    """
    try:
        data = json.loads(request.body)
        
        # Extract user data
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        # Validation
        if not all([first_name, last_name, email, password]):
            return Response({
                'success': False,
                'message': 'All fields are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if len(password) < 8:
            return Response({
                'success': False,
                'message': 'Password must be at least 8 characters long'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if user already exists
        if User.objects.filter(email=email).exists():
            return Response({
                'success': False,
                'message': 'User with this email already exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create user
        user = User.objects.create_user(
            username=email,  # Use email as username
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password
        )
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token
        
        # Add custom claims
        access_token['email'] = user.email
        access_token['first_name'] = user.first_name
        access_token['last_name'] = user.last_name
        
        return Response({
            'success': True,
            'message': 'User created successfully',
            'accessToken': str(access_token),
            'refreshToken': str(refresh),
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'username': user.username,
                'role': getattr(user, 'role', 'customer'),
            }
        }, status=status.HTTP_201_CREATED)
        
    except json.JSONDecodeError:
        return Response({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    except IntegrityError:
        return Response({
            'success': False,
            'message': 'User with this email already exists'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response({
            'success': False,
            'message': 'Registration failed. Please try again.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    Login user with email and password
    """
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        if not email or not password:
            return Response({
                'success': False,
                'message': 'Email and password are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Authenticate user
        user = authenticate(username=email, password=password)
        
        if user is None:
            # Try to find user by email and check if they exist
            try:
                user_obj = User.objects.get(email=email)
                # User exists but password is wrong
                return Response({
                    'success': False,
                    'message': 'Invalid password'
                }, status=status.HTTP_401_UNAUTHORIZED)
            except User.DoesNotExist:
                # User doesn't exist
                return Response({
                    'success': False,
                    'message': 'No account found with this email'
                }, status=status.HTTP_401_UNAUTHORIZED)
        
        if not user.is_active:
            return Response({
                'success': False,
                'message': 'Account is disabled'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token
        
        # Add custom claims
        access_token['email'] = user.email
        access_token['first_name'] = user.first_name
        access_token['last_name'] = user.last_name
        
        return Response({
            'success': True,
            'message': 'Login successful',
            'accessToken': str(access_token),
            'refreshToken': str(refresh),
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'username': user.username,
                'role': getattr(user, 'role', 'customer'),
            }
        }, status=status.HTTP_200_OK)
        
    except json.JSONDecodeError:
        return Response({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response({
            'success': False,
            'message': 'Login failed. Please try again.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    Logout user by blacklisting the refresh token
    """
    try:
        refresh_token = request.data.get('refresh_token')
        
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        
        return Response({
            'success': True,
            'message': 'Logout successful'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': True,  # Still return success even if blacklist fails
            'message': 'Logout completed'
        }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verify_token(request):
    """
    Verify if the current token is valid and return user data
    """
    try:
        user = request.user
        return Response({
            'success': True,
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'username': user.username,
                'role': getattr(user, 'role', 'customer'),
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'message': 'Token verification failed'
        }, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """
    Update user profile
    """
    try:
        user = request.user
        data = json.loads(request.body)
        
        # Update allowed fields
        if 'first_name' in data:
            user.first_name = data['first_name'].strip()
        if 'last_name' in data:
            user.last_name = data['last_name'].strip()
        if 'email' in data:
            new_email = data['email'].strip().lower()
            # Check if email is already taken by another user
            if User.objects.filter(email=new_email).exclude(id=user.id).exists():
                return Response({
                    'success': False,
                    'message': 'Email is already taken'
                }, status=status.HTTP_400_BAD_REQUEST)
            user.email = new_email
            user.username = new_email
        
        user.save()
        
        return Response({
            'success': True,
            'message': 'Profile updated successfully',
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'username': user.username,
                'role': getattr(user, 'role', 'customer'),
            }
        }, status=status.HTTP_200_OK)
        
    except json.JSONDecodeError:
        return Response({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response({
            'success': False,
            'message': 'Profile update failed'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Custom refresh token view
class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            # Rename 'access' to 'accessToken' to match frontend expectations
            data = response.data
            data['accessToken'] = data.pop('access')
            
        return response

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upgrade_to_vendor(request):
    """
    Upgrade user from customer to vendor with comprehensive business information
    """
    user = request.user
    
    # Check if user is eligible for upgrade
    if user.role != 'customer':
        return Response({
            'success': False,
            'message': 'Only customers can upgrade to vendor accounts'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get form data
        data = request.data
        
        # Validate required fields
        required_fields = ['business_name', 'business_type', 'business_email', 'shipping_policy', 'return_policy']
        missing_fields = []
        
        for field in required_fields:
            if not data.get(field, '').strip():
                missing_fields.append(field.replace('_', ' ').title())
        
        if missing_fields:
            return Response({
                'success': False,
                'message': f'Missing required fields: {", ".join(missing_fields)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate agreements
        if not data.get('agree_to_terms'):
            return Response({
                'success': False,
                'message': 'You must agree to the terms and conditions'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not data.get('agree_to_commission'):
            return Response({
                'success': False,
                'message': 'You must agree to the commission structure'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update user profile
        profile, created = UserProfile.objects.get_or_create(user=user)
        profile.role = 'vendor'
        
        # Business information
        profile.business_name = data.get('business_name', '').strip()
        profile.business_type = data.get('business_type', '').strip()
        profile.business_description = data.get('business_description', '').strip()
        
        # Contact information
        profile.business_phone = data.get('business_phone', '').strip()
        profile.business_email = data.get('business_email', '').strip()
        profile.business_address = data.get('business_address', '').strip()
        profile.website = data.get('website', '').strip()
        
        # Business details
        profile.tax_id = data.get('tax_id', '').strip()
        # Add these fields to your UserProfile model if they don't exist
        if hasattr(profile, 'years_in_business'):
            profile.years_in_business = data.get('years_in_business', '').strip()
        if hasattr(profile, 'number_of_employees'):
            profile.number_of_employees = data.get('number_of_employees', '').strip()
        if hasattr(profile, 'expected_monthly_sales'):
            profile.expected_monthly_sales = data.get('expected_monthly_sales', '').strip()
        
        # Policies
        if hasattr(profile, 'shipping_policy'):
            profile.shipping_policy = data.get('shipping_policy', '').strip()
        if hasattr(profile, 'return_policy'):
            profile.return_policy = data.get('return_policy', '').strip()
        
        # Social media (store as JSON)
        social_media = data.get('social_media', {})
        if social_media and hasattr(profile, 'social_media'):
            profile.social_media = {
                'facebook': social_media.get('facebook', '').strip(),
                'instagram': social_media.get('instagram', '').strip(),
                'twitter': social_media.get('twitter', '').strip(),
                'linkedin': social_media.get('linkedin', '').strip()
            }
        
        # Set vendor status
        if hasattr(profile, 'business_verified'):
            profile.business_verified = False  # Will be verified by admin
        if hasattr(profile, 'vendor_approved_at'):
            profile.vendor_approved_at = timezone.now()
        
        # Save the profile
        profile.save()
        
        # Optional: Create vendor application record for admin review
        # You can uncomment this if you add the VendorApplication model
        # try:
        #     VendorApplication.objects.create(
        #         user=user,
        #         business_name=profile.business_name,
        #         business_type=profile.business_type,
        #         application_data=data,
        #         status='pending',
        #         applied_at=timezone.now()
        #     )
        # except Exception as e:
        #     logger.warning(f"Failed to create vendor application record: {str(e)}")
        
        # Send notification emails
        try:
            # Send welcome email to new vendor
            send_vendor_welcome_email(user, profile)
            
            # Send notification to admin
            send_vendor_application_notification(user, profile)
        except Exception as e:
            # Log email error but don't fail the upgrade
            logger.error(f"Failed to send vendor upgrade emails: {str(e)}")
        
        # Return success response with updated user data
        return Response({
            'success': True,
            'message': 'Vendor account created successfully!',
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'username': user.username,
                'role': 'vendor',
                'business_name': profile.business_name,
                'business_type': profile.business_type,
                'business_verified': getattr(profile, 'business_verified', False),
                'business_email': profile.business_email,
                'business_phone': profile.business_phone,
                'website': profile.website
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Vendor upgrade failed for user {user.id}: {str(e)}")
        return Response({
            'success': False,
            'message': 'An error occurred during the upgrade process. Please try again.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def send_vendor_welcome_email(user, profile):
    """Send welcome email to new vendor"""
    try:
        subject = "Welcome to Kipsunya Biz - Your Vendor Account is Ready!"
        
        message = f"""
Dear {user.get_full_name() or user.email},

Congratulations! Your vendor account has been successfully created on Kipsunya Biz.

Business Details:
- Business Name: {profile.business_name}
- Business Type: {profile.business_type}
- Business Email: {profile.business_email}

Next Steps:
1. Complete your business profile
2. Add your first products
3. Set up your store policies
4. Start selling to thousands of customers

Your vendor dashboard: https://kipsunya.com/vendor/dashboard

If you have any questions, our vendor support team is here to help:
- Email: vendor-support@kipsunya.com
- Phone: +254 700 000 000

Welcome to the Kipsunya Biz family!

Best regards,
The Kipsunya Biz Team
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@kipsunya.com'),
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info(f"Welcome email sent to new vendor: {user.email}")
        
    except Exception as e:
        logger.error(f"Failed to send welcome email to {user.email}: {str(e)}")


def send_vendor_application_notification(user, profile):
    """Send notification to admin about new vendor application"""
    try:
        subject = f"New Vendor Application - {profile.business_name}"
        
        message = f"""
A new vendor has registered on Kipsunya Biz:

Vendor Details:
- Name: {user.get_full_name()}
- Email: {user.email}
- Business Name: {profile.business_name}
- Business Type: {profile.business_type}
- Business Email: {profile.business_email}
- Phone: {profile.business_phone}
- Applied: {timezone.now().strftime('%Y-%m-%d %H:%M')}

Please review the application in the admin panel:
https://kipsunya.com/admin/vendors/

Best regards,
Kipsunya Biz System
        """
        
        # Send to admin emails - update these with your actual admin emails
        admin_emails = ['admin@kipsunya.com', 'vendors@kipsunya.com']
        
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@kipsunya.com'),
            recipient_list=admin_emails,
            fail_silently=True,  # Don't fail if admin emails don't work
        )
        logger.info(f"Admin notification sent for new vendor: {profile.business_name}")
        
    except Exception as e:
        logger.error(f"Failed to send admin notification: {str(e)}")

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def vendor_detail(request, vendor_id):
    """
    Get vendor details - only for authenticated users
    """
    vendor = get_object_or_404(User, id=vendor_id, profile__role='vendor')
    serializer = VendorSerializer(vendor)
    return Response({
        'success': True,
        'vendor': serializer.data
    })
