"""
Facility Matching Tool
Matches patient cases to appropriate facilities based on location, capacity, and services
Based on: HarakaCare Facility Agent Data Requirements - Tool 4.2
"""

from typing import List, Dict, Tuple, Optional
from django.db.models import Q, F, FloatField
from django.db.models.functions import Cast
from ..models import (
    Facility, FacilityCandidate, FacilityRouting
)


class FacilityMatchingTool:
    """
    Tool for matching patient cases to suitable healthcare facilities
    Uses hybrid approach: rule-based logic with optional AI enhancement
    """

    def __init__(self):
        self.service_weights = {
            'emergency': 1.0,
            'general_medicine': 0.8,
            'obstetrics': 0.9,
            'pediatrics': 0.9,
            'surgery': 0.9,
            'mental_health': 0.7,
            'diagnostics': 0.6,
            'pharmacy': 0.5,
        }

    def find_candidate_facilities(self, routing: FacilityRouting, max_candidates: int = 10) -> List[FacilityCandidate]:
        """
        Find candidate facilities for a patient case
        
        Args:
            routing: FacilityRouting instance with patient case data
            max_candidates: Maximum number of candidates to return
            
        Returns:
            List of FacilityCandidate objects sorted by match score
        """
        # Base facility query
        facilities = Facility.objects.filter(is_active=True)
        
        # Filter by location (same district first, then nearby)
        district_facilities = facilities.filter(address__icontains=routing.patient_district)
        nearby_facilities = self._find_nearby_facilities(routing, exclude=district_facilities)
        
        # Combine results
        all_facilities = (district_facilities | nearby_facilities).distinct()
        
        # Score and rank facilities
        candidates = []
        for facility in all_facilities[:max_candidates * 2]:  # Get more to filter
            score_data = self._calculate_match_score(facility, routing)
            if score_data['score'] > 0.1:  # Minimum threshold
                candidate = FacilityCandidate(
                    routing=routing,
                    facility=facility,
                    match_score=score_data['score'],
                    distance_km=score_data['distance'],
                    has_capacity=score_data['has_capacity'],
                    offers_required_service=score_data['offers_service'],
                    can_handle_emergency=score_data['can_handle_emergency'],
                    selection_reason=score_data['reason']
                )
                candidates.append(candidate)
        
        # Sort by score and return top candidates
        candidates.sort(key=lambda x: x.match_score, reverse=True)
        return candidates[:max_candidates]

    def _find_nearby_facilities(self, routing: FacilityRouting, max_distance_km: float = 50.0, exclude=None) -> List[Facility]:
        """
        Find facilities within maximum distance of patient location
        
        Args:
            routing: FacilityRouting with patient location
            max_distance_km: Maximum distance in kilometers
            exclude: Facilities to exclude from search
            
        Returns:
            List of nearby facilities
        """
        if not routing.patient_location_lat or not routing.patient_location_lng:
            return Facility.objects.none()
        
        facilities = Facility.objects.filter(is_active=True)
        
        if exclude:
            facilities = facilities.exclude(id__in=exclude.values_list('id', flat=True))
        
        # Filter by coordinates (simplified bounding box)
        lat_delta = max_distance_km / 111.0  # Approximate km per degree latitude
        lng_delta = max_distance_km / (111.0 * abs(routing.patient_location_lat))
        
        facilities = facilities.filter(
            latitude__isnull=False,
            longitude__isnull=False,
            latitude__range=(
                routing.patient_location_lat - lat_delta,
                routing.patient_location_lat + lat_delta
            ),
            longitude__range=(
                routing.patient_location_lng - lng_delta,
                routing.patient_location_lng + lng_delta
            )
        )
        
        return facilities

    def _calculate_match_score(self, facility: Facility, routing: FacilityRouting) -> Dict:
        """
        Calculate match score for facility-patient pairing
        
        Args:
            facility: Facility to score
            routing: Patient case routing
            
        Returns:
            Dictionary with score and breakdown
        """
        score = 0.0
        factors = []
        
        # 1. Distance score (0-0.3)
        distance = facility.distance_to(routing.patient_location_lat, routing.patient_location_lng)
        distance_score = self._calculate_distance_score(distance)
        score += distance_score * 0.3
        factors.append(f"Distance: {distance_score:.2f}")
        
        # 2. Capacity score (0-0.25)
        capacity_score = self._calculate_capacity_score(facility, routing)
        score += capacity_score * 0.25
        factors.append(f"Capacity: {capacity_score:.2f}")
        
        # 3. Service match score (0-0.25)
        service_score = self._calculate_service_score(facility, routing)
        score += service_score * 0.25
        factors.append(f"Services: {service_score:.2f}")
        
        # 4. Facility type score (0-0.1)
        type_score = self._calculate_facility_type_score(facility, routing)
        score += type_score * 0.1
        factors.append(f"Type: {type_score:.2f}")
        
        # 5. Emergency capability score (0-0.1)
        emergency_score = self._calculate_emergency_score(facility, routing)
        score += emergency_score * 0.1
        factors.append(f"Emergency: {emergency_score:.2f}")
        
        # Determine if facility can handle the case
        has_capacity = facility.has_capacity()
        offers_service = self._offers_required_services(facility, routing)
        can_handle_emergency = facility.can_handle_emergency() if routing.is_emergency else True
        
        # Apply penalties for missing requirements
        if not has_capacity:
            score *= 0.3
        if not offers_service:
            score *= 0.5
        if routing.is_emergency and not can_handle_emergency:
            score *= 0.1
        
        reason = f"Score: {score:.2f} | " + " | ".join(factors)
        
        return {
            'score': min(score, 1.0),  # Cap at 1.0
            'distance': distance,
            'has_capacity': has_capacity,
            'offers_service': offers_service,
            'can_handle_emergency': can_handle_emergency,
            'reason': reason
        }

    def _calculate_distance_score(self, distance_km: Optional[float]) -> float:
        """Calculate distance-based score (closer is better)"""
        if distance_km is None:
            return 0.5  # Neutral score if distance unknown
        
        if distance_km <= 5:
            return 1.0
        elif distance_km <= 10:
            return 0.8
        elif distance_km <= 20:
            return 0.6
        elif distance_km <= 50:
            return 0.4
        else:
            return 0.2

    def _calculate_capacity_score(self, facility: Facility, routing: FacilityRouting) -> float:
        """Calculate capacity-based score"""
        if facility.available_beds is None:
            return 0.7  # Neutral score if capacity unknown
        
        bed_ratio = facility.available_beds / max(facility.total_beds, 1)
        
        if bed_ratio >= 0.5:
            return 1.0
        elif bed_ratio >= 0.3:
            return 0.8
        elif bed_ratio >= 0.1:
            return 0.6
        else:
            return 0.3

    def _calculate_service_score(self, facility: Facility, routing: FacilityRouting) -> float:
        """Calculate service match score"""
        required_services = self._get_required_services(routing)
        if not required_services:
            return 0.8  # Neutral score if no specific requirements
        
        offered_services = facility.services_offered or []
        matches = sum(1 for service in required_services if service in offered_services)
        
        if matches == len(required_services):
            return 1.0
        elif matches >= len(required_services) * 0.7:
            return 0.8
        elif matches >= len(required_services) * 0.5:
            return 0.6
        else:
            return 0.3

    def _calculate_facility_type_score(self, facility: Facility, routing: FacilityRouting) -> float:
        """Calculate facility type preference score"""
        type_scores = {
            'hospital': 1.0,
            'urgent_care': 0.9,
            'clinic': 0.7,
            'specialty_center': 0.8,
            'diagnostic_center': 0.5,
            'pharmacy': 0.3,
            'laboratory': 0.3,
        }
        
        base_score = type_scores.get(facility.facility_type, 0.5)
        
        # Boost for emergency cases
        if routing.is_emergency:
            if facility.facility_type in ['hospital', 'urgent_care']:
                base_score = min(base_score * 1.2, 1.0)
        
        return base_score

    def _calculate_emergency_score(self, facility: Facility, routing: FacilityRouting) -> float:
        """Calculate emergency handling score"""
        if not routing.is_emergency:
            return 0.8  # Neutral score for non-emergency cases
        
        if facility.offers_service('emergency') and facility.has_capacity():
            return 1.0
        elif facility.offers_service('emergency'):
            return 0.6
        else:
            return 0.2

    def _get_required_services(self, routing: FacilityRouting) -> List[str]:
        """Determine required services based on symptoms and conditions"""
        services = ['general_medicine']  # Default requirement
        
        # Map symptoms to services
        symptom_service_map = {
            'chest_pain': ['emergency', 'general_medicine'],
            'difficulty_breathing': ['emergency', 'general_medicine'],
            'abdominal_pain': ['general_medicine', 'surgery'],
            'injury_trauma': ['emergency', 'surgery'],
            'fever': ['general_medicine'],
            'headache': ['general_medicine'],
            'vomiting': ['general_medicine'],
            'diarrhea': ['general_medicine'],
            'skin_problem': ['general_medicine', 'diagnostics'],
        }
        
        primary_service = symptom_service_map.get(routing.primary_symptom, ['general_medicine'])
        services.extend(primary_service)
        
        # Add services for chronic conditions
        chronic_service_map = {
            'diabetes': ['general_medicine'],
            'hypertension': ['general_medicine'],
            'asthma': ['general_medicine'],
            'heart_disease': ['general_medicine', 'emergency'],
            'pregnancy': ['obstetrics'],
            'mental_health': ['mental_health'],
        }
        
        for condition in routing.chronic_conditions:
            condition_services = chronic_service_map.get(condition, [])
            services.extend(condition_services)
        
        return list(set(services))

    def _offers_required_services(self, facility: Facility, routing: FacilityRouting) -> bool:
        """Check if facility offers required services"""
        required_services = self._get_required_services(routing)
        offered_services = facility.services_offered or []
        
        return any(service in offered_services for service in required_services)

    def get_best_match(self, routing: FacilityRouting) -> Optional[FacilityCandidate]:
        """
        Get the single best facility match for a routing
        
        Args:
            routing: FacilityRouting instance
            
        Returns:
            Best FacilityCandidate or None if no suitable facility found
        """
        candidates = self.find_candidate_facilities(routing, max_candidates=1)
        return candidates[0] if candidates else None

    def validate_facility_match(self, facility: Facility, routing: FacilityRouting) -> Dict:
        """
        Validate if a facility can handle a specific case
        
        Args:
            facility: Facility to validate
            routing: Patient case routing
            
        Returns:
            Validation result with reasons
        """
        issues = []
        warnings = []
        
        # Check capacity
        if not facility.has_capacity():
            issues.append("No available beds")
        
        # Check services
        if not self._offers_required_services(facility, routing):
            issues.append("Does not offer required services")
        
        # Check emergency capability
        if routing.is_emergency and not facility.can_handle_emergency():
            issues.append("Cannot handle emergency cases")
        
        # Check distance
        distance = facility.distance_to(routing.patient_location_lat, routing.patient_location_lng)
        if distance and distance > 50:
            warnings.append(f"Far from patient location ({distance}km)")
        
        # Check wait time
        if facility.average_wait_time_minutes and facility.average_wait_time_minutes > 120:
            warnings.append(f"Long wait time ({facility.average_wait_time_minutes} minutes)")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'distance_km': distance
        }
