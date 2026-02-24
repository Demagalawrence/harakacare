"""
Prioritization Tool
Orders candidate facilities based on urgency and availability
Implements hybrid booking model: automatic for high-risk, manual for low/medium-risk
Based on: HarakaCare Facility Agent Data Requirements - Tool 4.3
"""

from typing import List, Dict, Tuple
from datetime import datetime, timedelta
from django.db.models import Q
from ..models import (
    Facility, FacilityCandidate, FacilityRouting
)


class PrioritizationTool:
    """
    Tool for prioritizing facility assignments based on clinical urgency
    Implements the hybrid booking model with automatic/manual routing
    """

    def __init__(self):
        self.priority_weights = {
            'emergency': 1000,
            'high_risk': 500,
            'medium_risk': 100,
            'low_risk': 10,
        }

    def prioritize_candidates(self, candidates: List[FacilityCandidate], routing: FacilityRouting) -> List[FacilityCandidate]:
        """
        Prioritize facility candidates based on multiple factors
        
        Args:
            candidates: List of facility candidates
            routing: Patient case routing information
            
        Returns:
            Prioritized list of candidates
        """
        # Calculate priority scores for each candidate
        scored_candidates = []
        for candidate in candidates:
            priority_score = self._calculate_priority_score(candidate, routing)
            candidate.priority_score = priority_score
            scored_candidates.append(candidate)
        
        # Sort by priority score (highest first)
        scored_candidates.sort(key=lambda x: x.priority_score, reverse=True)
        return scored_candidates

    def _calculate_priority_score(self, candidate: FacilityCandidate, routing: FacilityRouting) -> float:
        """
        Calculate comprehensive priority score for a facility candidate
        
        Args:
            candidate: FacilityCandidate to score
            routing: Patient case routing
            
        Returns:
            Priority score (higher = more priority)
        """
        score = 0.0
        
        # 1. Base clinical urgency score
        urgency_score = self._get_urgency_score(routing)
        score += urgency_score
        
        # 2. Facility capability score
        capability_score = self._get_capability_score(candidate, routing)
        score += capability_score
        
        # 3. Availability score
        availability_score = self._get_availability_score(candidate)
        score += availability_score
        
        # 4. Distance penalty (closer is better)
        distance_penalty = self._get_distance_penalty(candidate)
        score -= distance_penalty
        
        # 5. Wait time penalty
        wait_penalty = self._get_wait_time_penalty(candidate)
        score -= wait_penalty
        
        return max(score, 0.0)

    def _get_urgency_score(self, routing: FacilityRouting) -> float:
        """Get base urgency score based on risk level and red flags"""
        base_score = self.priority_weights.get(f'{routing.risk_level}_risk', 0)
        
        # Boost for red flags
        if routing.has_red_flags:
            base_score += 200
        
        # Additional boost for specific emergency symptoms
        emergency_symptoms = ['chest_pain', 'difficulty_breathing', 'injury_trauma']
        if routing.primary_symptom in emergency_symptoms:
            base_score += 300
        
        return base_score

    def _get_capability_score(self, candidate: FacilityCandidate, routing: FacilityRouting) -> float:
        """Score based on facility capabilities"""
        score = 0.0
        
        facility = candidate.facility
        
        # Emergency capability bonus
        if routing.is_emergency and candidate.can_handle_emergency:
            score += 150
        elif routing.is_emergency and not candidate.can_handle_emergency:
            score -= 500  # Heavy penalty for emergency cases
        
        # Service match bonus
        if candidate.offers_required_service:
            score += 100
        else:
            score -= 200
        
        # Facility type bonus
        facility_type_bonus = {
            'hospital': 50,
            'urgent_care': 40,
            'specialty_center': 30,
            'clinic': 20,
            'diagnostic_center': 10,
        }
        score += facility_type_bonus.get(facility.facility_type, 0)
        
        # Staff availability bonus
        if facility.staff_count and facility.staff_count > 5:
            score += 30
        elif facility.staff_count and facility.staff_count > 2:
            score += 15
        
        return score

    def _get_availability_score(self, candidate: FacilityCandidate) -> float:
        """Score based on facility availability"""
        score = 0.0
        facility = candidate.facility
        
        if candidate.has_capacity:
            # Bed availability ratio
            if facility.available_beds and facility.total_beds:
                bed_ratio = facility.available_beds / facility.total_beds
                if bed_ratio > 0.5:
                    score += 50
                elif bed_ratio > 0.2:
                    score += 30
                else:
                    score += 10
            else:
                score += 25  # Neutral score if capacity unknown
        else:
            score -= 300  # Heavy penalty for no capacity
        
        # Ambulance availability bonus
        if facility.ambulance_available:
            score += 20
        
        return score

    def _get_distance_penalty(self, candidate: FacilityCandidate) -> float:
        """Calculate distance penalty (further = higher penalty)"""
        if not candidate.distance_km:
            return 10  # Small penalty for unknown distance
        
        if candidate.distance_km <= 5:
            return 0
        elif candidate.distance_km <= 10:
            return 5
        elif candidate.distance_km <= 20:
            return 15
        elif candidate.distance_km <= 50:
            return 30
        else:
            return 50

    def _get_wait_time_penalty(self, candidate: FacilityCandidate) -> float:
        """Calculate wait time penalty"""
        facility = candidate.facility
        
        if not facility.average_wait_time_minutes:
            return 5  # Small penalty for unknown wait time
        
        wait_time = facility.average_wait_time_minutes
        
        if wait_time <= 30:
            return 0
        elif wait_time <= 60:
            return 10
        elif wait_time <= 120:
            return 25
        else:
            return 40

    def determine_booking_type(self, routing: FacilityRouting) -> str:
        """
        Determine if booking should be automatic or manual
        
        Args:
            routing: Patient case routing
            
        Returns:
            'automatic' or 'manual'
        """
        # Automatic booking for high-risk and emergency cases
        if routing.risk_level == 'high' or routing.has_red_flags:
            return 'automatic'
        
        # Automatic for specific emergency symptoms
        emergency_symptoms = ['chest_pain', 'difficulty_breathing', 'injury_trauma']
        if routing.primary_symptom in emergency_symptoms:
            return 'automatic'
        
        # Manual confirmation for medium and low risk cases
        return 'manual'

    def get_top_candidates(self, candidates: List[FacilityCandidate], routing: FacilityRouting, max_count: int = 3) -> List[FacilityCandidate]:
        """
        Get top N candidates for a routing
        
        Args:
            candidates: List of facility candidates
            routing: Patient case routing
            max_count: Maximum number of candidates to return
            
        Returns:
            Top prioritized candidates
        """
        prioritized = self.prioritize_candidates(candidates, routing)
        return prioritized[:max_count]

    def should_override_to_emergency(self, routing: FacilityRouting) -> bool:
        """
        Check if case should be treated as emergency regardless of risk level
        
        Args:
            routing: Patient case routing
            
        Returns:
            True if should be treated as emergency
        """
        emergency_indicators = [
            routing.has_red_flags,
            routing.primary_symptom in ['chest_pain', 'difficulty_breathing', 'injury_trauma'],
            'loss_of_consciousness' in routing.secondary_symptoms,
            'convulsions' in routing.secondary_symptoms,
            'severe_bleeding' in routing.secondary_symptoms,
        ]
        
        return any(emergency_indicators)

    def get_emergency_facilities(self, routing: FacilityRouting, max_distance_km: float = 30.0) -> List[Facility]:
        """
        Get facilities that can handle emergency cases
        
        Args:
            routing: Patient case routing
            max_distance_km: Maximum distance for emergency facilities
            
        Returns:
            List of emergency-capable facilities
        """
        return Facility.objects.filter(
            is_active=True,
            services_offered__contains='emergency',
            available_beds__gt=0
        ).filter(
            latitude__isnull=False,
            longitude__isnull=False
        ).annotate(
            distance_km=self._calculate_distance_annotation(routing.patient_location_lat, routing.patient_location_lng)
        ).filter(
            distance_km__lte=max_distance_km
        ).order_by('distance_km')

    def _calculate_distance_annotation(self, lat: float, lng: float):
        """
        Create distance calculation annotation for database query
        Note: This is a simplified version - in production, use proper GIS functions
        """
        # This would typically use PostGIS functions like ST_Distance
        # For now, return a placeholder that would be implemented with proper GIS
        from django.db.models import Value
        return Value(0.0, output_field=FloatField())

    def prioritize_for_capacity_update(self, facilities: List[Facility]) -> List[Facility]:
        """
        Prioritize facilities for capacity updates based on current load
        
        Args:
            facilities: List of facilities to prioritize
            
        Returns:
            Prioritized list of facilities
        """
        scored_facilities = []
        
        for facility in facilities:
            score = 0.0
            
            # Priority for facilities with low bed availability
            if facility.available_beds and facility.total_beds:
                bed_ratio = facility.available_beds / facility.total_beds
                if bed_ratio < 0.2:
                    score += 100
                elif bed_ratio < 0.5:
                    score += 50
            
            # Priority for high-traffic facilities
            if facility.average_wait_time_minutes and facility.average_wait_time_minutes > 60:
                score += 30
            
            # Priority for emergency facilities
            if facility.offers_service('emergency'):
                score += 20
            
            facility.priority_score = score
            scored_facilities.append(facility)
        
        scored_facilities.sort(key=lambda x: x.priority_score, reverse=True)
        return scored_facilities

    def get_booking_recommendation(self, routing: FacilityRouting, candidates: List[FacilityCandidate]) -> Dict:
        """
        Get booking recommendation with reasoning
        
        Args:
            routing: Patient case routing
            candidates: List of facility candidates
            
        Returns:
            Booking recommendation dictionary
        """
        if not candidates:
            return {
                'recommendation': 'no_facilities',
                'reason': 'No suitable facilities found',
                'action': 'escalate_to_manual_review'
            }
        
        prioritized = self.prioritize_candidates(candidates, routing)
        top_candidate = prioritized[0]
        booking_type = self.determine_booking_type(routing)
        
        recommendation = {
            'booking_type': booking_type,
            'recommended_facility': top_candidate.facility,
            'priority_score': top_candidate.priority_score,
            'match_score': top_candidate.match_score,
            'distance_km': top_candidate.distance_km,
            'estimated_wait_time': top_candidate.facility.average_wait_time_minutes,
            'reason': self._generate_recommendation_reason(routing, top_candidate, booking_type),
            'alternative_facilities': [
                {
                    'facility': c.facility,
                    'priority_score': c.priority_score,
                    'match_score': c.match_score,
                    'distance_km': c.distance_km,
                }
                for c in prioritized[1:3]
            ]
        }
        
        return recommendation

    def _generate_recommendation_reason(self, routing: FacilityRouting, candidate: FacilityCandidate, booking_type: str) -> str:
        """Generate human-readable reason for facility recommendation"""
        reasons = []
        
        # Clinical urgency reasons
        if routing.is_emergency:
            reasons.append("Emergency case requiring immediate attention")
        elif routing.risk_level == 'high':
            reasons.append("High-risk case requiring prompt care")
        elif routing.risk_level == 'medium':
            reasons.append("Medium-risk case requiring timely evaluation")
        else:
            reasons.append("Low-risk case suitable for routine care")
        
        # Facility capability reasons
        if candidate.can_handle_emergency:
            reasons.append("Facility equipped for emergency care")
        
        if candidate.has_capacity:
            reasons.append("Facility has available capacity")
        
        if candidate.distance_km and candidate.distance_km <= 10:
            reasons.append("Close to patient location")
        
        # Booking type reason
        if booking_type == 'automatic':
            reasons.append("Automatic booking due to clinical urgency")
        else:
            reasons.append("Manual confirmation required for safety")
        
        return " | ".join(reasons)
