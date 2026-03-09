from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.contrib.auth import authenticate, login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from rest_framework.authentication import SessionAuthentication
from .models import Facility, FacilityRouting
from .serializers import FacilitySerializer
from django.utils import timezone


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return


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
        """Filter facilities based on user profile"""
        try:
            user_profile = self.request.user.profile
            if user_profile.facility:
                # User can only see their assigned facility
                return Facility.objects.filter(id=user_profile.facility.id)
            elif user_profile.can_view_all_facilities:
                # User can see all facilities
                return Facility.objects.all()
            else:
                # No facility assigned and no special permissions
                return Facility.objects.none()
        except AttributeError:
            # No profile found - return all for superusers, none for others
            if self.request.user.is_superuser:
                return Facility.objects.all()
            return Facility.objects.none()


# Authentication views
@api_view(['POST'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([AllowAny])
def facility_login(request):
    """Login facility user"""
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response({'error': 'Username and password required'}, status=400)
    
    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        
        # Try to get facility from user profile
        try:
            user_profile = request.user.profile
            if user_profile.facility:
                facility = user_profile.facility
                facility_data = {
                    'id': facility.id,
                    'name': facility.name,
                    'facility_type': facility.facility_type,
                    'district': facility.district
                }
            else:
                # Fallback: get first facility or create default response
                facility = Facility.objects.first()
                if facility:
                    facility_data = {
                        'id': facility.id,
                        'name': facility.name,
                        'facility_type': facility.facility_type,
                        'district': facility.district
                    }
                else:
                    facility_data = {
                        'id': 1,
                        'name': 'Default Facility',
                        'facility_type': 'clinic',
                        'district': 'Kampala'
                    }
        except (AttributeError,):
            # Fallback: get first facility or create default response
            facility = Facility.objects.first()
            if facility:
                facility_data = {
                    'id': facility.id,
                    'name': facility.name,
                    'facility_type': facility.facility_type,
                    'district': facility.district
                }
            else:
                facility_data = {
                    'id': 1,
                    'name': 'Default Facility',
                    'facility_type': 'clinic',
                    'district': 'Kampala'
                }
        
        return Response({
            'success': True,
            'facility': facility_data
        })
    else:
        return Response({'error': 'Invalid credentials'}, status=401)


@api_view(['POST'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def facility_logout(request):
    """Logout facility user"""
    logout(request)
    return Response({'success': True})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def facility_whoami(request):
    """Get current facility info"""
    try:
        # Try to get facility from user profile, fallback to first facility
        try:
            user_profile = request.user.profile
            if user_profile.facility:
                facility = user_profile.facility
            else:
                facility = Facility.objects.first()
        except AttributeError:
            facility = Facility.objects.first()
            
        if facility:
            return Response({
                'authenticated': True,
                'facility': {
                    'id': facility.id,
                    'name': facility.name,
                    'facility_type': facility.facility_type,
                    'district': facility.district
                }
            })
        else:
            return Response({'authenticated': False, 'error': 'No facilities found'}, status=403)
    except Exception as e:
        return Response({'authenticated': False, 'error': str(e)}, status=403)


# Case management views
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_cases(request):
    """Get all cases for the facility"""
    try:
        # Try to get facility from user profile, fallback to first facility
        try:
            user_profile = request.user.profile
            if user_profile.facility:
                facility = user_profile.facility
            else:
                facility = Facility.objects.first()
        except AttributeError:
            facility = Facility.objects.first()
            
        if not facility:
            return Response({'error': 'No facilities found'}, status=403)
            
        routings = FacilityRouting.objects.filter(
            assigned_facility=facility
        ).order_by('-created_at')
        
        data = []
        for r in routings:
            data.append({
                'id': f'FR-{r.id}',
                'patientToken': r.patient_token,
                'primarySymptom': r.primary_symptom,
                'secondarySymptoms': r.secondary_symptoms or [],
                'riskLevel': r.risk_level,
                'status': r.routing_status,
                'village': r.patient_village or 'N/A',
                'district': r.patient_district or 'N/A',
                'ageRange': r.age_group or 'N/A',
                'sex': r.sex or 'N/A',
                'facility': facility.name,
                'createdAt': r.created_at.isoformat() if r.created_at else None,
                'confirmedAt': r.facility_confirmed_at.isoformat() if r.facility_confirmed_at else None,
                'bookingType': r.booking_type,
                'hasRedFlags': r.has_red_flags,
                'redFlagSymptoms': r.red_flags if hasattr(r, 'red_flags') else [],
                'chronicConditions': r.chronic_conditions if hasattr(r, 'chronic_conditions') else [],
                'followUpPriority': getattr(r, 'follow_up_priority', 'normal'),
                'triageReceivedAt': r.triage_received_at.isoformat() if hasattr(r, 'triage_received_at') and r.triage_received_at else None,
            })
        
        return Response(data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_stats(request):
    """Get statistics for the facility dashboard"""
    try:
        # Try to get facility from user profile, fallback to first facility
        try:
            user_profile = request.user.profile
            if user_profile.facility:
                facility = user_profile.facility
            else:
                facility = Facility.objects.first()
        except AttributeError:
            facility = Facility.objects.first()
            
        if not facility:
            return Response({'error': 'No facilities found'}, status=403)
            
        routings = FacilityRouting.objects.filter(assigned_facility=facility)
        
        return Response({
            'total': routings.count(),
            'high': routings.filter(risk_level='high').count(),
            'medium': routings.filter(risk_level='medium').count(),
            'low': routings.filter(risk_level='low').count(),
            'pending': routings.filter(routing_status='pending').count(),
            'confirmed': routings.filter(routing_status='confirmed').count(),
        })
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def confirm_case(request, case_id):
    """Confirm a case"""
    try:
        routing_id = case_id.replace('FR-', '')
        routing = FacilityRouting.objects.select_related('assigned_facility').get(id=int(routing_id))
        
        # Get facility from user profile
        try:
            user_profile = request.user.profile
            if not user_profile.facility:
                return Response({'error': 'User is not linked to a facility'}, status=403)
            facility = user_profile.facility
        except AttributeError:
            return Response({'error': 'User is not linked to a facility'}, status=403)
        if routing.assigned_facility_id != facility.id:
            return Response({'error': 'Not allowed'}, status=403)
        
        routing.routing_status = 'confirmed'
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
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def reject_case(request, case_id):
    """Reject a case"""
    try:
        routing_id = case_id.replace('FR-', '')
        routing = FacilityRouting.objects.select_related('assigned_facility').get(id=int(routing_id))
        
        # Get facility from user profile
        try:
            user_profile = request.user.profile
            if not user_profile.facility:
                return Response({'error': 'User is not linked to a facility'}, status=403)
            facility = user_profile.facility
        except AttributeError:
            return Response({'error': 'User is not linked to a facility'}, status=403)
        if routing.assigned_facility_id != facility.id:
            return Response({'error': 'Not allowed'}, status=403)
        
        routing.routing_status = 'rejected'
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
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def acknowledge_case(request, case_id):
    """Acknowledge a case"""
    try:
        routing_id = case_id.replace('FR-', '')
        routing = FacilityRouting.objects.select_related('assigned_facility').get(id=int(routing_id))
        
        # Get facility from user profile
        try:
            user_profile = request.user.profile
            if not user_profile.facility:
                return Response({'error': 'User is not linked to a facility'}, status=403)
            facility = user_profile.facility
        except AttributeError:
            return Response({'error': 'User is not linked to a facility'}, status=403)
        if routing.assigned_facility_id != facility.id:
            return Response({'error': 'Not allowed'}, status=403)
        
        routing.routing_status = 'acknowledged'
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
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def delete_case(request, case_id):
    """Delete a case"""
    try:
        routing_id = case_id.replace('FR-', '')
        routing = FacilityRouting.objects.select_related('assigned_facility').get(id=int(routing_id))
        
        # Get facility from user profile
        try:
            user_profile = request.user.profile
            if not user_profile.facility:
                return Response({'error': 'User is not linked to a facility'}, status=403)
            facility = user_profile.facility
        except AttributeError:
            return Response({'error': 'User is not linked to a facility'}, status=403)
        if routing.assigned_facility_id != facility.id:
            return Response({'error': 'Not allowed'}, status=403)
        
        routing.delete()
        
        return Response({
            'id': case_id,
            'message': 'Case deleted successfully'
        })
    except FacilityRouting.DoesNotExist:
        return Response({'error': 'Case not found'}, status=404)
    except Facility.DoesNotExist:
        return Response({'error': 'User is not linked to a facility'}, status=403)
    except ValueError:
        return Response({'error': 'Invalid case id'}, status=400)
    except Exception as e:
        return Response({'error': str(e)}, status=500)
