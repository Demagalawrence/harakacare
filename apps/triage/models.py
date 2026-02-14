"""
Triage Models
Models for AI-powered medical triage assessment
Based on: HarakaCare Triage Agent Data Requirements
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


import uuid

from apps.core.models import BaseModel, StatusModel


class TriageSession(StatusModel):
    """
    Main triage session model
    Stores anonymous patient triage data
    """

    class RiskLevel(models.TextChoices):
        LOW = 'low', _('Low Risk')
        MEDIUM = 'medium', _('Medium Risk')
        HIGH = 'high', _('High Risk')

    class FollowUpPriority(models.TextChoices):
        ROUTINE = 'routine', _('Routine')
        URGENT = 'urgent', _('Urgent')
        IMMEDIATE = 'immediate', _('Immediate')

    class SessionStatus(models.TextChoices):
        STARTED = 'started', _('Started')
        IN_PROGRESS = 'in_progress', _('In Progress')
        COMPLETED = 'completed', _('Completed')
        ESCALATED = 'escalated', _('Escalated')
        CANCELLED = 'cancelled', _('Cancelled')

    # Anonymous Patient Token (system-generated, no PII)
    patient_token = models.CharField(
        _('patient token'),
        max_length=64,
        unique=True,
        db_index=True,
        help_text=_('Anonymous identifier for this patient session')
    )

    # Session metadata
    session_status = models.CharField(
        _('session status'),
        max_length=20,
        choices=SessionStatus.choices,
        default=SessionStatus.STARTED
    )

    # Demographic Context (3.2)
    age_range = models.CharField(
        _('age range'),
        max_length=20,
        choices=[
            ('under_5', _('Under 5')),
            ('5_12', _('5-12')),
            ('13_17', _('13-17')),
            ('18_30', _('18-30')),
            ('31_50', _('31-50')),
            ('51_plus', _('51+')),
        ],
        help_text=_('Patient age range')
    )

    sex = models.CharField(
        _('sex'),
        max_length=20,
        choices=[
            ('male', _('Male')),
            ('female', _('Female')),
            ('prefer_not_to_say', _('Prefer not to say')),
        ],
        null=True,
        blank=True
    )

    # Location Data (3.3) - Coarse location only
    district = models.CharField(
        _('district'),
        max_length=100,
        help_text=_('District or area')
    )

    subcounty = models.CharField(
        _('subcounty'),
        max_length=100,
        null=True,
        blank=True,
        help_text=_('Sub-county or division')
    )

    device_location_lat = models.FloatField(
        _('latitude'),
        null=True,
        blank=True,
        help_text=_('Device GPS latitude (consent-based)')
    )

    device_location_lng = models.FloatField(
        _('longitude'),
        null=True,
        blank=True,
        help_text=_('Device GPS longitude (consent-based)')
    )

    location_consent = models.BooleanField(
        _('location consent'),
        default=False,
        help_text=_('Whether patient consented to share device location')
    )

    # Primary Symptom (3.4) - Single choice, required
    primary_symptom = models.CharField(
        _('primary symptom'),
        max_length=50,
        choices=[
            ('fever', _('Fever')),
            ('headache', _('Headache')),
            ('chest_pain', _('Chest pain')),
            ('difficulty_breathing', _('Difficulty breathing')),
            ('abdominal_pain', _('Abdominal pain')),
            ('vomiting', _('Vomiting')),
            ('diarrhea', _('Diarrhea')),
            ('injury_trauma', _('Injury / trauma')),
            ('skin_problem', _('Skin problem')),
            ('other', _('Other')),
        ]
    )

    # Secondary Symptoms (3.5) - Multiple choice (stored as array)
    secondary_symptoms =  models.JSONField(
        models.CharField(max_length=50),
        blank=True,
        default=list,
        help_text=_('Secondary symptoms (multiple choice)')
    )

    # Symptom Severity (3.6) - Required
    symptom_severity = models.CharField(
        _('symptom severity'),
        max_length=20,
        choices=[
            ('mild', _('Mild')),
            ('moderate', _('Moderate')),
            ('severe', _('Severe')),
            ('very_severe', _('Very severe')),
        ]
    )

    # Symptom Duration (3.7) - Required
    symptom_duration = models.CharField(
        _('symptom duration'),
        max_length=20,
        choices=[
            ('today', _('Today')),
            ('1_3_days', _('1-3 days')),
            ('4_7_days', _('4-7 days')),
            ('more_than_1_week', _('More than 1 week')),
            ('more_than_1_month', _('More than 1 month')),
        ]
    )

    # Symptom Pattern (3.8) - Optional
    symptom_pattern = models.CharField(
        _('symptom pattern'),
        max_length=20,
        choices=[
            ('getting_better', _('Getting better')),
            ('staying_same', _('Staying the same')),
            ('getting_worse', _('Getting worse')),
            ('comes_and_goes', _('Comes and goes')),
        ],
        null=True,
        blank=True
    )

    # Emergency Red Flags (3.9) - Stored as array of detected flags
    red_flags =  models.JSONField(
        models.CharField(max_length=50),
        blank=True,
        default=list,
        help_text=_('Emergency red-flag symptoms detected')
    )

    has_red_flags = models.BooleanField(
        _('has red flags'),
        default=False,
        help_text=_('Whether any emergency red flags were detected')
    )

    # Previous Condition (3.10) - Required
    condition_occurrence = models.CharField(
        _('condition occurrence'),
        max_length=30,
        choices=[
            ('first_occurrence', _('First occurrence')),
            ('happened_before', _('Happened before')),
            ('long_term', _('Long-term / continuous condition')),
        ]
    )

    # Chronic Conditions (3.11) - Multiple choice
    chronic_conditions =  models.JSONField(
        models.CharField(max_length=50),
        blank=True,
        default=list,
        help_text=_('Pre-existing chronic conditions')
    )

    # Current Medication (3.12)
    current_medication = models.CharField(
        _('current medication'),
        max_length=20,
        choices=[
            ('yes', _('Yes')),
            ('no', _('No')),
            ('not_sure', _('Not sure')),
        ],
        null=True,
        blank=True
    )

    # Allergies (3.13)
    has_allergies = models.CharField(
        _('has allergies'),
        max_length=20,
        choices=[
            ('yes', _('Yes')),
            ('no', _('No')),
            ('not_sure', _('Not sure')),
        ],
        null=True,
        blank=True
    )

    allergy_types =  models.JSONField(
        models.CharField(max_length=30),
        blank=True,
        default=list,
        help_text=_('Types of allergies: medication, food, environmental')
    )

    # Pregnancy Status (3.14) - Conditional
    pregnancy_status = models.CharField(
        _('pregnancy status'),
        max_length=30,
        choices=[
            ('yes', _('Yes')),
            ('no', _('No')),
            ('not_applicable', _('Not applicable')),
            ('prefer_not_to_say', _('Prefer not to say')),
        ],
        null=True,
        blank=True
    )

    # Additional Description (3.15) - Optional
    additional_description = models.TextField(
        _('additional description'),
        max_length=500,
        blank=True,
        help_text=_('Short free-text description (character-limited)')
    )

    # Consent (3.16) - Required
    consent_medical_triage = models.BooleanField(
        _('consent for medical triage'),
        default=False
    )

    consent_data_sharing = models.BooleanField(
        _('consent for data sharing'),
        default=False,
        help_text=_('Consent for anonymized data sharing with health facilities')
    )

    consent_follow_up = models.BooleanField(
        _('consent for follow-up'),
        default=False,
        help_text=_('Consent for follow-up if required')
    )

    # AI Assessment Results
    risk_level = models.CharField(
        _('risk level'),
        max_length=20,
        choices=RiskLevel.choices,
        null=True,
        blank=True,
        help_text=_('AI-assessed risk level')
    )

    risk_confidence = models.FloatField(
        _('risk confidence'),
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text=_('AI model confidence score (0-1)')
    )

    follow_up_priority = models.CharField(
        _('follow-up priority'),
        max_length=20,
        choices=FollowUpPriority.choices,
        null=True,
        blank=True
    )

    # Assessment metadata
    ai_model_version = models.CharField(
        _('AI model version'),
        max_length=50,
        null=True,
        blank=True,
        help_text=_('Version of AI model used for assessment')
    )

    assessment_completed_at = models.DateTimeField(
        _('assessment completed at'),
        null=True,
        blank=True
    )

    # Agent communication tracking
    forwarded_to_followup = models.BooleanField(
        _('forwarded to follow-up agent'),
        default=False
    )

    forwarded_to_facility = models.BooleanField(
        _('forwarded to facility matching'),
        default=False
    )

    # Channel information
    channel = models.CharField(
        _('channel'),
        max_length=20,
        choices=[
            ('ussd', _('USSD')),
            ('sms', _('SMS')),
            ('whatsapp', _('WhatsApp')),
            ('web', _('Web')),
            ('mobile_app', _('Mobile App')),
        ],
        default='ussd'
    )

    class Meta:
        verbose_name = _('triage session')
        verbose_name_plural = _('triage sessions')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patient_token']),
            models.Index(fields=['risk_level', 'created_at']),
            models.Index(fields=['district', 'subcounty']),
            models.Index(fields=['has_red_flags']),
            models.Index(fields=['session_status']),
        ]

    def __str__(self):
        return f"Triage {self.patient_token[:8]} - {self.risk_level or 'Pending'}"

    @property
    def is_emergency(self):
        """Check if this is an emergency case"""
        return self.has_red_flags or self.risk_level == self.RiskLevel.HIGH

    @property
    def needs_immediate_attention(self):
        """Check if case needs immediate attention"""
        return (
                self.has_red_flags or
                self.risk_level == self.RiskLevel.HIGH or
                self.symptom_severity == 'very_severe'
        )

    def generate_symptom_summary(self):
        """Generate a text summary of symptoms"""
        summary_parts = [f"Primary: {self.get_primary_symptom_display()}"]

        if self.secondary_symptoms:
            summary_parts.append(f"Secondary: {', '.join(self.secondary_symptoms)}")

        summary_parts.append(f"Severity: {self.get_symptom_severity_display()}")
        summary_parts.append(f"Duration: {self.get_symptom_duration_display()}")

        if self.has_red_flags:
            summary_parts.append(f"⚠️ RED FLAGS: {', '.join(self.red_flags)}")

        return " | ".join(summary_parts)


class SymptomAssessment(BaseModel):
    """
    Detailed symptom assessment with clinical context
    Tool 2: Symptom Assessment Tool output
    """

    triage_session = models.OneToOneField(
        TriageSession,
        on_delete=models.CASCADE,
        related_name='symptom_assessment',
        verbose_name=_('triage session')
    )

    # Structured symptom analysis
    symptom_complexity_score = models.FloatField(
        _('symptom complexity score'),
        validators=[MinValueValidator(0.0), MaxValueValidator(10.0)],
        help_text=_('Calculated complexity score based on symptoms')
    )

    symptom_cluster = models.CharField(
        _('symptom cluster'),
        max_length=100,
        blank=True,
        help_text=_('Identified symptom cluster (e.g., respiratory, gastrointestinal)')
    )

    # Clinical reasoning
    differential_conditions =  models.JSONField(
        models.CharField(max_length=100),
        blank=True,
        default=list,
        help_text=_('Possible conditions based on symptoms (for reference only)')
    )

    # Assessment notes (generated by tool)
    assessment_notes = models.TextField(
        _('assessment notes'),
        blank=True,
        help_text=_('AI-generated clinical assessment notes')
    )

    # Symptom severity indicators
    pain_scale = models.IntegerField(
        _('pain scale'),
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text=_('Pain intensity 0-10')
    )

    class Meta:
        verbose_name = _('symptom assessment')
        verbose_name_plural = _('symptom assessments')

    def __str__(self):
        return f"Assessment for {self.triage_session.patient_token[:8]}"


class RedFlagDetection(BaseModel):
    """
    Emergency red-flag detection results
    Tool 3: Red-Flag Detection Tool output
    """

    triage_session = models.OneToOneField(
        TriageSession,
        on_delete=models.CASCADE,
        related_name='red_flag_detection',
        verbose_name=_('triage session')
    )

    # Individual red flag checks
    difficulty_breathing = models.BooleanField(_('difficulty breathing'), default=False)
    chest_pain = models.BooleanField(_('chest pain'), default=False)
    loss_of_consciousness = models.BooleanField(_('loss of consciousness'), default=False)
    convulsions = models.BooleanField(_('convulsions/seizures'), default=False)
    severe_bleeding = models.BooleanField(_('severe bleeding'), default=False)
    confusion = models.BooleanField(_('confusion or inability to talk'), default=False)
    high_fever_unresponsive = models.BooleanField(_('high fever not responding'), default=False)

    # Detection metadata
    emergency_override = models.BooleanField(
        _('emergency override'),
        default=False,
        help_text=_('Whether red flags override AI assessment')
    )

    detection_method = models.CharField(
        _('detection method'),
        max_length=50,
        choices=[
            ('user_input', _('User Input')),
            ('ai_detected', _('AI Detected')),
            ('rule_based', _('Rule-based')),
        ],
        default='user_input'
    )

    detected_flags_count = models.IntegerField(
        _('detected flags count'),
        default=0,
        help_text=_('Number of red flags detected')
    )

    class Meta:
        verbose_name = _('red flag detection')
        verbose_name_plural = _('red flag detections')

    def __str__(self):
        return f"Red Flags for {self.triage_session.patient_token[:8]} - {self.detected_flags_count} detected"

    def count_red_flags(self):
        """Count total red flags detected"""
        flags = [
            self.difficulty_breathing,
            self.chest_pain,
            self.loss_of_consciousness,
            self.convulsions,
            self.severe_bleeding,
            self.confusion,
            self.high_fever_unresponsive,
        ]
        self.detected_flags_count = sum(flags)
        return self.detected_flags_count


class RiskClassification(BaseModel):
    """
    AI-powered risk classification results
    Tool 4: Risk Classification Tool output
    """

    triage_session = models.OneToOneField(
        TriageSession,
        on_delete=models.CASCADE,
        related_name='risk_classification',
        verbose_name=_('triage session')
    )

    # AI Model outputs
    raw_risk_score = models.FloatField(
        _('raw risk score'),
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text=_('Raw AI model risk score (0-1)')
    )

    ai_risk_level = models.CharField(
        _('AI risk level'),
        max_length=20,
        choices=TriageSession.RiskLevel.choices,
        help_text=_('AI-determined risk level before adjustments')
    )

    confidence_score = models.FloatField(
        _('confidence score'),
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text=_('Model confidence in prediction')
    )

    # Model metadata
    model_name = models.CharField(
        _('model name'),
        max_length=100,
        help_text=_('Name of AI model used')
    )

    model_version = models.CharField(
        _('model version'),
        max_length=50,
        help_text=_('Version of model used')
    )

    inference_time_ms = models.IntegerField(
        _('inference time (ms)'),
        null=True,
        blank=True,
        help_text=_('Time taken for inference in milliseconds')
    )

    # Feature importance
    feature_importance = models.JSONField(
        _('feature importance'),
        null=True,
        blank=True,
        help_text=_('Which features contributed most to classification')
    )

    # Input embeddings metadata
    symptom_embedding = models.JSONField(
        _('symptom embedding'),
        null=True,
        blank=True,
        help_text=_('Symptom text embeddings (for analysis)')
    )

    class Meta:
        verbose_name = _('risk classification')
        verbose_name_plural = _('risk classifications')

    def __str__(self):
        return f"Risk: {self.ai_risk_level} ({self.confidence_score:.2f}) - {self.triage_session.patient_token[:8]}"


class ClinicalContext(BaseModel):
    """
    Clinical context adjustments to risk
    Tool 5: Clinical Context Tool output
    """

    triage_session = models.OneToOneField(
        TriageSession,
        on_delete=models.CASCADE,
        related_name='clinical_context',
        verbose_name=_('triage session')
    )

    # Risk adjustment factors
    chronic_condition_modifier = models.FloatField(
        _('chronic condition modifier'),
        default=0.0,
        help_text=_('Risk adjustment for chronic conditions (-1.0 to +1.0)')
    )

    pregnancy_modifier = models.FloatField(
        _('pregnancy modifier'),
        default=0.0,
        help_text=_('Risk adjustment for pregnancy')
    )

    age_modifier = models.FloatField(
        _('age modifier'),
        default=0.0,
        help_text=_('Risk adjustment for age (young/elderly)')
    )

    medication_allergy_modifier = models.FloatField(
        _('medication/allergy modifier'),
        default=0.0,
        help_text=_('Risk adjustment for medication and allergies')
    )

    # Total adjustment
    total_risk_adjustment = models.FloatField(
        _('total risk adjustment'),
        default=0.0,
        help_text=_('Combined risk adjustment factor')
    )

    # Adjustment reasoning
    adjustment_reasoning = models.TextField(
        _('adjustment reasoning'),
        blank=True,
        help_text=_('Explanation for risk adjustments made')
    )

    # Final adjusted risk
    adjusted_risk_level = models.CharField(
        _('adjusted risk level'),
        max_length=20,
        choices=TriageSession.RiskLevel.choices,
        help_text=_('Risk level after clinical context adjustments')
    )

    class Meta:
        verbose_name = _('clinical context')
        verbose_name_plural = _('clinical contexts')

    def __str__(self):
        return f"Context for {self.triage_session.patient_token[:8]} - Adjustment: {self.total_risk_adjustment:+.2f}"


class TriageDecision(BaseModel):
    """
    Final triage decision synthesis
    Tool 6: Decision Synthesis Tool output
    """

    triage_session = models.OneToOneField(
        TriageSession,
        on_delete=models.CASCADE,
        related_name='triage_decision',
        verbose_name=_('triage session')
    )

    # Final decision
    final_risk_level = models.CharField(
        _('final risk level'),
        max_length=20,
        choices=TriageSession.RiskLevel.choices,
        help_text=_('Final triage risk level')
    )

    follow_up_priority = models.CharField(
        _('follow-up priority'),
        max_length=20,
        choices=TriageSession.FollowUpPriority.choices,
        help_text=_('Priority for follow-up')
    )

    # Decision logic
    decision_basis = models.CharField(
        _('decision basis'),
        max_length=50,
        choices=[
            ('ai_primary', _('AI Primary')),
            ('red_flag_override', _('Red Flag Override')),
            ('clinical_adjustment', _('Clinical Adjustment')),
            ('conservative_bias', _('Conservative Bias')),
        ],
        help_text=_('Primary basis for final decision')
    )

    # Recommendations
    recommended_action = models.TextField(
        _('recommended action'),
        help_text=_('Recommended next steps for patient')
    )

    facility_type_recommendation = models.CharField(
        _('facility type recommendation'),
        max_length=50,
        choices=[
            ('emergency', _('Emergency Department')),
            ('hospital', _('Hospital')),
            ('health_center', _('Health Center')),
            ('clinic', _('Clinic')),
            ('self_care', _('Self-care with monitoring')),
        ],
        null=True,
        blank=True
    )

    # Decision metadata
    decision_timestamp = models.DateTimeField(
        _('decision timestamp'),
        auto_now_add=True
    )

    decision_reasoning = models.TextField(
        _('decision reasoning'),
        help_text=_('Detailed explanation of how decision was reached')
    )

    # Disclaimers shown
    disclaimers =  models.JSONField(
        models.TextField(),
        default=list,
        help_text=_('Disclaimers shown to patient')
    )

    class Meta:
        verbose_name = _('triage decision')
        verbose_name_plural = _('triage decisions')

    def __str__(self):
        return f"Decision: {self.final_risk_level} - {self.triage_session.patient_token[:8]}"


class AgentCommunicationLog(BaseModel):
    """
    Log of inter-agent communications
    Tool 8: Agent Communication Tool output
    """

    triage_session = models.ForeignKey(
        TriageSession,
        on_delete=models.CASCADE,
        related_name='agent_communications',
        verbose_name=_('triage session')
    )

    # Target agent
    target_agent = models.CharField(
        _('target agent'),
        max_length=50,
        choices=[
            ('follow_up', _('Follow-up Agent')),
            ('facility_matching', _('Facility Matching Agent')),
            ('notification', _('Notification Agent')),
        ]
    )

    # Payload sent
    payload = models.JSONField(
        _('payload'),
        help_text=_('JSON payload sent to target agent')
    )

    # Communication status
    communication_status = models.CharField(
        _('status'),
        max_length=20,
        choices=[
            ('pending', _('Pending')),
            ('sent', _('Sent')),
            ('acknowledged', _('Acknowledged')),
            ('failed', _('Failed')),
        ],
        default='pending'
    )

    # Response
    response_data = models.JSONField(
        _('response data'),
        null=True,
        blank=True,
        help_text=_('Response received from target agent')
    )

    # Timing
    sent_at = models.DateTimeField(
        _('sent at'),
        null=True,
        blank=True
    )

    acknowledged_at = models.DateTimeField(
        _('acknowledged at'),
        null=True,
        blank=True
    )

    # Error tracking
    error_message = models.TextField(
        _('error message'),
        blank=True,
        help_text=_('Error message if communication failed')
    )

    retry_count = models.IntegerField(
        _('retry count'),
        default=0,
        help_text=_('Number of retry attempts')
    )

    class Meta:
        verbose_name = _('agent communication log')
        verbose_name_plural = _('agent communication logs')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['triage_session', 'target_agent']),
            models.Index(fields=['communication_status']),
        ]

    def __str__(self):
        return f"{self.target_agent} - {self.communication_status} - {self.triage_session.patient_token[:8]}"