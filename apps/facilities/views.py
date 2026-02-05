from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Facility
from .serializers import FacilitySerializer


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
