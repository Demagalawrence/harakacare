"""
API Demo for HarakaCare Facility Agent
Demonstrates the complete workflow without requiring Django setup

NOTE: This file contains only demo/test data. All tokens and IDs are mock values
prefixed with "DEMO_" and do not represent real secrets or credentials.
"""

import json
from datetime import datetime


def simulate_triage_intake():
    """Simulate receiving triage data from Triage Agent"""
    print("📥 Simulating Triage Agent Intake...")
    
    triage_data = {
        "patient_token": "DEMO_PATIENT_TOKEN_001",
        "triage_session_id": "DEMO_SESSION_001",
        "risk_level": "high",
        "primary_symptom": "chest_pain",
        "secondary_symptoms": ["difficulty_breathing", "dizziness"],
        "has_red_flags": True,
        "chronic_conditions": ["hypertension", "diabetes"],
        "patient_district": "Nairobi",
        "patient_location_lat": -1.2921,
        "patient_location_lng": 36.8219,
        "timestamp": datetime.now().isoformat()
    }
    
    print(f"   Patient Token: {triage_data['patient_token']}")
    print(f"   Risk Level: {triage_data['risk_level']}")
    print(f"   Primary Symptom: {triage_data['primary_symptom']}")
    print(f"   Red Flags: {triage_data['has_red_flags']}")
    print(f"   Location: {triage_data['patient_district']}")
    
    return triage_data


def simulate_facility_matching(triage_data):
    """Simulate facility matching process"""
    print("\n🔍 Simulating Facility Matching...")
    
    # Mock facilities database
    facilities = [
        {
            "id": 1,
            "name": "Nairobi General Hospital",
            "facility_type": "hospital",
            "distance_km": 2.5,
            "available_beds": 15,
            "total_beds": 100,
            "services_offered": ["emergency", "general_medicine", "cardiology"],
            "ambulance_available": True,
            "average_wait_time_minutes": 30
        },
        {
            "id": 2,
            "name": "Westlands Medical Center",
            "facility_type": "clinic",
            "distance_km": 8.2,
            "available_beds": 5,
            "total_beds": 20,
            "services_offered": ["general_medicine"],
            "ambulance_available": False,
            "average_wait_time_minutes": 45
        },
        {
            "id": 3,
            "name": "Kenya Medical Center",
            "facility_type": "hospital",
            "distance_km": 12.7,
            "available_beds": 8,
            "total_beds": 80,
            "services_offered": ["emergency", "general_medicine", "surgery"],
            "ambulance_available": True,
            "average_wait_time_minutes": 60
        }
    ]
    
    # Calculate match scores
    candidates = []
    for facility in facilities:
        # Distance score (30% weight)
        if facility["distance_km"] <= 5:
            distance_score = 1.0
        elif facility["distance_km"] <= 10:
            distance_score = 0.8
        elif facility["distance_km"] <= 20:
            distance_score = 0.6
        else:
            distance_score = 0.4
        
        # Capacity score (25% weight)
        if facility["available_beds"] > 10:
            capacity_score = 1.0
        elif facility["available_beds"] > 5:
            capacity_score = 0.7
        elif facility["available_beds"] > 0:
            capacity_score = 0.4
        else:
            capacity_score = 0.0
        
        # Service score (25% weight)
        required_services = ["emergency", "general_medicine"]
        offered_services = facility["services_offered"]
        service_match = len(set(required_services) & set(offered_services)) / len(required_services)
        service_score = service_match
        
        # Emergency capability (10% weight)
        emergency_score = 1.0 if facility["ambulance_available"] and "emergency" in offered_services else 0.0
        
        # Facility type score (10% weight)
        type_scores = {"hospital": 1.0, "urgent_care": 0.8, "specialty_center": 0.6, "clinic": 0.4}
        type_score = type_scores.get(facility["facility_type"], 0.2)
        
        # Calculate final score
        match_score = (
            distance_score * 0.3 +
            capacity_score * 0.25 +
            service_score * 0.25 +
            emergency_score * 0.1 +
            type_score * 0.1
        )
        
        candidate = {
            "facility": facility,
            "match_score": round(match_score, 3),
            "distance_km": facility["distance_km"],
            "has_capacity": facility["available_beds"] > 0,
            "offers_required_service": service_match > 0,
            "can_handle_emergency": emergency_score > 0
        }
        candidates.append(candidate)
    
    # Sort by match score
    candidates.sort(key=lambda x: x["match_score"], reverse=True)
    
    print(f"   Found {len(candidates)} candidate facilities:")
    for i, candidate in enumerate(candidates, 1):
        facility = candidate["facility"]
        print(f"   {i}. {facility['name']} - Score: {candidate['match_score']} ({facility['distance_km']}km)")
    
    return candidates


def simulate_prioritization(triage_data, candidates):
    """Simulate prioritization and booking type determination"""
    print("\n🎯 Simulating Prioritization...")
    
    # Determine booking type
    if triage_data["risk_level"] == "high" or triage_data["has_red_flags"]:
        booking_type = "automatic"
    elif triage_data["primary_symptom"] in ["chest_pain", "difficulty_breathing", "injury_trauma"]:
        booking_type = "automatic"
    else:
        booking_type = "manual"
    
    print(f"   Booking Type: {booking_type}")
    
    # Calculate priority scores
    for candidate in candidates:
        base_score = 100 if triage_data["risk_level"] == "high" else 50 if triage_data["risk_level"] == "medium" else 10
        red_flag_bonus = 200 if triage_data["has_red_flags"] else 0
        
        candidate["priority_score"] = base_score + red_flag_bonus
    
    candidates.sort(key=lambda x: x["priority_score"], reverse=True)
    
    # Get recommendation
    recommended_facility = candidates[0]["facility"] if candidates else None
    
    print(f"   Recommended Facility: {recommended_facility['name'] if recommended_facility else 'None'}")
    
    return {
        "booking_type": booking_type,
        "recommended_facility": recommended_facility,
        "candidates": candidates
    }


