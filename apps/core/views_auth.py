"""
Authentication API views for HarakaCare.
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate

from apps.core.permissions import IsHealthcareWorker

User = get_user_model()


class LoginView(APIView):
    """
    POST /api/v1/auth/login/
    Authenticate healthcare worker and return JWT tokens.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {'error': 'Username and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(username=username, password=password)

        if not user:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.is_active:
            return Response(
                {'error': 'Account is disabled'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Check if user is healthcare worker
        if not (user.is_staff or user.is_superuser):
            return Response(
                {'error': 'Access denied. Healthcare worker account required.'},
                status=status.HTTP_403_FORBIDDEN
            )

        refresh = RefreshToken.for_user(user)

        # Get profile info
        role = 'staff'
        facility = None
        can_view_all = False
        if hasattr(user, 'profile'):
            role = user.profile.role
            facility = user.profile.facility.name if user.profile.facility else None
            can_view_all = user.profile.can_view_all_facilities

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': role,
                'facility': facility,
                'can_view_all_facilities': can_view_all,
                'is_superuser': user.is_superuser,
            },
        })


class LogoutView(APIView):
    """
    POST /api/v1/auth/logout/
    Blacklist the refresh token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception:
            pass  # Token may already be blacklisted
        return Response({'message': 'Logged out successfully'})


class UserProfileView(APIView):
    """
    GET /api/v1/auth/profile/
    Get current user profile.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        role = 'staff'
        facility = None
        can_view_all = False
        if hasattr(user, 'profile'):
            role = user.profile.role
            facility = user.profile.facility.name if user.profile.facility else None
            can_view_all = user.profile.can_view_all_facilities

        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': role,
            'facility': facility,
            'can_view_all_facilities': can_view_all,
            'is_superuser': user.is_superuser,
            'is_staff': user.is_staff,
        })


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    POST /api/v1/auth/token/
    Obtain JWT token pair.
    """
    permission_classes = [AllowAny]


class CustomTokenRefreshView(TokenRefreshView):
    """
    POST /api/v1/auth/token/refresh/
    Refresh JWT access token.
    """
    permission_classes = [AllowAny]
