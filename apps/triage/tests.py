"""
Triage Agent Tests
Comprehensive tests for triage agent functionality
"""

import pytest
from django.urls import reverse
from rest_framework import status
from apps.triage.models import TriageSession, RedFlagDetection, TriageDecision
from apps.triage.tools.intake_validation import IntakeValidationTool
from apps.triage.tools.red_flag_detection import RedFlagDetectionTool
from conversations.models import Conversation, Message
import json



@pytest.mark.django_db
class TestIntakeValidationTool:
    """Test Tool 1: Intake & Validation"""

    def test_valid_intake_data(self):
        """Test validation with valid complete data"""
        data = {
            'age_range': '18_30',
            'sex': 'male',
            'district': 'Kampala',
            'subcounty': 'Central',
            'primary_symptom': 'fever',
            'secondary_symptoms': ['cough', 'fatigue'],
            'symptom_severity': 'moderate',
            'symptom_duration': '1_3_days',
            'condition_occurrence': 'first_occurrence',
            'chronic_conditions': ['none'],
            'consent_medical_triage': True,
            'consent_data_sharing': True,
            'consent_follow_up': True,
        }

        tool = IntakeValidationTool()
        is_valid, cleaned_data, errors = tool.validate(data)

        assert is_valid is True
        assert len(errors) == 0
        assert 'patient_token' in cleaned_data
        assert cleaned_data['patient_token'].startswith('PT-')

    def test_missing_required_fields(self):
        """Test validation fails with missing required fields"""
        data = {
            'age_range': '18_30',
            # Missing other required fields
        }

        tool = IntakeValidationTool()
        is_valid, cleaned_data, errors = tool.validate(data)

        assert is_valid is False
        assert len(errors) > 0
        assert any('district' in err.lower() for err in errors)

    def test_invalid_field_choices(self):
        """Test validation fails with invalid choices"""
        data = {
            'age_range': 'invalid_age',
            'district': 'Kampala',
            'primary_symptom': 'fever',
            'symptom_severity': 'moderate',
            'symptom_duration': '1_3_days',
            'condition_occurrence': 'first_occurrence',
            'consent_medical_triage': True,
            'consent_data_sharing': True,
            'consent_follow_up': True,
        }

        tool = IntakeValidationTool()
        is_valid, cleaned_data, errors = tool.validate(data)

        assert is_valid is False
        assert any('age_range' in err for err in errors)

    def test_consent_validation(self):
        """Test all consents must be True"""
        data = {
            'age_range': '18_30',
            'district': 'Kampala',
            'primary_symptom': 'fever',
            'symptom_severity': 'moderate',
            'symptom_duration': '1_3_days',
            'condition_occurrence': 'first_occurrence',
            'consent_medical_triage': True,
            'consent_data_sharing': False,  # Not consented
            'consent_follow_up': True,
        }

        tool = IntakeValidationTool()
        is_valid, cleaned_data, errors = tool.validate(data)

        assert is_valid is False
        assert any('consent' in err.lower() for err in errors)

    def test_red_flag_detection_in_intake(self):
        """Test red flag detection during intake"""
        data = {
            'primary_symptom': 'chest_pain',
            'secondary_symptoms': ['difficulty_breathing'],
            'symptom_severity': 'very_severe',
        }

        tool = IntakeValidationTool()
        red_flags = tool.detect_red_flags(data)

        assert len(red_flags) > 0
        assert 'chest_pain' in red_flags
        assert 'difficulty_breathing' in red_flags


