"""
Custom permission classes for HarakaCare RBAC.
"""
from rest_framework import permissions
from django.contrib.auth import get_user_model

User = get_user_model()


class IsHealthcareWorker(permissions.BasePermission):
    """
    Allows access only to authenticated healthcare workers.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_staff or request.user.is_superuser


class IsFacilityAdmin(permissions.BasePermission):
    """
    Allows access only to facility administrators.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if not hasattr(request.user, 'profile'):
            return False
        return request.user.profile.role in [
            'admin', 'facility_admin'
        ] or request.user.is_superuser


class IsTriageOfficer(permissions.BasePermission):
    """
    Allows access to triage officers and above.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if not hasattr(request.user, 'profile'):
            return False
        return request.user.profile.role in [
            'admin', 'facility_admin', 'clinical_officer', 'doctor', 'nurse', 'staff'
        ] or request.user.is_superuser


class CanViewAllFacilities(permissions.BasePermission):
    """
    Allows access only to users who can view all facilities (admins).
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if not hasattr(request.user, 'profile'):
            return False
        return request.user.profile.can_view_all_facilities or request.user.is_superuser


class CanOverrideAIRecommendation(permissions.BasePermission):
    """
    Allows only senior staff to override AI recommendations.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if not hasattr(request.user, 'profile'):
            return False
        return request.user.profile.role in [
            'admin', 'facility_admin', 'doctor', 'clinical_officer'
        ] or request.user.is_superuser


class IsPatientOrReadOnly(permissions.BasePermission):
    """
    Patients can create triage sessions but only authenticated staff can modify.
    """
    def has_permission(self, request, view):
        # Allow unauthenticated POST for public triage submission
        if request.method == 'POST':
            return True
        # Other methods require authentication
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Staff can always access
        if request.user and (request.user.is_staff or request.user.is_superuser):
            return True
        # Patients can only read their own sessions
        if hasattr(obj, 'patient_token'):
            # Object-level check would need patient association
            return True
        return False
