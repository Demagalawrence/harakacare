from django.utils import timezone
from apps.triage.models import TriageSession, TriageDecision

from apps.triage.models import (
    TriageSession,
    RedFlagDetection,
    RiskClassification,
    TriageDecision,
    AgentCommunicationLog,
    ClinicalContext
)
from apps.triage.serializers import (
    TriageIntakeSerializer,
    TriageSessionSerializer,
    TriageResultSerializer,
    TriageStatusSerializer
)

# Import tools
from apps.triage.tools.intake_validation import IntakeValidationTool
from apps.triage.tools.red_flag_detection import RedFlagDetectionTool
from apps.triage.tools.risk_classification import RiskClassificationTool
from apps.triage.tools.clinical_context import ClinicalContextTool
from apps.triage.tools.decision_synthesis import DecisionSynthesisTool
from apps.triage.tools.agent_communication import AgentCommunicationTool


class TriageOrchestrator:

    @staticmethod
    def run(patient_token: str, cleaned_data: dict):
        from apps.triage.models import TriageSession
        from django.utils import timezone

        # Get or create session
        cleaned_data.pop("session_status", None)
        cleaned_data.pop("patient_token", None)
        cleaned_data.pop("assessment_completed_at", None)

        # The ONLY place a medical session should ever be created
        session, created = TriageSession.objects.get_or_create(
            patient_token=patient_token,
            defaults={
                "session_status": TriageSession.SessionStatus.IN_PROGRESS
            }
        )

        # Update medical information
        for field, value in cleaned_data.items():
            if hasattr(session, field):
                setattr(session, field, value)

        session.session_status = TriageSession.SessionStatus.IN_PROGRESS
        session.save()
        # ---------------- RED FLAG ----------------
        red_flag_tool = RedFlagDetectionTool()
        red_flag_result = red_flag_tool.detect(cleaned_data)

        session.has_red_flags = red_flag_result['has_red_flags']
        session.red_flags = red_flag_result['detected_flags']
        session.save(update_fields=['has_red_flags', 'red_flags'])

        # ---------------- RISK ----------------
        if red_flag_result['emergency_override']:
            ai_risk_level = 'high'
            risk_confidence = 1.0
        else:
            risk_tool = RiskClassificationTool()
            risk_result = risk_tool.classify(session, cleaned_data)
            ai_risk_level = risk_result['risk_level']
            risk_confidence = risk_result['confidence']

        # ---------------- CONTEXT ----------------
        context_tool = ClinicalContextTool()
        context_result = context_tool.adjust_risk(
            session, cleaned_data, ai_risk_level, red_flag_result
        )

        # ---------------- DECISION ----------------
        # ---------------- DECISION ----------------
        decision_tool = DecisionSynthesisTool()
        final_decision = decision_tool.synthesize(
            session=session,
            red_flag_result=red_flag_result,
            ai_risk_level=ai_risk_level,
            context_result=context_result
        )

        # ✅ THIS WAS MISSING - persist the decision record
        TriageDecision.objects.update_or_create(
            triage_session=session,
            defaults={
                'final_risk_level': final_decision['risk_level'],
                'follow_up_priority': final_decision['follow_up_priority'],
                'decision_basis': final_decision['decision_basis'],
                'recommended_action': final_decision['recommended_action'],
                'facility_type_recommendation': final_decision['facility_type'],
                'decision_reasoning': final_decision['reasoning'],
                'disclaimers': final_decision['disclaimers'],
            }
        )

        # ... rest of session.save()
        session.risk_level = final_decision['risk_level']
        session.risk_confidence = risk_confidence
        session.follow_up_priority = final_decision['follow_up_priority']
        session.assessment_completed_at = timezone.now()
        session.session_status = TriageSession.SessionStatus.COMPLETED
        session.save()

        return session, final_decision, red_flag_result
    print("SESSION EXISTS AFTER RUN:", TriageSession.objects.filter(patient_token=['patient_token']).exists())

