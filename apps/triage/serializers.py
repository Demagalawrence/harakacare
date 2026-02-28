"""
Triage API Serializers
Serializers for triage REST API endpoints
UPDATED FOR COMPLAINT-BASED, AGE-ADAPTIVE TRIAGE
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
    Serializer for triage intake data submission - UPDATED
    Now handles complaint-based intake with age-adaptive fields
    """

    # ========================================================================
    # COMPLAINT-BASED INTAKE (NEW)
    # ========================================================================
    
    complaint_text = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Original user message: 'Tell me what is happening'"
    )
    
    complaint_group = serializers.ChoiceField(
        choices=[
            ('fever', 'Fever / feeling hot'),
            ('breathing', 'Breathing or cough problem'),
            ('injury', 'Injury or accident'),
            ('abdominal', 'Abdominal pain / vomiting / diarrhea'),
            ('headache', 'Headache / confusion / weakness'),
            ('chest_pain', 'Chest pain'),
            ('pregnancy', 'Pregnancy concern'),
            ('skin', 'Skin problem'),
            ('feeding', 'Feeding problem / general weakness'),
            ('bleeding', 'Bleeding / blood loss'),
            ('mental_health', 'Mental health / emotional crisis'),
            ('other', 'Other'),
        ],
        required=False,
        allow_null=True,
        help_text="AI-classified complaint group (NOT a diagnosis)"
    )

    # ========================================================================
    # MANDATORY DEMOGRAPHIC CONTEXT (UPDATED)
    # ========================================================================
    
    age_group = serializers.ChoiceField(
        choices=[
            ('newborn', 'Newborn (0-2 months)'),
            ('infant', 'Infant (2-12 months)'),
            ('child_1_5', 'Child (1-5 years)'),
            ('child_6_12', 'Child (6-12 years)'),
            ('teen', 'Teen (13-17 years)'),
            ('adult', 'Adult (18-64 years)'),
            ('elderly', 'Elderly (65+ years)'),
        ],
        required=True,
        help_text="Age group - determines question tree and risk modifiers"
    )
    
    sex = serializers.ChoiceField(
        choices=[
            ('male', 'Male'),
            ('female', 'Female'),
            ('other', 'Other / Prefer not to say'),
        ],
        required=True,
        help_text="Biological sex - required for pregnancy screening"
    )

    patient_relation = serializers.ChoiceField(
        choices=[
            ('self', 'For myself'),
            ('child', 'For my child'),
            ('family', 'For family member'),
            ('other', 'For someone else'),
        ],
        default='self',
        required=False,
        help_text="Who is the patient?"
    )

    # ========================================================================
    # LOCATION DATA (3.3) - Mostly unchanged
    # ========================================================================
    
    district = serializers.CharField(max_length=100, required=True)
    subcounty = serializers.CharField(max_length=100, required=False, allow_blank=True)
    village = serializers.CharField(max_length=100, required=False, allow_blank=True, 
                                   help_text="Village or LC1")
    device_location_lat = serializers.FloatField(required=False, allow_null=True)
    device_location_lng = serializers.FloatField(required=False, allow_null=True)
    location_consent = serializers.BooleanField(default=False)

    # ========================================================================
    # STRUCTURED SYMPTOM INDICATORS (NEW)
    # ========================================================================
    
    symptom_indicators = serializers.JSONField(
        required=False,
        default=dict,
        help_text="Structured answers from adaptive questions"
    )

    # Symptom Severity (UPDATED)
    symptom_severity = serializers.ChoiceField(
        choices=[
            ('mild', 'Mild - can do normal activities'),
            ('moderate', 'Moderate - some difficulty with activities'),
            ('severe', 'Severe - unable to do normal activities'),
            ('very_severe', 'Very severe - unable to move/talk/function'),
        ],
        required=False,
        allow_null=True
    )

    # Symptom Duration (EXPANDED)
    symptom_duration = serializers.ChoiceField(
        choices=[
            ('less_than_1_hour', 'Less than 1 hour'),
            ('1_6_hours', '1-6 hours'),
            ('6_24_hours', '6-24 hours'),
            ('1_3_days', '1-3 days'),
            ('4_7_days', '4-7 days'),
            ('more_than_1_week', 'More than 1 week'),
            ('more_than_1_month', 'More than 1 month'),
        ],
        required=False,
        allow_null=True
    )

    # Symptom Progression (NEW - replaces pattern)
    progression_status = serializers.ChoiceField(
        choices=[
            ('sudden', 'Sudden onset'),
            ('getting_worse', 'Getting worse'),
            ('staying_same', 'Staying the same'),
            ('getting_better', 'Getting better'),
            ('comes_and_goes', 'Comes and goes'),
        ],
        required=False,
        allow_null=True,
        help_text="Observable symptom trajectory"
    )

    # ========================================================================
    # RED FLAG INDICATORS (NEW - continuous monitoring)
    # ========================================================================
    
    red_flag_indicators = serializers.JSONField(
        required=False,
        default=dict,
        help_text="WHO ABCD danger signs detected at any point"
    )

    # ========================================================================
    # HIGH-RISK MODIFIERS (UPDATED)
    # ========================================================================
    
    risk_modifiers = serializers.JSONField(
        required=False,
        default=dict,
        help_text="High-risk population flags"
    )

    # Pregnancy Status (SIMPLIFIED)
    pregnancy_status = serializers.ChoiceField(
        choices=[
            ('yes', 'Yes, confirmed pregnant'),
            ('possible', 'Possibly pregnant'),
            ('no', 'No'),
            ('not_applicable', 'Not applicable'),
        ],
        required=False,
        allow_null=True
    )

    # Chronic conditions (SIMPLIFIED)
    has_chronic_conditions = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Patient has any chronic illness"
    )

    # Current medication (SIMPLIFIED)
    on_medication = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Patient is currently taking any medication"
    )

    # ========================================================================
    # DEPRECATED FIELDS (kept for backwards compatibility)
    # ========================================================================
    
    # These fields are deprecated but kept to avoid breaking existing clients
    age_range = serializers.ChoiceField(
        choices=['under_5', '5_12', '13_17', '18_30', '31_50', '51_plus'],
        required=False,
        write_only=True,
        help_text="DEPRECATED: Use age_group instead"
    )
    
    primary_symptom = serializers.ChoiceField(
        choices=[
            'fever', 'headache', 'chest_pain', 'difficulty_breathing',
            'abdominal_pain', 'vomiting', 'diarrhea', 'injury_trauma',
            'skin_problem', 'other'
        ],
        required=False,
        write_only=True,
        help_text="DEPRECATED: Use complaint_group instead"
    )

    secondary_symptoms = serializers.ListField(
        child=serializers.ChoiceField(
            choices=[
                'cough', 'fatigue', 'dizziness', 'nausea', 'body_weakness',
                'swelling', 'bleeding', 'loss_of_appetite', 'none'
            ]
        ),
        required=False,
        default=list,
        write_only=True,
        help_text="DEPRECATED: Use symptom_indicators instead"
    )

    symptom_pattern = serializers.ChoiceField(
        choices=['getting_better', 'staying_same', 'getting_worse', 'comes_and_goes'],
        required=False,
        allow_null=True,
        write_only=True,
        help_text="DEPRECATED: Use progression_status instead"
    )

    condition_occurrence = serializers.ChoiceField(
        choices=['first_occurrence', 'happened_before', 'long_term'],
        required=False,
        write_only=True,
        help_text="DEPRECATED: Use risk_modifiers instead"
    )

    chronic_conditions = serializers.ListField(
        child=serializers.ChoiceField(
            choices=[
                'hypertension', 'diabetes', 'asthma', 'heart_disease',
                'epilepsy', 'sickle_cell', 'other_chronic', 'none', 'prefer_not_to_say'
            ]
        ),
        required=False,
        default=list,
        write_only=True,
        help_text="DEPRECATED: Use risk_modifiers instead"
    )

    current_medication = serializers.ChoiceField(
        choices=['yes', 'no', 'not_sure'],
        required=False,
        allow_null=True,
        write_only=True,
        help_text="DEPRECATED: Use on_medication boolean instead"
    )

    has_allergies = serializers.ChoiceField(
        choices=['yes', 'no', 'not_sure'],
        required=False,
        allow_null=True,
        write_only=True,
        help_text="DEPRECATED: Include in risk_modifiers"
    )
    
    allergy_types = serializers.ListField(
        child=serializers.ChoiceField(choices=['medication', 'food', 'environmental']),
        required=False,
        default=list,
        write_only=True,
        help_text="DEPRECATED: Include in risk_modifiers"
    )

    additional_description = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        write_only=True,
        help_text="DEPRECATED: Use complaint_text instead"
    )

    # ========================================================================
    # CONSENT (REQUIRED) - UNCHANGED
    # ========================================================================
    
    consent_medical_triage = serializers.BooleanField(required=True)
    consent_data_sharing = serializers.BooleanField(required=True)
    consent_follow_up = serializers.BooleanField(required=True)

    # ========================================================================
    # CHANNEL - UNCHANGED
    # ========================================================================
    
    channel = serializers.ChoiceField(
        choices=['ussd', 'sms', 'whatsapp', 'web', 'mobile_app'],
        default='web'
    )

    def validate(self, data):
        """
        Object-level validation - UPDATED
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

        # Pregnancy validation - UPDATED with possible status
        if data.get('sex') == 'male' and data.get('pregnancy_status') in ['yes', 'possible']:
            raise serializers.ValidationError(
                "Invalid pregnancy status for male patient"
            )

        # Location validation
        if data.get('location_consent'):
            if not (data.get('device_location_lat') and data.get('device_location_lng')):
                raise serializers.ValidationError(
                    "Location coordinates required when location consent is given"
                )

        # Ensure at least complaint_text or complaint_group is provided
        if not data.get('complaint_text') and not data.get('complaint_group'):
            raise serializers.ValidationError(
                "Either complaint_text or complaint_group must be provided"
            )

        return data

    def to_internal_value(self, data):
        """
        Handle deprecated field mapping
        """
        # Make a mutable copy
        data = super().to_internal_value(data)
        
        # Map deprecated age_range to age_group if age_group not provided
        if not data.get('age_group') and data.get('age_range'):
            age_range_map = {
                'under_5': 'child_1_5',  # Approximate mapping
                '5_12': 'child_6_12',
                '13_17': 'teen',
                '18_30': 'adult',
                '31_50': 'adult',
                '51_plus': 'elderly',
            }
            data['age_group'] = age_range_map.get(data['age_range'], 'adult')
        
        # Map primary_symptom to complaint_group if complaint_group not provided
        if not data.get('complaint_group') and data.get('primary_symptom'):
            symptom_map = {
                'fever': 'fever',
                'headache': 'headache',
                'chest_pain': 'chest_pain',
                'difficulty_breathing': 'breathing',
                'abdominal_pain': 'abdominal',
                'vomiting': 'abdominal',
                'diarrhea': 'abdominal',
                'injury_trauma': 'injury',
                'skin_problem': 'skin',
                'other': 'other',
            }
            data['complaint_group'] = symptom_map.get(data['primary_symptom'], 'other')
        
        # Map additional_description to complaint_text if complaint_text not provided
        if not data.get('complaint_text') and data.get('additional_description'):
            data['complaint_text'] = data['additional_description']
        
        return data


class TriageSessionSerializer(serializers.ModelSerializer):
    """
    Full triage session serializer for responses - UPDATED
    """

    symptom_summary = serializers.SerializerMethodField()
    is_emergency = serializers.BooleanField(read_only=True)
    needs_immediate_attention = serializers.BooleanField(read_only=True)
    is_high_risk_population = serializers.BooleanField(read_only=True)

    class Meta:
        model = TriageSession
        fields = [
            'id',
            'patient_token',
            'session_status',
            
            # NEW/Updated fields
            'complaint_text',
            'complaint_group',
            'age_group',
            'sex',
            'patient_relation',
            'symptom_indicators',
            'symptom_severity',
            'symptom_duration',
            'progression_status',
            'red_flag_indicators',
            'has_red_flags',
            'red_flag_detected_at_turn',
            'risk_modifiers',
            'pregnancy_status',
            'has_chronic_conditions',
            'on_medication',
            
            # Location
            'district',
            'subcounty',
            'village',
            
            # Risk assessment
            'risk_level',
            'risk_confidence',
            'follow_up_priority',
            
            # Summary properties
            'symptom_summary',
            'is_emergency',
            'needs_immediate_attention',
            'is_high_risk_population',
            
            # Metadata
            'assessment_completed_at',
            'created_at',
            'channel',
            'conversation_turns'
        ]
        read_only_fields = [
            'id',
            'patient_token',
            'has_red_flags',
            'red_flag_detected_at_turn',
            'risk_level',
            'risk_confidence',
            'follow_up_priority',
            'assessment_completed_at',
            'created_at',
            'conversation_turns'
        ]

    def get_symptom_summary(self, obj):
        return obj.generate_symptom_summary()


class TriageResultSerializer(serializers.Serializer):
    """
    Triage result returned to patient - UPDATED
    """

    patient_token = serializers.CharField()
    risk_level = serializers.CharField()
    risk_confidence = serializers.FloatField()
    follow_up_priority = serializers.CharField()

    # Red flags - UPDATED
    has_red_flags = serializers.BooleanField()
    red_flag_indicators = serializers.JSONField()
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

    # Additional info (NEW)
    age_group = serializers.CharField()
    complaint_group = serializers.CharField()
    conversation_turns = serializers.IntegerField()


class RedFlagDetectionSerializer(serializers.ModelSerializer):
    """
    Red flag detection results - UPDATED with WHO ABCD
    """

    detected_flag_names = serializers.SerializerMethodField()

    class Meta:
        model = RedFlagDetection
        fields = [
            # WHO ABCD categories
            'airway_obstruction',
            'severe_breathing_difficulty',
            'chest_indrawing',
            'severe_bleeding',
            'signs_of_shock',
            'unconscious',
            'convulsions',
            'confusion',
            'stroke_symptoms',
            
            # Age-specific
            'unable_to_drink',
            'vomits_everything',
            'lethargic_floppy',
            
            # Other critical
            'severe_pain',
            'pregnancy_emergency',
            
            # Metadata
            'emergency_override',
            'detection_method',
            'detected_flags_count',
            'detection_turn_number',
            
            # Helper
            'detected_flag_names'
        ]

    def get_detected_flag_names(self, obj):
        return obj.get_detected_flag_names()


class RiskClassificationSerializer(serializers.ModelSerializer):
    """
    AI risk classification results - UPDATED
    """

    class Meta:
        model = RiskClassification
        fields = [
            'raw_risk_score',
            'ai_risk_level',
            'confidence_score',
            'model_name',
            'model_version',
            'inference_time_ms',
            'feature_importance',  # Added
            'complaint_embedding'   # Added
        ]


class ClinicalContextSerializer(serializers.ModelSerializer):
    """
    Clinical context adjustments - UPDATED
    """

    class Meta:
        model = ClinicalContext
        fields = [
            'age_modifier',
            'pregnancy_modifier',
            'chronic_condition_modifier',
            'immunocompromised_modifier',
            'medication_modifier',
            'total_risk_adjustment',
            'adjustment_reasoning',
            'adjusted_risk_level',
            'conservative_bias_applied'
        ]


class TriageDecisionSerializer(serializers.ModelSerializer):
    """
    Final triage decision - UPDATED with new decision basis
    """

    class Meta:
        model = TriageDecision
        fields = [
            'final_risk_level',
            'follow_up_priority',
            'decision_basis',  # Now includes age_risk_modifier
            'recommended_action',
            'facility_type_recommendation',
            'decision_timestamp',
            'decision_reasoning',
            'disclaimers'
        ]


class TriageStatusSerializer(serializers.Serializer):
    """
    Triage session status check - UPDATED
    """

    patient_token = serializers.CharField()
    session_status = serializers.CharField()
    complaint_group = serializers.CharField(allow_null=True)
    age_group = serializers.CharField()
    risk_level = serializers.CharField(allow_null=True)
    has_red_flags = serializers.BooleanField()
    assessment_completed = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    assessment_completed_at = serializers.DateTimeField(allow_null=True)
    conversation_turns = serializers.IntegerField()


class SymptomIndicatorUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating symptom indicators during conversation
    NEW - supports adaptive questioning
    """

    patient_token = serializers.CharField()
    symptom_indicators = serializers.JSONField(required=True)
    red_flag_indicators = serializers.JSONField(required=False, default=dict)
    turn_number = serializers.IntegerField(min_value=1)