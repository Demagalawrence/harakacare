"""
Triage API Serializers
Serializers for triage REST API endpoints
"""

from rest_framework import serializers
from apps.triage.models import (
    TriageSession,
    SymptomAssessment,
    RedFlagDetection,
    RiskClassification,
    ClinicalContext,
    TriageDecision
)


class TriageIntakeSerializer(serializers.Serializer):
    """
    Serializer for triage intake data submission
    Validates all required fields per data requirements doc
    """

    # Demographic Context (3.2)
    age_range = serializers.ChoiceField(
        choices=['under_5', '5_12', '13_17', '18_30', '31_50', '51_plus'],
        required=True
    )
    sex = serializers.ChoiceField(
        choices=['male', 'female', 'prefer_not_to_say'],
        required=False,
        allow_null=True
    )

    # Location Data (3.3)
    district = serializers.CharField(max_length=100, required=True)
    subcounty = serializers.CharField(max_length=100, required=False, allow_blank=True)
    device_location_lat = serializers.FloatField(required=False, allow_null=True)
    device_location_lng = serializers.FloatField(required=False, allow_null=True)
    location_consent = serializers.BooleanField(default=False)

    # Primary Symptom (3.4)
    primary_symptom = serializers.ChoiceField(
        choices=[
            'fever', 'headache', 'chest_pain', 'difficulty_breathing',
            'abdominal_pain', 'vomiting', 'diarrhea', 'injury_trauma',
            'skin_problem', 'other'
        ],
        required=True
    )

    # Secondary Symptoms (3.5)
    secondary_symptoms = serializers.ListField(
        child=serializers.ChoiceField(
            choices=[
                'cough', 'fatigue', 'dizziness', 'nausea', 'body_weakness',
                'swelling', 'bleeding', 'loss_of_appetite', 'none'
            ]
        ),
        required=False,
        default=list
    )

    # Symptom Severity (3.6)
    symptom_severity = serializers.ChoiceField(
        choices=['mild', 'moderate', 'severe', 'very_severe'],
        required=True
    )

    # Symptom Duration (3.7)
    symptom_duration = serializers.ChoiceField(
        choices=['today', '1_3_days', '4_7_days', 'more_than_1_week', 'more_than_1_month'],
        required=True
    )

    # Symptom Pattern (3.8)
    symptom_pattern = serializers.ChoiceField(
        choices=['getting_better', 'staying_same', 'getting_worse', 'comes_and_goes'],
        required=False,
        allow_null=True
    )

    # Previous Condition (3.10)
    condition_occurrence = serializers.ChoiceField(
        choices=['first_occurrence', 'happened_before', 'long_term'],
        required=True
    )

    # Chronic Conditions (3.11)
    chronic_conditions = serializers.ListField(
        child=serializers.ChoiceField(
            choices=[
                'hypertension', 'diabetes', 'asthma', 'heart_disease',
                'epilepsy', 'sickle_cell', 'other_chronic', 'none', 'prefer_not_to_say'
            ]
        ),
        required=False,
        default=list
    )

    # Current Medication (3.12)
    current_medication = serializers.ChoiceField(
        choices=['yes', 'no', 'not_sure'],
        required=False,
        allow_null=True
    )

    # Allergies (3.13)
    has_allergies = serializers.ChoiceField(
        choices=['yes', 'no', 'not_sure'],
        required=False,
        allow_null=True
    )
    allergy_types = serializers.ListField(
        child=serializers.ChoiceField(choices=['medication', 'food', 'environmental']),
        required=False,
        default=list
    )

    # Pregnancy Status (3.14)
    pregnancy_status = serializers.ChoiceField(
        choices=['yes', 'no', 'not_applicable', 'prefer_not_to_say'],
        required=False,
        allow_null=True
    )

    # Additional Description (3.15)
    additional_description = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True
    )

    # Consent (3.16)
    consent_medical_triage = serializers.BooleanField(required=True)
    consent_data_sharing = serializers.BooleanField(required=True)
    consent_follow_up = serializers.BooleanField(required=True)

    # Channel
    channel = serializers.ChoiceField(
        choices=['ussd', 'sms', 'whatsapp', 'web', 'mobile_app'],
        default='web'
    )

    def validate(self, data):
        """
        Object-level validation
        """
        # All consents must be True
        if not data.get('consent_medical_triage'):
            raise serializers.ValidationError(
                "Consent for medical triage is required"
            )
        if not data.get('consent_data_sharing'):
            raise serializers.ValidationError(
                "Consent for data sharing is required"
            )
        if not data.get('consent_follow_up'):
            raise serializers.ValidationError(
                "Consent for follow-up is required"
            )

        # Pregnancy validation
        if data.get('sex') == 'male' and data.get('pregnancy_status') == 'yes':
            raise serializers.ValidationError(
                "Invalid pregnancy status for male patient"
            )

        # Location validation
        if data.get('location_consent'):
            if not (data.get('device_location_lat') and data.get('device_location_lng')):
                raise serializers.ValidationError(
                    "Location coordinates required when location consent is given"
                )

        return data