@pytest.mark.django_db
class TestRedFlagDetectionTool:
    """Test Tool 3: Red-Flag Detection"""

    def test_critical_red_flag_chest_pain(self):
        """Test detection of critical red flag: chest pain"""
        data = {
            'primary_symptom': 'chest_pain',
            'symptom_severity': 'severe',
            'age_range': '51_plus',
        }

        tool = RedFlagDetectionTool()
        result = tool.detect(data)

        assert result['has_red_flags'] is True
        assert result['emergency_override'] is True
        assert 'chest_pain' in result['detected_flags']
        assert result['highest_severity'] == 'critical'

    def test_difficulty_breathing_detection(self):
        """Test difficulty breathing detection"""
        data = {
            'primary_symptom': 'difficulty_breathing',
            'symptom_severity': 'very_severe',
            'age_range': 'under_5',
        }

        tool = RedFlagDetectionTool()
        result = tool.detect(data)

        assert result['has_red_flags'] is True
        assert result['emergency_override'] is True
        assert 'difficulty_breathing' in result['detected_flags']

    def test_no_red_flags(self):
        """Test case with no red flags"""
        data = {
            'primary_symptom': 'headache',
            'symptom_severity': 'mild',
            'age_range': '18_30',
            'secondary_symptoms': ['fatigue']
        }

        tool = RedFlagDetectionTool()
        result = tool.detect(data)

        assert result['has_red_flags'] is False
        assert result['emergency_override'] is False
        assert len(result['detected_flags']) == 0

    def test_age_specific_red_flags_child(self):
        """Test age-specific red flags for children"""
        data = {
            'primary_symptom': 'fever',
            'symptom_severity': 'very_severe',
            'age_range': 'under_5',
        }

        tool = RedFlagDetectionTool()
        result = tool.detect(data)

        assert result['has_red_flags'] is True
        # Should detect pediatric emergency

    def test_emergency_message_generation(self):
        """Test emergency message generation"""
        data = {
            'primary_symptom': 'chest_pain',
            'symptom_severity': 'severe',
        }

        tool = RedFlagDetectionTool()
        result = tool.detect(data)
        message = tool.get_emergency_message(result)

        assert len(message) > 0
        assert 'EMERGENCY' in message.upper() or 'URGENT' in message.upper()


