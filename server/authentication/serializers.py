from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile

class VendorSerializer(serializers.ModelSerializer):
    """Serializer for vendor information"""
    phone = serializers.CharField(source='profile.phone', read_only=True)
    business_name = serializers.CharField(source='profile.business_name', read_only=True)
    business_type = serializers.CharField(source='profile.business_type', read_only=True)
    business_verified = serializers.BooleanField(source='profile.business_verified', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'email',
            'phone', 'business_name', 'business_type', 'business_verified'
        ]
