"""
Create sample facilities and test data for API demonstration
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'harakacare.settings.development')
django.setup()

from apps.facilities.models import Facility


def create_sample_facilities():
    """Create sample facilities for testing"""
    
    facilities_data = [
        {
            'name': 'Nairobi General Hospital',
            'facility_type': 'hospital',
            'address': 'Nairobi, Kenya',
            'phone_number': '+254-20-1234567',
            'latitude': -1.2921,
            'longitude': 36.8219,
            'total_beds': 100,
            'available_beds': 25,
            'staff_count': 50,
            'services_offered': ['emergency', 'general_medicine', 'cardiology', 'pediatrics'],
            'average_wait_time_minutes': 30,
            'ambulance_available': True,
            'notification_endpoint': 'https://nairobi-hospital.example.com/api/notifications',
            'is_active': True
        },
        {
            'name': 'Westlands Medical Center',
            'facility_type': 'clinic',
            'address': 'Westlands, Nairobi',
            'phone_number': '+254-20-7654321',
            'latitude': -1.2655,
            'longitude': 36.7955,
            'total_beds': 20,
            'available_beds': 8,
            'staff_count': 15,
            'services_offered': ['general_medicine', 'pediatrics'],
            'average_wait_time_minutes': 45,
            'ambulance_available': False,
            'notification_endpoint': '',
            'is_active': True
        },
        {
            'name': 'Kenya Medical Center',
            'facility_type': 'hospital',
            'address': 'Upper Hill, Nairobi',
            'phone_number': '+254-20-9876543',
            'latitude': -1.3000,
            'longitude': 36.8000,
            'total_beds': 80,
            'available_beds': 12,
            'staff_count': 40,
            'services_offered': ['emergency', 'general_medicine', 'surgery', 'obstetrics'],
            'average_wait_time_minutes': 60,
            'ambulance_available': True,
            'notification_endpoint': 'https://kenya-medical.example.com/api/webhook',
            'is_active': True
        },
        {
            'name': 'Mombasa Emergency Clinic',
            'facility_type': 'urgent_care',
            'address': 'Mombasa, Kenya',
            'phone_number': '+254-41-1234567',
            'latitude': -4.0435,
            'longitude': 39.6682,
            'total_beds': 15,
            'available_beds': 3,
            'staff_count': 10,
            'services_offered': ['emergency', 'general_medicine'],
            'average_wait_time_minutes': 20,
            'ambulance_available': True,
            'notification_endpoint': '',
            'is_active': True
        }
    ]
    
    created_facilities = []
    
    for facility_data in facilities_data:
        # Check if facility already exists
        existing = Facility.objects.filter(name=facility_data['name']).first()
        if existing:
            print(f"📝 Facility '{facility_data['name']}' already exists, updating...")
            for key, value in facility_data.items():
                setattr(existing, key, value)
            existing.save()
            created_facilities.append(existing)
        else:
            print(f"➕ Creating facility '{facility_data['name']}'...")
            facility = Facility.objects.create(**facility_data)
            created_facilities.append(facility)
    
    print(f"\n✅ Created/Updated {len(created_facilities)} facilities")
    
    # Display created facilities
    print("\n📋 Sample Facilities Created:")
    for facility in created_facilities:
        print(f"   🏥 {facility.name}")
        print(f"      Type: {facility.get_facility_type_display()}")
        print(f"      Beds: {facility.available_beds}/{facility.total_beds}")
        print(f"      Services: {', '.join(facility.services_offered)}")
        print(f"      Emergency: {'Yes' if facility.can_handle_emergency() else 'No'}")
        print()
    
    return created_facilities


def test_facility_apis():
    """Test facility API endpoints"""
    import requests
    import json
    
    BASE_URL = "http://127.0.0.1:8000"
    
    print("🔍 Testing Facility API Endpoints...")
    print("=" * 50)
    
    # Test 1: Get all facilities
    print("\n1️⃣ GET All Facilities:")
    try:
        response = requests.get(f"{BASE_URL}/api/facilities/facilities/", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            facilities = response.json()
            print(f"   ✅ Found {len(facilities)} facilities")
            for facility in facilities[:2]:  # Show first 2
                print(f"      🏥 {facility['name']} - {facility['facility_type']}")
        else:
            print(f"   ❌ Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Exception: {str(e)}")
    
    # Test 2: Get specific facility
    print("\n2️⃣ GET Specific Facility:")
    try:
        response = requests.get(f"{BASE_URL}/api/facilities/facilities/1/", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            facility = response.json()
            print(f"   ✅ Facility: {facility['name']}")
            print(f"      📍 Location: {facility['address']}")
            print(f"      🛏️  Beds: {facility['available_beds']}/{facility['total_beds']}")
        else:
            print(f"   ❌ Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Exception: {str(e)}")
    
    # Test 3: Search facilities
    print("\n3️⃣ Search Facilities:")
    try:
        response = requests.get(f"{BASE_URL}/api/facilities/facilities/?search=Nairobi", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            facilities = response.json()
            print(f"   ✅ Found {len(facilities)} facilities in Nairobi")
            for facility in facilities:
                print(f"      🏥 {facility['name']}")
        else:
            print(f"   ❌ Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Exception: {str(e)}")
    
    # Test 4: Filter by facility type
    print("\n4️⃣ Filter by Facility Type:")
    try:
        response = requests.get(f"{BASE_URL}/api/facilities/facilities/?facility_type=hospital", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            facilities = response.json()
            print(f"   ✅ Found {len(facilities)} hospitals")
            for facility in facilities:
                print(f"      🏥 {facility['name']} - {facility['available_beds']} beds available")
        else:
            print(f"   ❌ Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Exception: {str(e)}")


def demonstrate_facility_agent_workflow():
    """Demonstrate the complete Facility Agent workflow"""
    print("\n🚀 Facility Agent Workflow Demonstration")
    print("=" * 50)
    
    # Simulate triage data
    triage_data = {
        "patient_token": "demo_patient_12345",
        "risk_level": "high",
        "primary_symptom": "chest_pain",
        "secondary_symptoms": ["difficulty_breathing", "dizziness"],
        "has_red_flags": True,
        "chronic_conditions": ["hypertension"],
        "patient_district": "Nairobi",
        "patient_location_lat": -1.2921,
        "patient_location_lng": 36.8219
    }
    
    print("📥 Step 1: Triage Data Received")
    print(f"   Patient Token: {triage_data['patient_token']}")
    print(f"   Risk Level: {triage_data['risk_level']}")
    print(f"   Primary Symptom: {triage_data['primary_symptom']}")
    print(f"   Red Flags: {triage_data['has_red_flags']}")
    print(f"   Location: {triage_data['patient_district']}")
    
    # Step 2: Facility Matching
    print("\n🔍 Step 2: Facility Matching")
    facilities = Facility.objects.filter(is_active=True)
    
    candidates = []
    for facility in facilities:
        # Calculate distance
        distance = facility.distance_to(triage_data['patient_location_lat'], triage_data['patient_location_lng'])
        
        # Calculate match score
        distance_score = 1.0 if distance and distance <= 5 else 0.8 if distance and distance <= 10 else 0.4
        capacity_score = 1.0 if facility.available_beds and facility.available_beds > 10 else 0.7 if facility.available_beds and facility.available_beds > 5 else 0.4
        service_score = 1.0 if facility.offers_service('emergency') else 0.5
        emergency_score = 1.0 if facility.can_handle_emergency() else 0.0
        
        match_score = (distance_score * 0.3 + capacity_score * 0.25 + service_score * 0.25 + emergency_score * 0.2)
        
        candidates.append({
            'facility': facility,
            'match_score': match_score,
            'distance_km': distance,
            'has_capacity': facility.has_capacity(),
            'offers_required_service': facility.offers_service('emergency'),
            'can_handle_emergency': facility.can_handle_emergency()
        })
    
    # Sort by match score
    candidates.sort(key=lambda x: x['match_score'], reverse=True)
    
    print(f"   Found {len(candidates)} candidate facilities:")
    for i, candidate in enumerate(candidates[:3], 1):
        facility = candidate['facility']
        print(f"   {i}. {facility.name}")
        print(f"      📍 Distance: {candidate['distance_km']} km")
        print(f"      📊 Match Score: {candidate['match_score']:.3f}")
        print(f"      🛏️  Capacity: {candidate['has_capacity']}")
        print(f"      🚑 Emergency: {candidate['can_handle_emergency']}")
    
    # Step 3: Prioritization
    print("\n🎯 Step 3: Prioritization & Booking Decision")
    
    # Determine booking type
    booking_type = "automatic" if triage_data['risk_level'] == 'high' or triage_data['has_red_flags'] else "manual"
    print(f"   Booking Type: {booking_type.upper()}")
    
    # Select best facility
    if candidates:
        best_candidate = candidates[0]
        selected_facility = best_candidate['facility']
        print(f"   Selected Facility: {selected_facility.name}")
        print(f"   Match Score: {best_candidate['match_score']:.3f}")
        print(f"   Distance: {best_candidate['distance_km']} km")
        
        # Step 4: Notification Simulation
        print("\n📢 Step 4: Facility Notification")
        print(f"   ✅ Notification sent to {selected_facility.name}")
        print(f"   📧 Subject: URGENT: New Patient Case - {triage_data['patient_token'][:8]}")
        print(f"   ⏰ Expected Response: 30 minutes (emergency case)")
        
        # Step 5: Facility Response Simulation
        print("\n🏥 Step 5: Facility Response")
        print(f"   ✅ {selected_facility.name} ACCEPTED the case")
        print(f"   🛏️  Bed Reserved: 1 bed in Emergency Department")
        print(f"   ⏰ Estimated Arrival: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        # Step 6: Follow-up Notification
        print("\n📱 Step 6: Follow-up Agent Notification")
        print(f"   ✅ Follow-up Agent notified of successful routing")
        print(f"   🎯 Priority: HIGH")
        print(f"   📊 Status: CONFIRMED")
        
        print(f"\n🎉 Patient {triage_data['patient_token'][:8]} successfully routed to {selected_facility.name}!")
    else:
        print("   ❌ No suitable facilities found")


def main():
    """Main function to run all demonstrations"""
    print("🚀 HarakaCare Facility Agent - API Demonstration")
    print("=" * 60)
    
    # Create sample data
    create_sample_facilities()
    
    # Test API endpoints
    test_facility_apis()
    
    # Demonstrate workflow
    demonstrate_facility_agent_workflow()
    
    print("\n" + "=" * 60)
    print("🎉 API Demonstration Complete!")
    print("\n📋 What You Can Do:")
    print("   🌐 Visit: http://127.0.0.1:8000/admin/ to manage facilities")
    print("   🔍 API: http://127.0.0.1:8000/api/facilities/facilities/ to list facilities")
    print("   📊 Monitor: Check server logs for routing activity")
    print("   🚀 Test: Use the API to integrate with Triage Agent")


if __name__ == "__main__":
    main()
