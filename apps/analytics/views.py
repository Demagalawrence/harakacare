"""
Analytics views for HarakaCare.
"""
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET"])
@login_required
def analytics_overview(request):
    """
    GET /api/v1/analytics/
    Returns aggregated analytics overview (no patient-identifiable data).
    """
    return JsonResponse({
        'message': 'Analytics module',
        'status': 'available',
        'note': 'Full analytics implementation in progress',
        'endpoints': {
            'overview': '/api/v1/analytics/',
            'risk_distribution': '/api/v1/analytics/risk-distribution/',
            'symptom_trends': '/api/v1/analytics/symptom-trends/',
            'referral_trends': '/api/v1/analytics/referral-trends/',
            'facility_workload': '/api/v1/analytics/facility-workload/',
        }
    })
