from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Facility
from .serializers import FacilitySerializer

# Simple in-memory storage for demonstration (empty now - will use real database)
test_cases_storage = []


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def get_cases(request):
    """Get cases for facility dashboard"""
    if request.method == 'POST':
        # Create a test case for demonstration
        from datetime import datetime
        import uuid
        
        test_case = {
            'id': f'HC-{uuid.uuid4().hex[:6].upper()}',
            'patientToken': f'PT-{uuid.uuid4().hex[:3].upper()}',
            'primarySymptom': 'Test Fever',
            'riskLevel': 'medium',
            'status': 'pending',
            'district': 'Test District',
            'facility': 'Test Hospital',
            'createdAt': datetime.now().isoformat(),
            'sex': 'male',
            'age': 25
        }
        # Store in memory
        test_cases_storage.append(test_case)
        return Response(test_case, status=201)
    
    # Return cases from triage sessions only
    all_cases = []
    
    # Try to get triage sessions and convert them to case format
    try:
        from apps.triage.models import TriageSession
        triage_sessions = TriageSession.objects.filter(status='completed').order_by('-created_at')[:10]  # Get latest 10
        
        for session in triage_sessions:
            # Convert triage session to case format
            case_data = {
                'id': f'TS-{session.id}',
                'patientToken': session.patient_token or f'TOKEN-{session.id}',
                'primarySymptom': session.complaint_group or 'Unknown',
                'riskLevel': session.risk_level or 'medium',
                'status': 'pending',
                'district': session.district or 'Unknown',
                'facility': session.preferred_facility or 'Unknown',
                'createdAt': session.created_at.isoformat() if session.created_at else datetime.now().isoformat(),
                'sex': session.sex or 'unknown',
                'age': session.age or 0
            }
            all_cases.append(case_data)
            
    except Exception as e:
        print(f"Error reading triage sessions: {e}")
    
    return Response(all_cases)


@api_view(['POST'])
@permission_classes([AllowAny])
def confirm_case(request, case_id):
    """Confirm a case"""
    # Find and update the case in storage
    for i, case_item in enumerate(test_cases_storage):
        if case_item['id'] == case_id:
            test_cases_storage[i]['status'] = 'confirmed'
            test_cases_storage[i]['confirmedAt'] = datetime.now().isoformat()
            return Response({
                'id': case_item['id'],
                'status': 'confirmed',
                'confirmedAt': test_cases_storage[i]['confirmedAt'],
                'message': 'Case confirmed successfully'
            })
    
    return Response({'error': 'Case not found'}, status=404)


@api_view(['POST'])
@permission_classes([AllowAny])
def reject_case(request, case_id):
    """Reject a case"""
    # Find and update the case in storage
    for i, case_item in enumerate(test_cases_storage):
        if case_item['id'] == case_id:
            test_cases_storage[i]['status'] = 'rejected'
            test_cases_storage[i]['rejectedReason'] = request.data.get('reason', 'Rejected by facility')
            return Response({
                'id': case_item['id'],
                'status': 'rejected',
                'reason': test_cases_storage[i]['rejectedReason'],
                'message': 'Case rejected successfully'
            })
    
    return Response({'error': 'Case not found'}, status=404)


@api_view(['POST'])
@permission_classes([AllowAny])
def acknowledge_case(request, case_id):
    """Acknowledge a case"""
    # Find and update the case in storage
    for i, case_item in enumerate(test_cases_storage):
        if case_item['id'] == case_id:
            test_cases_storage[i]['acknowledged'] = True
            return Response({
                'id': case_item['id'],
                'acknowledged': True,
                'message': 'Case acknowledged successfully'
            })
    
    return Response({'error': 'Case not found'}, status=404)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_stats(request):
    """Get stats for facility dashboard"""
    # Calculate stats from stored cases
    total = len(test_cases_storage)
    high = len([c for c in test_cases_storage if c.get('riskLevel') == 'high'])
    medium = len([c for c in test_cases_storage if c.get('riskLevel') == 'medium'])
    low = len([c for c in test_cases_storage if c.get('riskLevel') == 'low'])
    pending = len([c for c in test_cases_storage if c.get('status') == 'pending'])
    confirmed = len([c for c in test_cases_storage if c.get('status') == 'confirmed'])
    
    return Response({
        'total': total,
        'high': high,
        'medium': medium,
        'low': low,
        'pending': pending,
        'confirmed': confirmed
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
