from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone

from rest_framework.authentication import SessionAuthentication

from .models import Facility
from .serializers import FacilitySerializer

from django.contrib.auth import authenticate, login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return


@api_view(['POST'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([AllowAny])
@csrf_exempt
def facility_login(request):
    """Facility dashboard login (session-based)"""
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response({'error': 'username and password are required'}, status=400)

    user = authenticate(request, username=username, password=password)
    if user is None:
        return Response({'error': 'Invalid credentials'}, status=401)

    try:
        facility = Facility.objects.get(user=user)
    except Facility.DoesNotExist:
        return Response({'error': 'User is not linked to a facility'}, status=403)

    login(request, user)
    return Response({
        'success': True,
        'facility': {
            'id': facility.id,
            'name': facility.name,
            'facility_type': facility.facility_type,
        }
    })


@api_view(['POST'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
@csrf_exempt
def facility_logout(request):
    """Logout facility dashboard"""
    logout(request)
    return Response({'success': True})


@api_view(['GET'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([AllowAny])
@csrf_exempt
def facility_whoami(request):
    """Return current logged-in facility"""
    if not request.user.is_authenticated:
        return Response({'authenticated': False, 'error': 'Not authenticated'}, status=401)
    
    try:
        facility = Facility.objects.get(user=request.user)
    except Facility.DoesNotExist:
        return Response({'error': 'User is not linked to a facility'}, status=403)

    return Response({
        'authenticated': True,
        'facility': {
            'id': facility.id,
            'name': facility.name,
            'facility_type': facility.facility_type,
        }
    })


@api_view(['GET'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([AllowAny])
@csrf_exempt
def get_cases(request):
    """Get cases for facility dashboard (scoped to logged-in facility)"""
    if not request.user.is_authenticated:
        return Response({'error': 'Not authenticated'}, status=401)
    
    try:
        facility = Facility.objects.get(user=request.user)
    except Facility.DoesNotExist:
        return Response({'error': 'User is not linked to a facility'}, status=403)

    from .models import FacilityRouting

    routings = FacilityRouting.objects.filter(assigned_facility=facility).order_by('-triage_received_at')[:50]
    data = []
    for r in routings:
        data.append({
            'id': f'FR-{r.id}',
            'patientToken': r.patient_token,
            'primarySymptom': r.primary_symptom,
            'riskLevel': r.risk_level,
            'status': r.routing_status,
            'village': r.patient_village,
            'district': r.patient_district,
            'createdAt': r.triage_received_at.isoformat() if r.triage_received_at else None,
            'bookingType': r.booking_type,
        })

    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def confirm_case(request, case_id):
    """Confirm a case"""
    try:
        routing_id = case_id.replace('FR-', '')
        from .models import FacilityRouting
        routing = FacilityRouting.objects.select_related('assigned_facility').get(id=int(routing_id))

        facility = Facility.objects.get(user=request.user)
        if routing.assigned_facility_id != facility.id:
            return Response({'error': 'Not allowed'}, status=403)

        routing.routing_status = FacilityRouting.RoutingStatus.CONFIRMED
        routing.facility_confirmed_at = timezone.now()
        routing.save(update_fields=['routing_status', 'facility_confirmed_at', 'updated_at'])

        return Response({
            'id': case_id,
            'status': 'confirmed',
            'confirmedAt': routing.facility_confirmed_at.isoformat() if routing.facility_confirmed_at else None,
            'message': 'Case confirmed successfully'
        })

    except FacilityRouting.DoesNotExist:
        return Response({'error': 'Case not found'}, status=404)
    except Facility.DoesNotExist:
        return Response({'error': 'User is not linked to a facility'}, status=403)
    except ValueError:
        return Response({'error': 'Invalid case id'}, status=400)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_case(request, case_id):
    """Reject a case"""
    try:
        routing_id = case_id.replace('FR-', '')
        from .models import FacilityRouting
        routing = FacilityRouting.objects.select_related('assigned_facility').get(id=int(routing_id))

        facility = Facility.objects.get(user=request.user)
        if routing.assigned_facility_id != facility.id:
            return Response({'error': 'Not allowed'}, status=403)

        routing.routing_status = FacilityRouting.RoutingStatus.REJECTED
        routing.save(update_fields=['routing_status', 'updated_at'])

        return Response({
            'id': case_id,
            'status': 'rejected',
            'message': 'Case rejected successfully'
        })

    except FacilityRouting.DoesNotExist:
        return Response({'error': 'Case not found'}, status=404)
    except Facility.DoesNotExist:
        return Response({'error': 'User is not linked to a facility'}, status=403)
    except ValueError:
        return Response({'error': 'Invalid case id'}, status=400)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def acknowledge_case(request, case_id):
    """Acknowledge a case"""
    try:
        routing_id = case_id.replace('FR-', '')
        from .models import FacilityRouting
        routing = FacilityRouting.objects.select_related('assigned_facility').get(id=int(routing_id))

        facility = Facility.objects.get(user=request.user)
        if routing.assigned_facility_id != facility.id:
            return Response({'error': 'Not allowed'}, status=403)

        routing.routing_status = FacilityRouting.RoutingStatus.NOTIFIED
        routing.save(update_fields=['routing_status', 'updated_at'])

        return Response({
            'id': case_id,
            'status': 'acknowledged',
            'message': 'Case acknowledged successfully'
        })

    except FacilityRouting.DoesNotExist:
        return Response({'error': 'Case not found'}, status=404)
    except Facility.DoesNotExist:
        return Response({'error': 'User is not linked to a facility'}, status=403)
    except ValueError:
        return Response({'error': 'Invalid case id'}, status=400)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_case(request, case_id):
    """Delete a case"""
    try:
        routing_id = case_id.replace('FR-', '')
        from .models import FacilityRouting
        routing = FacilityRouting.objects.select_related('assigned_facility').get(id=int(routing_id))

        facility = Facility.objects.get(user=request.user)
        if routing.assigned_facility_id != facility.id:
            return Response({'error': 'Not allowed'}, status=403)

        routing.delete()

        return Response({'id': case_id, 'message': 'Case deleted successfully'})

    except FacilityRouting.DoesNotExist:
        return Response({'error': 'Case not found'}, status=404)
    except Facility.DoesNotExist:
        return Response({'error': 'User is not linked to a facility'}, status=403)
    except ValueError as e:
        return Response({'error': f'Invalid case ID format: {e}'}, status=400)
    except Exception as e:
        print(f"Error deleting case {case_id}: {e}")
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([AllowAny])
@csrf_exempt
def get_stats(request):
    """Get stats for facility dashboard"""
    if not request.user.is_authenticated:
        return Response({'error': 'Not authenticated'}, status=401)
    
    try:
        facility = Facility.objects.get(user=request.user)
    except Facility.DoesNotExist:
        return Response({'error': 'User is not linked to a facility'}, status=403)

    from .models import FacilityRouting
    routings = FacilityRouting.objects.filter(assigned_facility=facility)

    total = routings.count()
    high = routings.filter(risk_level='high').count()
    medium = routings.filter(risk_level='medium').count()
    low = routings.filter(risk_level='low').count()
    pending = routings.filter(routing_status=FacilityRouting.RoutingStatus.PENDING).count()
    confirmed = routings.filter(routing_status=FacilityRouting.RoutingStatus.CONFIRMED).count()
    acknowledged = routings.filter(routing_status=FacilityRouting.RoutingStatus.NOTIFIED).count()
    rejected = routings.filter(routing_status=FacilityRouting.RoutingStatus.REJECTED).count()
    
    return Response({
        'total': total,
        'high': high,
        'medium': medium,
        'low': low,
        'pending': pending,
        'confirmed': confirmed,
        'acknowledged': acknowledged,
        'rejected': rejected
    })


class FacilityViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Facility model providing CRUD operations.
    
    API Endpoints:
    - GET /api/facilities/ - List all facilities
    - POST /api/facilities/ - Create new facility
    - GET /api/facilities/{id}/ - Retrieve specific facility
    - PUT /api/facilities/{id}/ - Update facility
    - PATCH /api/facilities/{id}/ - Partially update facility
    - DELETE /api/facilities/{id}/ - Delete facility
    """
    
    queryset = Facility.objects.all()
    serializer_class = FacilitySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active', 'facility_type']
    search_fields = ['name', 'address', 'facility_type']
    ordering_fields = ['name', 'facility_type', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        """
        Optionally filter out inactive facilities unless explicitly requested.
        """
        queryset = Facility.objects.all()
        show_inactive = self.request.query_params.get('show_inactive', 'false').lower() == 'true'
        
        if not show_inactive:
            queryset = queryset.filter(is_active=True)
            
        return queryset
    
    def perform_destroy(self, instance):
        """
        Soft delete facility by setting is_active to False instead of actual deletion.
        """
        instance.is_active = False
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)