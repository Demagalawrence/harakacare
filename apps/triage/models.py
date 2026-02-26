"""
Triage Models - UPDATED FOR COMPLAINT-BASED, AGE-ADAPTIVE TRIAGE
Models for AI-powered medical triage assessment
Based on: WHO/ICRC triage principles + HarakaCare requirements

MAJOR CHANGES:
- Replaced "primary symptom" with "complaint group"
- Added mandatory age_group (7 categories) and sex fields
- Added complaint_text for AI classification
- Added symptom_indicators (JSONField) for structured answers
- Added progression_status for symptom trajectory
- Added risk_modifiers for high-risk populations
- Continuous red_flag_indicators throughout conversation
- Removed vital signs (users can't measure these)
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

from apps.core.models import BaseModel, StatusModel


class TriageSession(StatusModel):
    """
    Main triage session model - REDESIGNED
    Implements WHO/ICRC-aligned, age-adaptive triage
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

    # ========================================================================
    # ANONYMOUS PATIENT TOKEN
    # ========================================================================
    
    patient_token = models.CharField(
        _('patient token'),
        max_length=64,
        unique=True,
        db_index=True,
        help_text=_('Anonymous identifier for this patient session')
    )

    session_status = models.CharField(
        _('session status'),
        max_length=20,
        choices=SessionStatus.choices,
        default=SessionStatus.STARTED
    )

    # ========================================================================
    # NEW: COMPLAINT-BASED INTAKE (replaces "primary symptom")
    # ========================================================================
    
    complaint_text = models.TextField(
        _('complaint text'),
        help_text=_('Original user message: "Tell me what is happening"'),
        blank=True
    )

    complaint_group = models.CharField(
        _('complaint group'),
        max_length=50,
        choices=[
            ('fever', _('Fever / feeling hot')),
            ('breathing', _('Breathing or cough problem')),
            ('injury', _('Injury or accident')),
            ('abdominal', _('Abdominal pain / vomiting / diarrhea')),
            ('headache', _('Headache / confusion / weakness')),
            ('chest_pain', _('Chest pain')),
            ('pregnancy', _('Pregnancy concern')),
            ('skin', _('Skin problem')),
            ('feeding', _('Feeding problem / general weakness')),
            ('bleeding', _('Bleeding / blood loss')),
            ('mental_health', _('Mental health / emotional crisis')),
            ('other', _('Other')),
        ],
        null=True,
        blank=True,
        help_text=_('AI-classified complaint group (NOT a diagnosis)')
    )

    # ========================================================================
    # MANDATORY DEMOGRAPHIC CONTEXT (captured EARLY)
    # ========================================================================
    
    age_group = models.CharField(
        _('age group'),
        max_length=20,
        choices=[
            ('newborn', _('Newborn (0-2 months)')),
            ('infant', _('Infant (2-12 months)')),
            ('child_1_5', _('Child (1-5 years)')),
            ('child_6_12', _('Child (6-12 years)')),
            ('teen', _('Teen (13-17 years)')),
            ('adult', _('Adult (18-64 years)')),
            ('elderly', _('Elderly (65+ years)')),
        ],
        help_text=_('Age group - determines question tree and risk modifiers')
    )

    sex = models.CharField(
        _('sex'),
        max_length=20,
        choices=[
            ('male', _('Male')),
            ('female', _('Female')),
            ('other', _('Other / Prefer not to say')),
        ],
        help_text=_('Biological sex - required for pregnancy screening')
    )

    # Person for whom triage is being done
    patient_relation = models.CharField(
        _('patient relation'),
        max_length=20,
        choices=[
            ('self', _('For myself')),
            ('child', _('For my child')),
            ('family', _('For family member')),
            ('other', _('For someone else')),
        ],
        default='self',
        help_text=_('Who is the patient?')
    )

    # ========================================================================
    # STRUCTURED SYMPTOM INDICATORS (from adaptive questions)
    # ========================================================================
    
    symptom_indicators = models.JSONField(
        _('symptom indicators'),
        default=dict,
        blank=True,
        help_text=_(
            'Structured answers from adaptive questions, e.g., '
            '{"breathing_difficulty": true, "chest_indrawing": false, '
            '"can_drink": true, "rash_present": false}'
        )
    )

    # Observable severity (NOT clinical measurements)
    symptom_severity = models.CharField(
        _('symptom severity'),
        max_length=20,
        choices=[
            ('mild', _('Mild - can do normal activities')),
            ('moderate', _('Moderate - some difficulty with activities')),
            ('severe', _('Severe - unable to do normal activities')),
            ('very_severe', _('Very severe - unable to move/talk/function')),
        ],
        null=True,
        blank=True
    )

    symptom_duration = models.CharField(
        _('symptom duration'),
        max_length=20,
        choices=[
            ('less_than_1_hour', _('Less than 1 hour')),
            ('1_6_hours', _('1-6 hours')),
            ('6_24_hours', _('6-24 hours')),
            ('1_3_days', _('1-3 days')),
            ('4_7_days', _('4-7 days')),
            ('more_than_1_week', _('More than 1 week')),
            ('more_than_1_month', _('More than 1 month')),
        ],
        null=True,
        blank=True
    )

    # NEW: Symptom progression (replaces "pattern")
    progression_status = models.CharField(
        _('progression status'),
        max_length=20,
        choices=[
            ('sudden', _('Sudden onset')),
            ('getting_worse', _('Getting worse')),
            ('staying_same', _('Staying the same')),
            ('getting_better', _('Getting better')),
            ('comes_and_goes', _('Comes and goes')),
        ],
        null=True,
        blank=True,
        help_text=_('Observable symptom trajectory')
    )

    # ========================================================================
    # CONTINUOUS RED FLAG INDICATORS (WHO ABCD)
    # ========================================================================
    
    red_flag_indicators = models.JSONField(
        _('red flag indicators'),
        default=dict,
        blank=True,
        help_text=_(
            'WHO ABCD danger signs detected at any point: '
            '{"airway_obstruction": false, "severe_breathing": true, '
            '"heavy_bleeding": false, "unconscious": false, '
            '"convulsions": false, "confusion": false}'
        )
    )

    has_red_flags = models.BooleanField(
        _('has red flags'),
        default=False,
        help_text=_('Whether ANY emergency red flags were detected')
    )

    red_flag_detected_at_turn = models.IntegerField(
        _('red flag detected at turn'),
        null=True,
        blank=True,
        help_text=_('Conversation turn number when first red flag detected')
    )

    # ========================================================================
    # HIGH-RISK MODIFIERS
    # ========================================================================
    
    risk_modifiers = models.JSONField(
        _('risk modifiers'),
        default=dict,
        blank=True,
        help_text=_(
            'High-risk population flags: '
            '{"is_pregnant": false, "has_chronic_asthma": true, '
            '"is_newborn": false, "is_immunocompromised": false}'
        )
    )

    # Pregnancy status (for females 13-50)
    pregnancy_status = models.CharField(
        _('pregnancy status'),
        max_length=30,
        choices=[
            ('yes', _('Yes, confirmed pregnant')),
            ('possible', _('Possibly pregnant')),
            ('no', _('No')),
            ('not_applicable', _('Not applicable')),
        ],
        null=True,
        blank=True
    )

    # Chronic conditions (simplified - yes/no, details in risk_modifiers)
    has_chronic_conditions = models.BooleanField(
        _('has chronic conditions'),
        default=False,
        help_text=_('Patient has any chronic illness (details in risk_modifiers)')
    )

    # Current medication
    on_medication = models.BooleanField(
        _('on medication'),
        default=False,
        help_text=_('Patient is currently taking any medication')
    )

    # ========================================================================
    # LOCATION DATA (captured near END)
    # ========================================================================
    
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

    village = models.CharField(
        _('village'),
        max_length=100,
        null=True,
        blank=True,
        help_text=_('Village or LC1')
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

    # ========================================================================
    # DEPRECATED FIELDS (keep for migration compatibility)
    # ========================================================================
    
    # DEPRECATED: Replaced by complaint_group
    primary_symptom = models.CharField(
        _('primary symptom (DEPRECATED)'),
        max_length=50,
        null=True,
        blank=True,
        help_text=_('DEPRECATED: Use complaint_group instead')
    )

    # DEPRECATED: Replaced by symptom_indicators
    secondary_symptoms = models.JSONField(
        default=list,
        blank=True,
        help_text=_('DEPRECATED: Use symptom_indicators instead')
    )

    # DEPRECATED: Replaced by red_flag_indicators
    red_flags = models.JSONField(
        default=list,
        blank=True,
        help_text=_('DEPRECATED: Use red_flag_indicators instead')
    )

    # DEPRECATED: Too broad
    chronic_conditions = models.JSONField(
        default=list,
        blank=True,
        help_text=_('DEPRECATED: Use risk_modifiers instead')
    )

    # DEPRECATED: Users can't provide this
    additional_description = models.TextField(
        _('additional description (DEPRECATED)'),
        blank=True,
        help_text=_('DEPRECATED: Use complaint_text instead')
    )

    # ========================================================================
    # CONSENT (REQUIRED)
    # ========================================================================
    
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

    # ========================================================================
    # AI ASSESSMENT RESULTS
    # ========================================================================
    
    risk_level = models.CharField(
        _('risk level'),
        max_length=20,
        choices=RiskLevel.choices,
        null=True,
        blank=True,
        help_text=_('Final risk level (after all adjustments)')
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

    # ========================================================================
    # AGENT COMMUNICATION
    # ========================================================================
    
    forwarded_to_followup = models.BooleanField(
        _('forwarded to follow-up agent'),
        default=False
    )

    forwarded_to_facility = models.BooleanField(
        _('forwarded to facility matching'),
        default=False
    )

    # ========================================================================
    # CHANNEL & METADATA
    # ========================================================================
    
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

    conversation_turns = models.IntegerField(
        _('conversation turns'),
        default=0,
        help_text=_('Number of conversation turns to complete triage')
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
            models.Index(fields=['age_group', 'complaint_group']),  # NEW
            models.Index(fields=['complaint_group', 'risk_level']),  # NEW
        ]

    def __str__(self):
        return f"Triage {self.patient_token[:8]} - {self.complaint_group or 'No complaint'} - {self.risk_level or 'Pending'}"

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

    @property
    def is_high_risk_population(self):
        """Check if patient is in high-risk population"""
        high_risk_ages = ['newborn', 'infant', 'child_1_5', 'elderly']
        is_pregnant = self.pregnancy_status in ['yes', 'possible']
        
        return (
            self.age_group in high_risk_ages or
            is_pregnant or
            self.has_chronic_conditions
        )

    def generate_symptom_summary(self):
        """Generate a text summary of symptoms"""
        summary_parts = []
        
        if self.complaint_group:
            summary_parts.append(f"Complaint: {self.get_complaint_group_display()}")
        
        if self.age_group:
            summary_parts.append(f"Age: {self.get_age_group_display()}")
        
        if self.symptom_severity:
            summary_parts.append(f"Severity: {self.get_symptom_severity_display()}")
        
        if self.symptom_duration:
            summary_parts.append(f"Duration: {self.get_symptom_duration_display()}")
        
        if self.progression_status:
            summary_parts.append(f"Progress: {self.get_progression_status_display()}")

        if self.has_red_flags:
            red_flag_names = [k.replace('_', ' ').title() for k, v in self.red_flag_indicators.items() if v]
            summary_parts.append(f"⚠️ RED FLAGS: {', '.join(red_flag_names)}")

        return " | ".join(summary_parts)


# ============================================================================
# SYMPTOM ASSESSMENT - DEPRECATED (replaced by adaptive questioning)
# ============================================================================

class SymptomAssessment(BaseModel):
    """
    DEPRECATED: Replaced by adaptive question engine
    Kept for migration compatibility only
    """

    triage_session = models.OneToOneField(
        TriageSession,
        on_delete=models.CASCADE,
        related_name='symptom_assessment',
        verbose_name=_('triage session')
    )

    symptom_complexity_score = models.FloatField(
        _('symptom complexity score'),
        validators=[MinValueValidator(0.0), MaxValueValidator(10.0)],
        default=0.0
    )

    symptom_cluster = models.CharField(
        _('symptom cluster'),
        max_length=100,
        blank=True
    )

    differential_conditions = models.JSONField(
        default=list,
        blank=True
    )

    assessment_notes = models.TextField(
        _('assessment notes'),
        blank=True
    )

    pain_scale = models.IntegerField(
        _('pain scale'),
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)]
    )

    class Meta:
        verbose_name = _('symptom assessment (DEPRECATED)')
        verbose_name_plural = _('symptom assessments (DEPRECATED)')

    def __str__(self):
        return f"DEPRECATED Assessment for {self.triage_session.patient_token[:8]}"


