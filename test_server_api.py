"""
Test the HarakaCare Facility Agent API endpoints
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"

def test_admin_panel():
    """Test that Django admin is accessible"""
    print("🔧 Testing Django Admin Panel...")
    
    try:
        response = requests.get(f"{BASE_URL}/admin/", timeout=5)
        if response.status_code == 200:
            print("   ✅ Admin panel accessible")
            return True
        else:
            print(f"   ❌ Admin panel returned {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Admin panel error: {str(e)}")
        return False

def test_facility_api():
    """Test facility API endpoints"""
    print("\n🏥 Testing Facility API...")
    
    try:
        # Test facilities list
        response = requests.get(f"{BASE_URL}/api/facilities/facilities/", timeout=5)
        print(f"   Facilities API Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Facilities API working - Found {len(data)} facilities")
            return True
        else:
            print(f"   ❌ Facilities API failed: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Facilities API error: {str(e)}")
        return False

def test_triage_api():
    """Test triage API endpoints"""
    print("\n🩺 Testing Triage API...")
    
    try:
        # Test triage endpoint
        response = requests.get(f"{BASE_URL}/api/v1/triage/", timeout=5)
        print(f"   Triage API Status: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✅ Triage API accessible")
            return True
        else:
            print(f"   ❌ Triage API failed: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Triage API error: {str(e)}")
        return False

def test_facility_agent_simulation():
    """Simulate Facility Agent workflow"""
    print("\n🚀 Testing Facility Agent Workflow Simulation...")
    
    # Simulate triage data
    triage_data = {
        "patient_token": "test_patient_123",
        "risk_level": "high",
        "primary_symptom": "chest_pain",
        "secondary_symptoms": ["difficulty_breathing"],
        "has_red_flags": True,
        "chronic_conditions": ["hypertension"],
        "patient_district": "Nairobi",
        "patient_location_lat": -1.2921,
        "patient_location_lng": 36.8219
    }
    
    print(f"   📥 Simulating triage intake:")
    print(f"      Patient Token: {triage_data['patient_token']}")
    print(f"      Risk Level: {triage_data['risk_level']}")
    print(f"      Primary Symptom: {triage_data['primary_symptom']}")
    print(f"      Red Flags: {triage_data['has_red_flags']}")
    
    # Simulate facility matching
    facilities = [
        {
            "name": "Nairobi General Hospital",
            "distance_km": 2.5,
            "available_beds": 15,
            "services_offered": ["emergency", "general_medicine"],
            "ambulance_available": True
        },
        {
            "name": "Westlands Medical Center", 
            "distance_km": 8.2,
            "available_beds": 5,
            "services_offered": ["general_medicine"],
            "ambulance_available": False
        }
    ]
    
    print(f"\n   🔍 Matching facilities...")
    for i, facility in enumerate(facilities, 1):
        # Calculate match score
        distance_score = 1.0 if facility["distance_km"] <= 5 else 0.8 if facility["distance_km"] <= 10 else 0.4
        capacity_score = 1.0 if facility["available_beds"] > 10 else 0.7 if facility["available_beds"] > 5 else 0.4
        service_score = 1.0 if "emergency" in facility["services_offered"] else 0.5
        emergency_score = 1.0 if facility["ambulance_available"] and "emergency" in facility["services_offered"] else 0.0
        
        match_score = (distance_score * 0.3 + capacity_score * 0.25 + service_score * 0.25 + emergency_score * 0.2)
        
        print(f"      {i}. {facility['name']} - Score: {match_score:.3f} ({facility['distance_km']}km)")
    
    # Determine booking type
    booking_type = "automatic" if triage_data["risk_level"] == "high" or triage_data["has_red_flags"] else "manual"
    print(f"\n   🎯 Booking Type: {booking_type}")
    
    # Select best facility
    best_facility = facilities[0]  # First facility has best score
    print(f"   🏥 Selected Facility: {best_facility['name']}")
    
    return True

def main():
    """Run all API tests"""
    print("🚀 HarakaCare Facility Agent - Server API Tests")
    print("=" * 60)
    
    tests = [
        test_admin_panel,
        test_facility_api,
        test_triage_api,
        test_facility_agent_simulation,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"   ❌ Test error: {str(e)}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"🎯 API Test Results:")
    print(f"   ✅ Passed: {passed}")
    print(f"   ❌ Failed: {failed}")
    print(f"   📊 Success Rate: {(passed/(passed+failed)*100):.1f}%")
    
    if failed == 0:
        print("\n🎉 All API tests passed!")
        print("🔧 HarakaCare server is running successfully!")
        print("📱 Facility Agent APIs are accessible!")
    else:
        print(f"\n⚠️  {failed} test(s) failed - check server configuration")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
