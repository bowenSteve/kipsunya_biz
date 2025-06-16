# authentication/models.py
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    """Extend Django's User with additional fields needed for orders"""
    
    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('vendor', 'Vendor'),
        ('admin', 'Admin'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    
    # Basic profile fields
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, default='Kenya')
    date_of_birth = models.DateField(blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    business_name = models.CharField(max_length=255, blank=True, null=True)
    business_type = models.CharField(max_length=100, blank=True, null=True)
    business_description = models.TextField(blank=True, null=True)
    business_phone = models.CharField(max_length=20, blank=True, null=True)
    business_email = models.EmailField(blank=True, null=True)
    business_address = models.TextField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    tax_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Business details
    years_in_business = models.CharField(max_length=20, blank=True, null=True)
    number_of_employees = models.CharField(max_length=20, blank=True, null=True)
    expected_monthly_sales = models.CharField(max_length=50, blank=True, null=True)
    
    # Policies
    shipping_policy = models.TextField(blank=True, null=True)
    return_policy = models.TextField(blank=True, null=True)
    
    # Social media (stored as JSON)
    social_media = models.JSONField(default=dict, blank=True)
    
    # Vendor status
    business_verified = models.BooleanField(default=False)
    vendor_approved_at = models.DateTimeField(null=True, blank=True)
    # Vendor fields (basic)
    business_name = models.CharField(max_length=255, blank=True, null=True)
    business_type = models.CharField(max_length=100, blank=True, null=True)
    business_verified = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.email} - {self.get_role_display()}"

# Automatically create profile when user is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()

# Add role property to User model for easy access
def get_user_role(self):
    try:
        return self.profile.role
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=self, role='customer')
        return 'customer'

User.add_to_class('role', property(get_user_role))