# ============================================================================
# RED FLAG DETECTION - UPDATED FOR CONTINUOUS MONITORING
# ============================================================================

class RedFlagDetection(BaseModel):
    """
    Emergency red-flag detection results - UPDATED
    Implements WHO ABCD (Airway, Breathing, Circulation, Disability)
    Continuous monitoring throughout conversation
    """

    triage_session = models.OneToOneField(
        TriageSession,
        on_delete=models.CASCADE,
        related_name='red_flag_detection',
        verbose_name=_('triage session')
    )

    # ========================================================================
    # WHO ABCD DANGER SIGNS
    # ========================================================================
    
    # AIRWAY
    airway_obstruction = models.BooleanField(
        _('airway obstruction'),
        default=False,
        help_text=_('Choking, stridor, cannot speak')
    )

    # BREATHING
    severe_breathing_difficulty = models.BooleanField(
        _('severe breathing difficulty'),
        default=False,
        help_text=_('Struggling to breathe, very fast breathing, blue lips')
    )
    
    chest_indrawing = models.BooleanField(
        _('chest indrawing (children)'),
        default=False,
        help_text=_('Visible chest pulling in with breathing')
    )

    # CIRCULATION
    severe_bleeding = models.BooleanField(
        _('severe bleeding'),
        default=False,
        help_text=_('Heavy bleeding, blood loss')
    )
    
    signs_of_shock = models.BooleanField(
        _('signs of shock'),
        default=False,
        help_text=_('Very pale/weak, collapse, cold extremities')
    )

    # DISABILITY (neurological)
    unconscious = models.BooleanField(
        _('unconscious / unresponsive'),
        default=False,
        help_text=_('Not responding, cannot be woken')
    )
    
    convulsions = models.BooleanField(
        _('convulsions/seizures'),
        default=False,
        help_text=_('Fitting, convulsing now or recently')
    )
    
    confusion = models.BooleanField(
        _('confusion / disorientation'),
        default=False,
        help_text=_('Cannot recognize people, confused speech')
    )
    
    stroke_symptoms = models.BooleanField(
        _('stroke symptoms'),
        default=False,
        help_text=_('Face droop, arm weakness, speech difficulty, sudden onset')
    )

    # ========================================================================
    # AGE-SPECIFIC DANGER SIGNS (WHO IMCI)
    # ========================================================================
    
    # For infants/children
    unable_to_drink = models.BooleanField(
        _('unable to drink/feed (child)'),
        default=False,
        help_text=_('Cannot drink or breastfeed')
    )
    
    vomits_everything = models.BooleanField(
        _('vomits everything (child)'),
        default=False,
        help_text=_('Vomits everything given')
    )
    
    lethargic_floppy = models.BooleanField(
        _('lethargic/floppy (infant)'),
        default=False,
        help_text=_('Baby unusually sleepy, floppy, difficult to wake')
    )

    # ========================================================================
    # OTHER CRITICAL CONDITIONS
    # ========================================================================
    
    severe_pain = models.BooleanField(
        _('severe uncontrolled pain'),
        default=False,
        help_text=_('Worst pain ever experienced, unbearable')
    )
    
    pregnancy_emergency = models.BooleanField(
        _('pregnancy emergency'),
        default=False,
        help_text=_('Heavy vaginal bleeding, severe abdominal pain in pregnancy')
    )

    # ========================================================================
    # DETECTION METADATA
    # ========================================================================
    
    emergency_override = models.BooleanField(
        _('emergency override'),
        default=False,
        help_text=_('Red flags override AI assessment')
    )

    detection_method = models.CharField(
        _('detection method'),
        max_length=50,
        choices=[
            ('user_keywords', _('User Keywords')),
            ('ai_detected', _('AI Detected')),
            ('adaptive_question', _('Adaptive Question Response')),
            ('continuous_monitoring', _('Continuous Monitoring')),
        ],
        default='user_keywords'
    )

    detected_flags_count = models.IntegerField(
        _('detected flags count'),
        default=0,
        help_text=_('Number of red flags detected')
    )

    detection_turn_number = models.IntegerField(
        _('detection turn number'),
        null=True,
        blank=True,
        help_text=_('Conversation turn when flags were detected')
    )

    class Meta:
        verbose_name = _('red flag detection')
        verbose_name_plural = _('red flag detections')

    def __str__(self):
        return f"Red Flags for {self.triage_session.patient_token[:8]} - {self.detected_flags_count} detected"

    def count_red_flags(self):
        """Count total red flags detected"""
        flags = [
            self.airway_obstruction,
            self.severe_breathing_difficulty,
            self.chest_indrawing,
            self.severe_bleeding,
            self.signs_of_shock,
            self.unconscious,
            self.convulsions,
            self.confusion,
            self.stroke_symptoms,
            self.unable_to_drink,
            self.vomits_everything,
            self.lethargic_floppy,
            self.severe_pain,
            self.pregnancy_emergency,
        ]
        self.detected_flags_count = sum(flags)
        return self.detected_flags_count
    
    def get_detected_flag_names(self):
        """Get list of detected flag names"""
        flag_fields = [
            'airway_obstruction', 'severe_breathing_difficulty', 'chest_indrawing',
            'severe_bleeding', 'signs_of_shock', 'unconscious', 'convulsions',
            'confusion', 'stroke_symptoms', 'unable_to_drink', 'vomits_everything',
            'lethargic_floppy', 'severe_pain', 'pregnancy_emergency'
        ]
        
        detected = []
        for field in flag_fields:
            if getattr(self, field, False):
                # Convert field name to readable format
                readable = field.replace('_', ' ').title()
                detected.append(readable)
        
        return detected