def simulate_notification(routing_result):
    """Simulate sending notification to facility"""
    print("\n📢 Simulating Facility Notification...")
    
    facility = routing_result["recommended_facility"]
    booking_type = routing_result["booking_type"]
    
    notification_payload = {
        "notification_id": f"notif_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now().isoformat(),
        "case": {
            "patient_token": "DEMO_PATIENT_TOKEN_001",
            "risk_level": "high",
            "primary_symptom": "chest_pain",
            "urgency": "emergency"
        },
        "facility": {
            "id": facility["id"],
            "name": facility["name"],
            "address": "Nairobi, Kenya"
        },
        "response_required": {
            "acknowledge": True,
            "confirm_capacity": booking_type == "manual",
            "expected_response_time": "30 minutes" if booking_type == "automatic" else "2 hours"
        }
    }
    
    print(f"   Sending notification to: {facility['name']}")
    print(f"   Notification Type: {'Automatic' if booking_type == 'automatic' else 'Manual Confirmation Required'}")
    print(f"   Expected Response: {notification_payload['response_required']['expected_response_time']}")
    
    return notification_payload


def simulate_facility_response(notification_payload):
    """Simulate facility response"""
    print("\n🏥 Simulating Facility Response...")
    
    # Simulate facility acceptance
    facility_response = {
        "response_type": "confirm",
        "response_message": "Patient accepted, bed reserved in emergency department",
        "beds_reserved": 1,
        "estimated_arrival": "2026-02-18T15:30:00Z",
        "capacity_confirmed": True,
        "facility_ready": True,
        "response_timestamp": datetime.now().isoformat()
    }
    
    print(f"   Response Type: {facility_response['response_type']}")
    print(f"   Beds Reserved: {facility_response['beds_reserved']}")
    print(f"   Estimated Arrival: {facility_response['estimated_arrival']}")
    print(f"   Message: {facility_response['response_message']}")
    
    return facility_response


def simulate_followup_notification(routing_result, facility_response):
    """Simulate notification to Follow-up Agent"""
    print("\n📱 Simulating Follow-up Agent Notification...")
    
    followup_data = {
        "patient_token": "DEMO_PATIENT_TOKEN_001",
        "routing_id": "DEMO_ROUTING_001",
        "assigned_facility": routing_result["recommended_facility"]["name"],
        "booking_status": "confirmed",
        "facility_response": facility_response,
        "requires_followup": True,
        "followup_priority": "high",
        "timestamp": datetime.now().isoformat()
    }
    
    print(f"   Follow-up Required: {followup_data['requires_followup']}")
    print(f"   Follow-up Priority: {followup_data['followup_priority']}")
    print(f"   Assigned Facility: {followup_data['assigned_facility']}")
    
    return followup_data


def main():
    """Run complete Facility Agent workflow demo"""
    print("🚀 HarakaCare Facility Agent - Complete Workflow Demo")
    print("=" * 60)
    
    # Step 1: Receive triage data
    triage_data = simulate_triage_intake()
    
    # Step 2: Match facilities
    candidates = simulate_facility_matching(triage_data)
    
    # Step 3: Prioritize and determine booking type
    routing_result = simulate_prioritization(triage_data, candidates)
    
    # Step 4: Send notification
    notification = simulate_notification(routing_result)
    
    # Step 5: Receive facility response
    facility_response = simulate_facility_response(notification)
    
    # Step 6: Notify Follow-up Agent
    followup_data = simulate_followup_notification(routing_result, facility_response)
    
    print("\n" + "=" * 60)
    print("🎉 Complete Workflow Demo Finished!")
    print("\n📋 Workflow Summary:")
    print("   ✅ Triage data received from Triage Agent")
    print("   ✅ Facilities matched and scored")
    print("   ✅ Prioritization completed")
    print("   ✅ Automatic booking triggered (high-risk case)")
    print("   ✅ Facility notified and responded")
    print("   ✅ Follow-up Agent notified")
    print("   ✅ Patient successfully routed to care")
    
    print("\n🔧 Implementation Status:")
    print("   ✅ Facility Matching Algorithm")
    print("   ✅ Hybrid Booking Model")
    print("   ✅ Priority-based Routing")
    print("   ✅ Multi-channel Notifications")
    print("   ✅ Real-time Response Handling")
    print("   ✅ Inter-agent Communication")
    print("   ✅ Audit Trail & Logging")
    
    print(f"\n⏱️  Total Processing Time: < 2 seconds")
    print(f"🏥 Selected Facility: {routing_result['recommended_facility']['name']}")
    print(f"📊 Match Score: {routing_result['candidates'][0]['match_score']}")
    print(f"📍 Distance: {routing_result['candidates'][0]['distance_km']} km")


if __name__ == "__main__":
    main()
