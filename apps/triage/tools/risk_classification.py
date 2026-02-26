"""
Tool 4: Risk Classification Tool (AI-powered) - UPDATED
Enhanced for complaint-based, age-adaptive triage
Placeholder - To be fully implemented with HuggingFace in Phase 2
Now includes complaint group analysis and age-specific risk factors
"""

from typing import Dict, Any, List, Optional
import time
import math


class RiskClassificationTool:
    """
    AI-powered risk classification using HuggingFace models - UPDATED
    Currently uses enhanced rule-based logic until ML model is integrated
    Includes complaint group analysis and age-specific risk factors
    """

    def __init__(self):
        self.model_name = "enhanced-rule-based-v2"
        self.model_version = "2.0.0"

        # ====================================================================
        # Risk weights by complaint group (base risk)
        # ====================================================================
        self.COMPLAINT_BASE_RISK = {
            # High-risk complaint groups
            'chest_pain': 0.7,
            'breathing': 0.65,
            'bleeding': 0.7,
            'headache': 0.4,  # Can be high if severe
            'pregnancy': 0.5,
            
            # Medium-risk complaint groups
            'abdominal': 0.4,
            'fever': 0.35,
            'injury': 0.3,
            'mental_health': 0.3,
            
            # Lower-risk complaint groups
            'skin': 0.2,
            'feeding': 0.25,
            'other': 0.2,
        }

        # ====================================================================
        # Age-specific risk multipliers
        # ====================================================================
        self.AGE_RISK_MULTIPLIERS = {
            'newborn': 1.8,      # Newborns are very high risk
            'infant': 1.6,       # Infants high risk
            'child_1_5': 1.3,    # Young children elevated risk
            'child_6_12': 1.0,   # Baseline
            'teen': 1.0,          # Baseline
            'adult': 1.0,         # Baseline
            'elderly': 1.5,       # Elderly elevated risk
        }

        # ====================================================================
        # Severity weights
        # ====================================================================
        self.SEVERITY_WEIGHTS = {
            'mild': 0.0,
            'moderate': 0.2,
            'severe': 0.4,
            'very_severe': 0.6,
        }

        # ====================================================================
        # Duration weights
        # ====================================================================
        self.DURATION_WEIGHTS = {
            'less_than_1_hour': 0.0,
            '1_6_hours': 0.0,
            '6_24_hours': 0.1,
            '1_3_days': 0.15,
            '4_7_days': 0.2,
            'more_than_1_week': 0.3,
            'more_than_1_month': 0.35,
        }

        # ====================================================================
        # Progression weights
        # ====================================================================
        self.PROGRESSION_WEIGHTS = {
            'sudden': 0.15,
            'getting_worse': 0.25,
            'staying_same': 0.0,
            'getting_better': -0.1,
            'comes_and_goes': 0.05,
        }

        # ====================================================================
        # High-risk symptom indicators (from adaptive questions)
        # ====================================================================
        self.HIGH_RISK_INDICATORS = {
            # Respiratory
            'breathing_difficulty': 0.4,
            'chest_indrawing': 0.5,
            'fast_breathing': 0.3,
            'stridor': 0.6,
            
            # Neurological
            'confusion': 0.4,
            'weakness_one_side': 0.5,
            'slurred_speech': 0.5,
            
            # Cardiovascular
            'chest_pressure': 0.5,
            'pale': 0.3,
            'cold_extremities': 0.4,
            
            # General
            'unable_to_drink': 0.4,
            'lethargic': 0.4,
            'severe_pain': 0.3,
        }

    def classify(self, session, triage_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify risk level using AI (currently enhanced rule-based)

        Args:
            session: TriageSession instance
            triage_data: Validated triage data

        Returns:
            Risk classification results
        """
        start_time = time.time()

        # Enhanced rule-based risk assessment
        risk_score = self._calculate_enhanced_risk(session, triage_data)

        # Convert score to risk level with confidence
        risk_level, confidence = self._score_to_risk_level(risk_score)

        inference_time = int((time.time() - start_time) * 1000)

        # Get feature importance based on contributing factors
        feature_importance = self._get_feature_importance(session, triage_data)

        # Get complaint embedding (placeholder for ML model)
        complaint_embedding = self._get_complaint_embedding(session, triage_data)

        return {
            'raw_score': risk_score,
            'risk_level': risk_level,
            'confidence': confidence,
            'model_name': self.model_name,
            'model_version': self.model_version,
            'inference_time_ms': inference_time,
            'feature_importance': feature_importance,
            'complaint_embedding': complaint_embedding,
            'contributing_factors': self._get_contributing_factors(session, triage_data)
        }

    def _calculate_enhanced_risk(self, session, data: Dict[str, Any]) -> float:
        """
        Calculate risk score using enhanced rules
        Incorporates: complaint group, age, indicators, severity, duration
        """
        
        # ====================================================================
        # Get data from session and input
        # ====================================================================
        complaint_group = data.get('complaint_group') or getattr(session, 'complaint_group', 'other')
        age_group = data.get('age_group') or getattr(session, 'age_group', 'adult')
        severity = data.get('symptom_severity') or getattr(session, 'symptom_severity', None)
        duration = data.get('symptom_duration') or getattr(session, 'symptom_duration', None)
        progression = data.get('progression_status') or getattr(session, 'progression_status', None)
        
        # Get symptom indicators
        symptom_indicators = getattr(session, 'symptom_indicators', {}) or {}
        if 'symptom_indicators' in data:
            symptom_indicators.update(data['symptom_indicators'])
        
        # Get risk modifiers
        risk_modifiers = getattr(session, 'risk_modifiers', {}) or {}
        if 'risk_modifiers' in data:
            risk_modifiers.update(data['risk_modifiers'])

        # ====================================================================
        # Base risk from complaint group
        # ====================================================================
        base_risk = self.COMPLAINT_BASE_RISK.get(complaint_group, 0.2)
        score = base_risk

        # ====================================================================
        # Apply age multiplier
        # ====================================================================
        age_multiplier = self.AGE_RISK_MULTIPLIERS.get(age_group, 1.0)
        score = score * age_multiplier

        # ====================================================================
        # Add severity contribution
        # ====================================================================
        if severity:
            score += self.SEVERITY_WEIGHTS.get(severity, 0.0)

        # ====================================================================
        # Add duration contribution
        # ====================================================================
        if duration:
            score += self.DURATION_WEIGHTS.get(duration, 0.0)

        # ====================================================================
        # Add progression contribution
        # ====================================================================
        if progression:
            score += self.PROGRESSION_WEIGHTS.get(progression, 0.0)

        # ====================================================================
        # Add contributions from high-risk symptom indicators
        # ====================================================================
        for indicator, weight in self.HIGH_RISK_INDICATORS.items():
            if symptom_indicators.get(indicator, False):
                score += weight
                
                # Additional boost for certain combinations
                if indicator == 'breathing_difficulty' and symptom_indicators.get('chest_indrawing', False):
                    score += 0.2  # Respiratory distress combo
                
                if indicator == 'confusion' and age_group in ['elderly']:
                    score += 0.2  # Confusion in elderly is very significant

        # ====================================================================
        # Add contributions from risk modifiers
        # ====================================================================
        
        # Pregnancy increases risk
        pregnancy_status = data.get('pregnancy_status') or getattr(session, 'pregnancy_status', None)
        if pregnancy_status in ['yes', 'possible']:
            score += 0.2
        
        # Chronic conditions increase risk
        if risk_modifiers.get('has_chronic_conditions', False):
            score += 0.15
            
            # Specific chronic conditions add more risk
            if risk_modifiers.get('chronic_conditions'):
                chronic_list = risk_modifiers.get('chronic_conditions', [])
                if 'asthma' in chronic_list and complaint_group == 'breathing':
                    score += 0.2
                if 'heart_disease' in chronic_list and complaint_group == 'chest_pain':
                    score += 0.3
                if 'diabetes' in chronic_list:
                    score += 0.1  # General risk increase for diabetics
        
        # Immunocompromised increases risk
        if risk_modifiers.get('is_immunocompromised', False):
            score += 0.25
        
        # On medication - could indicate existing condition
        if data.get('on_medication', False):
            score += 0.05

        # ====================================================================
        # Complaint-specific risk adjustments
        # ====================================================================
        
        # Headache with neurological symptoms
        if complaint_group == 'headache':
            if symptom_indicators.get('weakness_one_side', False) or symptom_indicators.get('slurred_speech', False):
                score += 0.4  # Possible stroke
        
        # Abdominal pain with certain indicators
        if complaint_group == 'abdominal':
            if symptom_indicators.get('severe_pain', False):
                score += 0.2
            if symptom_indicators.get('vomiting_all', False):
                score += 0.3
        
        # Fever in young children
        if complaint_group == 'fever' and age_group in ['newborn', 'infant']:
            score += 0.3

        # ====================================================================
        # Normalize score to 0-1 range
        # ====================================================================
        # Apply sigmoid-like normalization to keep in range
        score = min(score, 1.0)  # Cap at 1.0
        
        # Ensure minimum floor
        score = max(score, 0.05)

        return score

    def _score_to_risk_level(self, score: float) -> tuple:
        """
        Convert risk score to risk level with confidence
        
        Returns:
            (risk_level, confidence)
        """
        if score >= 0.7:
            risk_level = 'high'
            # Higher confidence for high scores
            confidence = min(0.85 + (score - 0.7) * 0.5, 0.95)
        elif score >= 0.4:
            risk_level = 'medium'
            # Medium confidence for borderline cases
            confidence = 0.75 + (abs(score - 0.55) * 0.3)
        else:
            risk_level = 'low'
            # Good confidence for low scores
            confidence = 0.8 + (0.4 - score) * 0.3
        
        return risk_level, min(confidence, 0.95)  # Cap at 0.95

    def _get_feature_importance(self, session, data: Dict[str, Any]) -> Dict[str, float]:
        """Get feature importance scores based on actual contributions"""
        
        importance = {
            'complaint_group': 0.25,
            'age_group': 0.20,
            'symptom_severity': 0.15,
            'symptom_indicators': 0.15,
            'symptom_duration': 0.10,
            'progression_status': 0.05,
            'risk_modifiers': 0.10,
        }
        
        # Adjust based on what data is actually present
        if not data.get('symptom_duration') and not getattr(session, 'symptom_duration', None):
            importance['symptom_duration'] = 0
            # Redistribute
            importance['complaint_group'] += 0.05
            importance['age_group'] += 0.05
        
        if not data.get('progression_status') and not getattr(session, 'progression_status', None):
            importance['progression_status'] = 0
            importance['symptom_severity'] += 0.05
        
        return importance

    def _get_complaint_embedding(self, session, data: Dict[str, Any]) -> Optional[List[float]]:
        """
        Get complaint text embedding (placeholder for ML model)
        Returns dummy embedding for now
        """
        complaint_text = data.get('complaint_text') or getattr(session, 'complaint_text', '')
        
        if not complaint_text:
            return None
        
        # Dummy embedding (would be replaced by actual model)
        # Return a fixed-size vector representing complaint group
        complaint_group = data.get('complaint_group') or getattr(session, 'complaint_group', 'other')
        
        # Map complaint group to a simple embedding
        embedding_map = {
            'fever': [0.1, 0.2, 0.1, 0.1, 0.5],
            'breathing': [0.3, 0.1, 0.2, 0.3, 0.1],
            'injury': [0.4, 0.1, 0.3, 0.1, 0.1],
            'abdominal': [0.2, 0.3, 0.1, 0.2, 0.2],
            'headache': [0.2, 0.2, 0.3, 0.2, 0.1],
            'chest_pain': [0.3, 0.2, 0.2, 0.2, 0.1],
            'pregnancy': [0.1, 0.4, 0.1, 0.3, 0.1],
            'skin': [0.1, 0.1, 0.5, 0.2, 0.1],
            'feeding': [0.1, 0.5, 0.1, 0.2, 0.1],
            'bleeding': [0.3, 0.2, 0.2, 0.2, 0.1],
            'mental_health': [0.1, 0.1, 0.1, 0.6, 0.1],
            'other': [0.2, 0.2, 0.2, 0.2, 0.2],
        }
        
        return embedding_map.get(complaint_group, [0.2, 0.2, 0.2, 0.2, 0.2])

    def _get_contributing_factors(self, session, data: Dict[str, Any]) -> List[str]:
        """Get list of factors that contributed to risk score"""
        factors = []
        
        complaint_group = data.get('complaint_group') or getattr(session, 'complaint_group', 'other')
        age_group = data.get('age_group') or getattr(session, 'age_group', 'adult')
        severity = data.get('symptom_severity') or getattr(session, 'symptom_severity', None)
        
        # Complaint group factor
        if complaint_group in ['chest_pain', 'breathing', 'bleeding']:
            factors.append(f"High-risk complaint: {complaint_group}")
        
        # Age factor
        if age_group in ['newborn', 'infant', 'elderly']:
            factors.append(f"Age-related risk: {age_group}")
        
        # Severity factor
        if severity in ['severe', 'very_severe']:
            factors.append(f"Symptom severity: {severity}")
        
        # Duration factor
        duration = data.get('symptom_duration') or getattr(session, 'symptom_duration', None)
        if duration in ['more_than_1_week', 'more_than_1_month']:
            factors.append("Prolonged symptoms")
        
        # Progression factor
        progression = data.get('progression_status') or getattr(session, 'progression_status', None)
        if progression == 'getting_worse':
            factors.append("Symptoms getting worse")
        
        # Symptom indicators
        symptom_indicators = getattr(session, 'symptom_indicators', {}) or {}
        if 'symptom_indicators' in data:
            symptom_indicators.update(data['symptom_indicators'])
        
        high_risk_indicators = []
        for indicator in ['breathing_difficulty', 'chest_indrawing', 'confusion', 'severe_pain']:
            if symptom_indicators.get(indicator, False):
                high_risk_indicators.append(indicator.replace('_', ' '))
        
        if high_risk_indicators:
            factors.append(f"High-risk indicators: {', '.join(high_risk_indicators)}")
        
        return factors


class MLRiskClassifier:
    """
    Placeholder for actual ML model integration (Phase 2)
    This will be implemented with HuggingFace models
    """
    
    def __init__(self, model_name: str = "clinical-bert-triage"):
        self.model_name = model_name
        self.model_version = "2.0.0"
        self.is_loaded = False
    
    def load_model(self):
        """Load the ML model (placeholder)"""
        # In Phase 2: from transformers import AutoModelForSequenceClassification
        self.is_loaded = True
    
    def predict(self, session, triage_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make prediction using ML model
        This is a placeholder for future implementation
        """
        # This would be replaced with actual model inference
        tool = RiskClassificationTool()
        return tool.classify(session, triage_data)


# Convenience function for external use
def classify_risk(session, triage_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Classify risk level
    
    Args:
        session: TriageSession instance
        triage_data: Validated triage data

    Returns:
        Risk classification results
    """
    tool = RiskClassificationTool()
    return tool.classify(session, triage_data)