class TriageSessionSerializer(serializers.ModelSerializer):
    """
    Full triage session serializer for responses
    """

    symptom_summary = serializers.SerializerMethodField()
    is_emergency = serializers.BooleanField(read_only=True)
    needs_immediate_attention = serializers.BooleanField(read_only=True)

    class Meta:
        model = TriageSession
        fields = [
            'id',
            'patient_token',
            'session_status',
            'age_range',
            'sex',
            'district',
            'subcounty',
            'primary_symptom',
            'secondary_symptoms',
            'symptom_severity',
            'symptom_duration',
            'symptom_pattern',
            'has_red_flags',
            'red_flags',
            'risk_level',
            'risk_confidence',
            'follow_up_priority',
            'symptom_summary',
            'is_emergency',
            'needs_immediate_attention',
            'assessment_completed_at',
            'created_at',
            'channel'
        ]
        read_only_fields = [
            'id',
            'patient_token',
            'has_red_flags',
            'red_flags',
            'risk_level',
            'risk_confidence',
            'follow_up_priority',
            'assessment_completed_at',
            'created_at'
        ]

    def get_symptom_summary(self, obj):
        return obj.generate_symptom_summary()


class TriageResultSerializer(serializers.Serializer):
    """
    Triage result returned to patient
    """

    patient_token = serializers.CharField()
    risk_level = serializers.CharField()
    risk_confidence = serializers.FloatField()
    follow_up_priority = serializers.CharField()

    # Red flags
    has_red_flags = serializers.BooleanField()
    red_flags = serializers.ListField(child=serializers.CharField())
    emergency_message = serializers.CharField(allow_blank=True)

    # Recommendations
    recommended_action = serializers.CharField()
    recommended_facility_type = serializers.CharField()
    recommended_facilities = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )

    # Symptom summary
    symptom_summary = serializers.CharField()

    # Disclaimers
    disclaimers = serializers.ListField(child=serializers.CharField())

    # Timing
    assessment_completed_at = serializers.DateTimeField()

    # Follow-up
    follow_up_required = serializers.BooleanField()
    follow_up_timeframe = serializers.CharField()


class RedFlagDetectionSerializer(serializers.ModelSerializer):
    """
    Red flag detection results
    """

    class Meta:
        model = RedFlagDetection
        fields = [
            'difficulty_breathing',
            'chest_pain',
            'loss_of_consciousness',
            'convulsions',
            'severe_bleeding',
            'confusion',
            'high_fever_unresponsive',
            'emergency_override',
            'detection_method',
            'detected_flags_count'
        ]


class RiskClassificationSerializer(serializers.ModelSerializer):
    """
    AI risk classification results
    """

    class Meta:
        model = RiskClassification
        fields = [
            'raw_risk_score',
            'ai_risk_level',
            'confidence_score',
            'model_name',
            'model_version',
            'inference_time_ms'
        ]


class TriageDecisionSerializer(serializers.ModelSerializer):
    """
    Final triage decision
    """

    class Meta:
        model = TriageDecision
        fields = [
            'final_risk_level',
            'follow_up_priority',
            'decision_basis',
            'recommended_action',
            'facility_type_recommendation',
            'decision_timestamp',
            'decision_reasoning',
            'disclaimers'
        ]


class TriageStatusSerializer(serializers.Serializer):
    """
    Triage session status check
    """

    patient_token = serializers.CharField()
    session_status = serializers.CharField()
    risk_level = serializers.CharField(allow_null=True)
    has_red_flags = serializers.BooleanField()
    assessment_completed = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    assessment_completed_at = serializers.DateTimeField(allow_null=True)