# ============================================================================
# RISK CLASSIFICATION - UPDATED FOR COMPLAINT-BASED LOGIC
# ============================================================================

class RiskClassification(BaseModel):
    """
    AI-powered risk classification - UPDATED
    Now considers: complaint group, age, red flags, symptom indicators
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

    # Feature importance (now includes complaint_group, age_group)
    feature_importance = models.JSONField(
        _('feature importance'),
        null=True,
        blank=True,
        help_text=_('Features that contributed to classification including complaint_group, age_group')
    )

    # Input embeddings
    complaint_embedding = models.JSONField(
        _('complaint embedding'),
        null=True,
        blank=True,
        help_text=_('Complaint text embeddings (for analysis)')
    )

    class Meta:
        verbose_name = _('risk classification')
        verbose_name_plural = _('risk classifications')

    def __str__(self):
        return f"Risk: {self.ai_risk_level} ({self.confidence_score:.2f}) - {self.triage_session.patient_token[:8]}"


# ============================================================================
# CLINICAL CONTEXT - UPDATED FOR AGE & RISK MODIFIERS
# ============================================================================

class ClinicalContext(BaseModel):
    """
    Clinical context adjustments - UPDATED
    Now includes age-specific and population-based modifiers
    """

    triage_session = models.OneToOneField(
        TriageSession,
        on_delete=models.CASCADE,
        related_name='clinical_context',
        verbose_name=_('triage session')
    )

    # Age-based modifiers
    age_modifier = models.FloatField(
        _('age modifier'),
        default=0.0,
        help_text=_(
            'Risk adjustment for age: '
            'newborn/infant +0.2, elderly +0.15, child_1_5 +0.1'
        )
    )

    # Population-based modifiers
    pregnancy_modifier = models.FloatField(
        _('pregnancy modifier'),
        default=0.0,
        help_text=_('Risk adjustment for pregnancy')
    )

    chronic_condition_modifier = models.FloatField(
        _('chronic condition modifier'),
        default=0.0,
        help_text=_('Risk adjustment for chronic conditions')
    )

    immunocompromised_modifier = models.FloatField(
        _('immunocompromised modifier'),
        default=0.0,
        help_text=_('Risk adjustment for immunocompromised status')
    )

    medication_modifier = models.FloatField(
        _('medication modifier'),
        default=0.0,
        help_text=_('Risk adjustment for current medications')
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

    conservative_bias_applied = models.BooleanField(
        _('conservative bias applied'),
        default=False,
        help_text=_('Whether conservative bias was applied (never downgrade)')
    )

    class Meta:
        verbose_name = _('clinical context')
        verbose_name_plural = _('clinical contexts')

    def __str__(self):
        return f"Context for {self.triage_session.patient_token[:8]} - Adjustment: {self.total_risk_adjustment:+.2f}"


# ============================================================================
# TRIAGE DECISION - UNCHANGED (still the final synthesis)
# ============================================================================

class TriageDecision(BaseModel):
    """
    Final triage decision synthesis
    Combines: red flags + AI risk + clinical context + complaint group
    """

    triage_session = models.OneToOneField(
        TriageSession,
        on_delete=models.CASCADE,
        related_name='triage_decision',
        verbose_name=_('triage session')
    )

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

    decision_basis = models.CharField(
        _('decision basis'),
        max_length=50,
        choices=[
            ('red_flag_override', _('Red Flag Override')),
            ('age_risk_modifier', _('Age/Risk Modifier')),
            ('ai_primary', _('AI Primary')),
            ('clinical_adjustment', _('Clinical Adjustment')),
            ('conservative_bias', _('Conservative Bias')),
        ],
        help_text=_('Primary basis for final decision')
    )

    recommended_action = models.TextField(
        _('recommended action'),
        help_text=_('Recommended next steps for patient')
    )

    facility_type_recommendation = models.CharField(
        _('facility type recommendation'),
        max_length=50,
        choices=[
            ('emergency', _('Emergency Department - IMMEDIATE')),
            ('hospital', _('Hospital - Urgent')),
            ('health_center', _('Health Center - Soon')),
            ('clinic', _('Clinic - Routine')),
            ('self_care', _('Self-care with monitoring')),
        ],
        null=True,
        blank=True
    )

    decision_timestamp = models.DateTimeField(
        _('decision timestamp'),
        auto_now_add=True
    )

    decision_reasoning = models.TextField(
        _('decision reasoning'),
        help_text=_('Detailed explanation of how decision was reached (audit trail)')
    )

    disclaimers = models.JSONField(
        default=list,
        help_text=_('Disclaimers shown to patient')
    )

    class Meta:
        verbose_name = _('triage decision')
        verbose_name_plural = _('triage decisions')

    def __str__(self):
        return f"Decision: {self.final_risk_level} - {self.triage_session.patient_token[:8]}"


# ============================================================================
# AGENT COMMUNICATION - UNCHANGED
# ============================================================================

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

    target_agent = models.CharField(
        _('target agent'),
        max_length=50,
        choices=[
            ('follow_up', _('Follow-up Agent')),
            ('facility_matching', _('Facility Matching Agent')),
            ('notification', _('Notification Agent')),
        ]
    )

    payload = models.JSONField(
        _('payload'),
        help_text=_('JSON payload sent to target agent')
    )

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

    response_data = models.JSONField(
        _('response data'),
        null=True,
        blank=True,
        help_text=_('Response received from target agent')
    )

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