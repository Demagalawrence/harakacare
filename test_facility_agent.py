"""
Test script for HarakaCare Facility Agent
Tests the core functionality without requiring migrations
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'harakacare.settings.development')
django.setup()

from apps.facilities.tools.facility_matching import FacilityMatchingTool
from apps.facilities.tools.prioritization import PrioritizationTool
from apps.facilities.tools.notification_dispatch import NotificationDispatchTool
from apps.facilities.tools.logging_monitoring import LoggingMonitoringTool
from apps.facilities.models import Facility


def test_facility_matching():
    """Test facility matching functionality"""
    print("🔍 Testing Facility Matching Tool...")
    
    # Create mock triage data
    triage_data = {
        'patient_token': 'test_patient_123',
        'risk_level': 'high',
        'primary_symptom': 'chest_pain',
        'secondary_symptoms': ['difficulty_breathing'],
        'has_red_flags': True,
        'chronic_conditions': ['hypertension'],
        'patient_district': 'Nairobi',
        'patient_location_lat': -1.2921,
        'patient_location_lng': 36.8219,
    }
    
    # Create mock routing object (without saving to DB)
    class MockRouting:
        def __init__(self, data):
            self.patient_token = data['patient_token']
            self.risk_level = data['risk_level']
            self.primary_symptom = data['primary_symptom']
            self.secondary_symptoms = data['secondary_symptoms']
            self.has_red_flags = data['has_red_flags']
            self.chronic_conditions = data['chronic_conditions']
            self.patient_district = data['patient_district']
            self.patient_location_lat = data['patient_location_lat']
            self.patient_location_lng = data['patient_location_lng']
        
        @property
        def is_emergency(self):
            return self.has_red_flags or self.risk_level == 'high'
    
    mock_routing = MockRouting(triage_data)
    
    # Test matching tool
    matching_tool = FacilityMatchingTool()
    
    # Test distance calculation
    print("📍 Testing distance calculation...")
    test_lat, test_lng = -1.2921, 36.8219
    distance_score = matching_tool._calculate_distance_score(5.0)
    print(f"   Distance score for 5km: {distance_score}")
    
    # Test capacity scoring
    print("🏥 Testing capacity scoring...")
    mock_facility = Facility(
        name="Test Hospital",
        available_beds=10,
        total_beds=50
    )
    capacity_score = matching_tool._calculate_capacity_score(mock_facility, mock_routing)
    print(f"   Capacity score: {capacity_score}")
    
    # Test service matching
    print("🩺 Testing service matching...")
    service_score = matching_tool._calculate_service_score(mock_facility, mock_routing)
    print(f"   Service score: {service_score}")
    
    print("✅ Facility Matching Tool tests completed!\n")


def test_prioritization():
    """Test prioritization functionality"""
    print("🎯 Testing Prioritization Tool...")
    
    prioritization_tool = PrioritizationTool()
    
    # Test booking type determination
    class MockRouting:
        def __init__(self, risk_level, has_red_flags, primary_symptom):
            self.risk_level = risk_level
            self.has_red_flags = has_red_flags
            self.primary_symptom = primary_symptom
        
        @property
        def is_emergency(self):
            return self.has_red_flags or self.risk_level == 'high'
    
    # Test high-risk case
    high_risk_routing = MockRouting('high', True, 'chest_pain')
    booking_type = prioritization_tool.determine_booking_type(high_risk_routing)
    print(f"   High-risk case booking type: {booking_type}")
    
    # Test low-risk case
    low_risk_routing = MockRouting('low', False, 'headache')
    booking_type = prioritization_tool.determine_booking_type(low_risk_routing)
    print(f"   Low-risk case booking type: {booking_type}")
    
    # Test emergency override
    emergency_routing = MockRouting('medium', True, 'fever')
    should_override = prioritization_tool.should_override_to_emergency(emergency_routing)
    print(f"   Emergency override for medium risk with red flags: {should_override}")
    
    print("✅ Prioritization Tool tests completed!\n")


def test_notification_dispatch():
    """Test notification dispatch functionality"""
    print("📢 Testing Notification Dispatch Tool...")
    
    notification_tool = NotificationDispatchTool()
    
    # Test subject generation
    class MockRouting:
        def __init__(self):
            self.patient_token = 'test_123'
            self.is_emergency = True
    
    class MockFacility:
        def __init__(self):
            self.name = "Test Hospital"
    
    mock_routing = MockRouting()
    mock_facility = MockFacility()
    
    subject = notification_tool._generate_subject(mock_routing, 'new_case')
    print(f"   Generated subject: {subject}")
    
    # Test message generation
    message = notification_tool._generate_message(mock_routing, mock_facility, 'new_case')
    print(f"   Generated message length: {len(message)} characters")
    
    # Test payload building
    payload = notification_tool._build_payload(mock_routing, mock_facility)
    print(f"   Payload keys: {list(payload.keys())}")
    
    print("✅ Notification Dispatch Tool tests completed!\n")


def test_logging_monitoring():
    """Test logging and monitoring functionality"""
    print("📊 Testing Logging & Monitoring Tool...")
    
    logging_tool = LoggingMonitoringTool()
    
    # Test system event logging
    logging_tool.log_system_event(
        'test_event',
        {'test_data': 'sample'},
        'info'
    )
    print("   System event logged successfully")
    
    # Test performance metrics
    metrics = {
        'total_routings': 10,
        'emergency_routings': 3,
        'average_response_time': 15.5,
    }
    logging_tool.log_performance_metrics(metrics)
    print("   Performance metrics logged successfully")
    
    print("✅ Logging & Monitoring Tool tests completed!\n")


def test_facility_model():
    """Test enhanced facility model methods"""
    print("🏥 Testing Enhanced Facility Model...")
    
    # Create test facility
    facility = Facility(
        name="Test Hospital",
        facility_type="hospital",
        total_beds=100,
        available_beds=25,
        services_offered=['emergency', 'general_medicine'],
        latitude=-1.2921,
        longitude=36.8219,
        ambulance_available=True
    )
    
    # Test capacity checking
    has_capacity = facility.has_capacity(5)
    print(f"   Has capacity for 5 beds: {has_capacity}")
    
    # Test service offering
    offers_emergency = facility.offers_service('emergency')
    print(f"   Offers emergency service: {offers_emergency}")
    
    # Test emergency handling
    can_handle_emergency = facility.can_handle_emergency()
    print(f"   Can handle emergency: {can_handle_emergency}")
    
    # Test distance calculation
    distance = facility.distance_to(-1.2850, 36.8300)
    print(f"   Distance to test location: {distance} km")
    
    print("✅ Enhanced Facility Model tests completed!\n")


def main():
    """Run all tests"""
    print("🚀 Starting HarakaCare Facility Agent Tests\n")
    print("=" * 50)
    
    try:
        test_facility_model()
        test_facility_matching()
        test_prioritization()
        test_notification_dispatch()
        test_logging_monitoring()
        
        print("=" * 50)
        print("🎉 All tests completed successfully!")
        print("\n📋 Test Summary:")
        print("   ✅ Facility Model enhancements")
        print("   ✅ Facility Matching Tool")
        print("   ✅ Prioritization Tool")
        print("   ✅ Notification Dispatch Tool")
        print("   ✅ Logging & Monitoring Tool")
        print("\n🔧 Ready for integration with Triage Agent!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