@pytest.mark.django_db
class TestTriageAPIEndpoints:
    """Test Triage REST API endpoints"""

    def test_start_triage_session(self, api_client):
        """Test starting a new triage session"""
        url = reverse('triage:start')
        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'patient_token' in response.data
        assert response.data['patient_token'].startswith('PT-')

    def test_submit_triage_valid_data(self, api_client):
        """Test submitting valid triage data"""
        # Start session
        start_url = reverse('triage:start')
        start_response = api_client.post(start_url)
        patient_token = start_response.data['patient_token']

        # Submit triage
        submit_url = reverse('triage:submit', kwargs={'patient_token': patient_token})
        triage_data = {
            'age_range': '18_30',
            'sex': 'female',
            'district': 'Kampala',
            'subcounty': 'Central',
            'primary_symptom': 'headache',
            'secondary_symptoms': ['fatigue'],
            'symptom_severity': 'moderate',
            'symptom_duration': '1_3_days',
            'symptom_pattern': 'staying_same',
            'condition_occurrence': 'first_occurrence',
            'chronic_conditions': ['none'],
            'current_medication': 'no',
            'has_allergies': 'no',
            'pregnancy_status': 'no',
            'consent_medical_triage': True,
            'consent_data_sharing': True,
            'consent_follow_up': True,
            'channel': 'web'
        }

        response = api_client.post(submit_url, triage_data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert 'risk_level' in response.data
        assert 'patient_token' in response.data
        assert response.data['patient_token'] == patient_token

    def test_submit_triage_emergency_case(self, api_client):
        """Test submitting emergency case with red flags"""
        start_response = api_client.post(reverse('triage:start'))
        patient_token = start_response.data['patient_token']

        submit_url = reverse('triage:submit', kwargs={'patient_token': patient_token})
        emergency_data = {
            'age_range': '51_plus',
            'sex': 'male',
            'district': 'Kampala',
            'primary_symptom': 'chest_pain',
            'secondary_symptoms': ['difficulty_breathing'],
            'symptom_severity': 'very_severe',
            'symptom_duration': 'today',
            'condition_occurrence': 'first_occurrence',
            'chronic_conditions': ['heart_disease'],
            'consent_medical_triage': True,
            'consent_data_sharing': True,
            'consent_follow_up': True,
        }

        response = api_client.post(submit_url, emergency_data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['has_red_flags'] is True
        assert response.data['risk_level'] == 'high'
        assert len(response.data['emergency_message']) > 0

    def test_submit_triage_missing_consent(self, api_client):
        """Test submission fails without consent"""
        start_response = api_client.post(reverse('triage:start'))
        patient_token = start_response.data['patient_token']

        submit_url = reverse('triage:submit', kwargs={'patient_token': patient_token})
        data_without_consent = {
            'age_range': '18_30',
            'district': 'Kampala',
            'primary_symptom': 'fever',
            'symptom_severity': 'moderate',
            'symptom_duration': '1_3_days',
            'condition_occurrence': 'first_occurrence',
            'consent_medical_triage': False,  # Not consented
            'consent_data_sharing': True,
            'consent_follow_up': True,
        }

        response = api_client.post(submit_url, data_without_consent, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data or 'errors' in response.data
        
    def test_get_triage_result(self, api_client):
        """Test retrieving triage results"""
        # Create completed session
        session = TriageSession.objects.create(
            patient_token='PT-TEST123',
            session_status=TriageSession.SessionStatus.COMPLETED,
            age_range='18_30',
            district='Kampala',
            primary_symptom='fever',
            symptom_severity='moderate',
            symptom_duration='1_3_days',
            condition_occurrence='first_occurrence',
            risk_level='low',
            risk_confidence=0.85,
            consent_medical_triage=True,
            consent_data_sharing=True,
            consent_follow_up=True
        )

        # Create decision
        TriageDecision.objects.create(
            triage_session=session,
            final_risk_level='low',
            follow_up_priority='routine',
            decision_basis='ai_primary',
            recommended_action='Monitor symptoms and self-care',
            facility_type_recommendation='self_care',
            decision_reasoning='Low risk based on mild symptoms',
            disclaimers=['This is not a diagnosis']
        )

        url = reverse('triage:result', kwargs={'patient_token': 'PT-TEST123'})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['patient_token'] == 'PT-TEST123'
        assert response.data['risk_level'] == 'low'

    def test_get_triage_status(self, api_client):
        """Test checking triage status"""
        session = TriageSession.objects.create(
            patient_token='PT-STATUS123',
            session_status=TriageSession.SessionStatus.IN_PROGRESS,
            age_range='18_30',
            district='Kampala',
            primary_symptom='fever',
            symptom_severity='moderate',
            symptom_duration='1_3_days',
            condition_occurrence='first_occurrence',
            consent_medical_triage=True,
            consent_data_sharing=True,
            consent_follow_up=True
        )

        url = reverse('triage:status', kwargs={'patient_token': 'PT-STATUS123'})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['session_status'] == 'in_progress'
        assert response.data['assessment_completed'] is False


@pytest.mark.django_db
class TestTriageModels:
    """Test Triage models"""

    def test_triage_session_creation(self):
        """Test creating a triage session"""
        session = TriageSession.objects.create(
            patient_token='PT-MODEL123',
            age_range='18_30',
            district='Kampala',
            primary_symptom='fever',
            symptom_severity='moderate',
            symptom_duration='1_3_days',
            condition_occurrence='first_occurrence',
            consent_medical_triage=True,
            consent_data_sharing=True,
            consent_follow_up=True
        )

        assert session.patient_token == 'PT-MODEL123'
        assert session.is_emergency is False

    def test_triage_session_with_red_flags(self):
        """Test session with red flags"""
        session = TriageSession.objects.create(
            patient_token='PT-EMERGENCY123',
            age_range='51_plus',
            district='Kampala',
            primary_symptom='chest_pain',
            symptom_severity='very_severe',
            symptom_duration='today',
            condition_occurrence='first_occurrence',
            has_red_flags=True,
            red_flags=['chest_pain', 'difficulty_breathing'],
            risk_level='high',
            consent_medical_triage=True,
            consent_data_sharing=True,
            consent_follow_up=True
        )

        assert session.is_emergency is True
        assert session.needs_immediate_attention is True

    def test_symptom_summary_generation(self):
        """Test symptom summary generation"""
        session = TriageSession.objects.create(
            patient_token='PT-SUMMARY123',
            age_range='18_30',
            district='Kampala',
            primary_symptom='fever',
            secondary_symptoms=['cough', 'fatigue'],
            symptom_severity='moderate',
            symptom_duration='1_3_days',
            condition_occurrence='first_occurrence',
            consent_medical_triage=True,
            consent_data_sharing=True,
            consent_follow_up=True
        )

        summary = session.generate_symptom_summary()

        assert 'fever' in summary.lower()
        assert 'moderate' in summary.lower()
        assert '1-3 days' in summary.lower()