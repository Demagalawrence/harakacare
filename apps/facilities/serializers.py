from rest_framework import serializers
from .models import Facility


class FacilitySerializer(serializers.ModelSerializer):
    """
    Serializer for the Facility model.
    
    Handles serialization and deserialization of Facility data for API endpoints.
    Includes validation and proper field formatting.
    """
    
    facility_type_display = serializers.CharField(source='get_facility_type_display', read_only=True)
    
    class Meta:
        model = Facility
        fields = [
            'id', 'name', 'facility_type', 'facility_type_display', 
            'address', 'latitude', 'longitude', 'phone_number', 
            'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'facility_type_display']
    
    def validate_phone_number(self, value):
        """
        Validate phone number format if provided.
        """
        if value and not value.replace('+', '').replace('-', '').replace(' ', '').isdigit():
            raise serializers.ValidationError("Phone number must contain only digits, +, -, and spaces.")
        return value
    
    def validate_name(self, value):
        """
        Validate facility name is not empty or just whitespace.
        """
        if not value.strip():
            raise serializers.ValidationError("Facility name cannot be empty.")
        return value.strip()
    
    def validate_latitude(self, value):
        """
        Validate latitude is within valid range (-90 to 90).
        """
        if value is not None and not (-90 <= value <= 90):
            raise serializers.ValidationError("Latitude must be between -90 and 90 degrees.")
        return value
    
    def validate_longitude(self, value):
        """
        Validate longitude is within valid range (-180 to 180).
        """
        if value is not None and not (-180 <= value <= 180):
            raise serializers.ValidationError("Longitude must be between -180 and 180 degrees.")
        return value
    
    def validate(self, data):
        """
        Validate that if latitude is provided, longitude must also be provided and vice versa.
        """
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if (latitude is not None and longitude is None) or (latitude is None and longitude is not None):
            raise serializers.ValidationError(
                "Both latitude and longitude must be provided together."
            )
        
        return data
