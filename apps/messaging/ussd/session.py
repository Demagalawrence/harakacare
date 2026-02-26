"""
USSD Session Management
"""

from datetime import datetime
from typing import Dict
from django.core.cache import cache

from apps.messaging.ussd.menus import USSDMenu


class USSDSession:
    """Manages USSD session state in cache."""

    def __init__(self, session_id: str, phone_number: str):
        self.session_id = session_id
        self.phone_number = phone_number
        self.current_menu = USSDMenu.WELCOME.value
        self.language = "en"
        self.data: Dict = {
            "patient_token": None,
            "complaint_group": None,
            "age_group": None,
            "sex": None,
            "symptom_severity": None,
            "symptom_duration": None,
            "district": None,
            "pregnancy_status": None,
            "consent_given": False,
            "emergency_detected": False,
        }
        self.step = 0
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()

    def update(self, **kwargs):
        self.data.update(kwargs)
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "phone_number": self.phone_number,
            "current_menu": self.current_menu,
            "language": self.language,
            "data": self.data,
            "step": self.step,
            # Store as ISO strings so JSON serialisation never breaks
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class SessionManager:
    """Manages USSD sessions using Django cache."""

    SESSION_TIMEOUT = 300  # 5 minutes (USSD sessions are short-lived)

    @staticmethod
    def get_session(session_id: str, phone_number: str) -> USSDSession:
        """Return an existing session or create a fresh one."""
        cache_key = f"ussd_session:{session_id}"
        session_data = cache.get(cache_key)

        if session_data:
            session = USSDSession(
                session_id=session_data["session_id"],
                phone_number=session_data["phone_number"],
            )
            session.current_menu = session_data["current_menu"]
            session.language = session_data["language"]
            session.data = session_data["data"]
            session.step = session_data["step"]
            # Deserialise datetimes properly so callers can use them as datetime objects
            session.created_at = datetime.fromisoformat(session_data["created_at"])
            session.updated_at = datetime.fromisoformat(session_data["updated_at"])
            return session

        # First request for this session_id — create and persist it
        session = USSDSession(session_id, phone_number)
        SessionManager.save_session(session)
        return session

    @staticmethod
    def save_session(session: USSDSession) -> None:
        cache_key = f"ussd_session:{session.session_id}"
        cache.set(cache_key, session.to_dict(), SessionManager.SESSION_TIMEOUT)

    @staticmethod
    def delete_session(session_id: str) -> None:
        cache_key = f"ussd_session:{session_id}"
        cache.delete(cache_key)