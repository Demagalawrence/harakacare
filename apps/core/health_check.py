from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.models import User
from apps.facilities.models import Facility


@csrf_exempt
@require_http_methods(["GET"])
def health_check(request):
    """Health check endpoint that verifies users exist"""
    try:
        # Check if users exist
        kampala_user = User.objects.filter(username='kampala_staff').exists()
        mulago_user = User.objects.filter(username='mulago_staff').exists()
        luwero_user = User.objects.filter(username='luwero_staff').exists()
        admin_user = User.objects.filter(username='admin').exists()
        
        # Check if facilities exist
        kampala_facility = Facility.objects.filter(name='Kampala Referral Hospital').exists()
        mulago_facility = Facility.objects.filter(name='Mulago National Hospital').exists()
        luwero_facility = Facility.objects.filter(name='Luwero General Hospital').exists()
        
        all_users_ready = kampala_user and mulago_user and luwero_user and admin_user
        all_facilities_ready = kampala_facility and mulago_facility and luwero_facility
        
        return JsonResponse({
            'status': 'healthy' if all_users_ready and all_facilities_ready else 'unhealthy',
            'users': {
                'kampala_staff': kampala_user,
                'mulago_staff': mulago_user,
                'luwero_staff': luwero_user,
                'admin': admin_user
            },
            'facilities': {
                'kampala_referral': kampala_facility,
                'mulago_national': mulago_facility,
                'luwero_general': luwero_facility
            },
            'ready': all_users_ready and all_facilities_ready,
            'message': 'All users and facilities are ready' if all_users_ready and all_facilities_ready else 'Setup required - visit /setup-database/'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Health check failed: {str(e)}'
        }, status=500)
