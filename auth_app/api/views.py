from rest_framework.views import APIView
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework import status
from django.db import IntegrityError, transaction
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.exceptions import TokenError
from .serializers import RegistrationSerializer
from rest_framework.permissions import AllowAny, IsAuthenticated
from .permissions import RefreshTokenPermission
from django.contrib.auth import get_user_model
from .serializers import LoginSerializer

from auth_app.api.authentication import CookieJWTAuthentication


PUBLIC_PERMISSIONS = (AllowAny,)
AUTHENTICATED_PERMISSIONS = (IsAuthenticated,)
REFRESH_PERMISSIONS = (RefreshTokenPermission,)

def set_auth_cookies(response, access_token, new_refresh_token):
    if access_token:
        response.set_cookie(
            key='access_token',
            value=access_token,
            httponly=True,
            secure=True,
            samesite='Lax'
        )

    if new_refresh_token:
        response.set_cookie(
            key='refresh_token',
            value=new_refresh_token,
            httponly=True,
            secure=True,
            samesite='Lax'
        )
    return response

class RegistrationView(APIView):
    """ API view for user registration. """
    permission_classes = PUBLIC_PERMISSIONS
    def post(self, request):
        """Handle user registration."""
        serializer = RegistrationSerializer(data=request.data)

        if serializer.is_valid():
            try:
                with transaction.atomic():
                    serializer.save()
            except IntegrityError:
                return Response(
                    {"detail": "A user with this username or email already exists."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response({"detail": "User created successfully!"}, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CookieTokenObtainPairView(TokenObtainPairView):
    """API view for obtaining JWT tokens and setting them as HttpOnly cookies."""
    permission_classes = PUBLIC_PERMISSIONS
    serializer_class = LoginSerializer

    def get_valid_login_serializer(self, data):
        serializer = self.get_serializer(data=data)
        try:
            serializer.is_valid(raise_exception=True)
        except AuthenticationFailed:
            raise AuthenticationFailed("Invalid login data.")
        return serializer

    def post(self, request, *args, **kwargs):
        """Handle user login and set JWT tokens as HttpOnly cookies."""
        serializer = self.get_valid_login_serializer(request.data)

        user = serializer.user
        response = Response(
            {
                'detail': 'Login successfully!',
                'user': {
                    'id': user.pk,
                    'username': user.username,
                    'email': user.email,
                },
            },
            status=status.HTTP_200_OK,
        )
        data = serializer.validated_data
        return set_auth_cookies(response, data['access'], data['refresh'])

class CookieRefreshView(TokenRefreshView):
    """API view for refreshing JWT tokens using HttpOnly cookies."""
    permission_classes = PUBLIC_PERMISSIONS
    
    def post(self, request, *args, **kwargs):
        """Handle refreshing of JWT tokens using the refresh token from HttpOnly cookies."""
        refresh_token = request.COOKIES.get('refresh_token')

        if refresh_token is None:
            return self.respond_with_token_error()
        
        serializer = self.get_valid_refresh_serializer(refresh_token)
        if serializer is None:
            return self.respond_with_token_error()

        response = Response({"detail": "Token refreshed"}, status=status.HTTP_200_OK)
        data = serializer.validated_data
        return set_auth_cookies(response, data.get('access'), data.get('refresh'))

    def get_valid_refresh_serializer(self, token):
        """Validate refresh token and return its serializer, or None."""
        serializer = self.get_serializer(data={'refresh': token})
        try:
            self.check_user_active(token)
            serializer.is_valid(raise_exception=True)
        except (TokenError, AuthenticationFailed):
            return None
        return serializer

    def respond_with_token_error(self):
        """Respond with a token error indicating the refresh token is invalid or not provided."""
        return Response(
                {"detail": "Refresh token invalid or not provided"}, 
                status=status.HTTP_401_UNAUTHORIZED
                )

    def check_user_active(self, refresh_token):
        """Check if the user associated with the refresh token is active."""
        token = RefreshToken(refresh_token)
        user_id = token.payload.get('user_id')
        if not get_user_model().objects.filter(pk=user_id, is_active=True).exists():
            raise TokenError('User is inactive')

class CookieLogoutView(APIView):
    """API view for logging out users by blacklisting the refresh token and deleting cookies."""
    permission_classes = AUTHENTICATED_PERMISSIONS

    def authenticate_access_cookie(self, request):
        """Validate the access cookie and return its verified JWT payload."""
        result = CookieJWTAuthentication().authenticate_access_cookie(request)
        if result is None:
            raise AuthenticationFailed('Access token is required.')
        return result[1]

    def post(self, request):
        """Handle user logout by blacklisting the refresh token and deleting HttpOnly cookies."""
        access_token = self.authenticate_access_cookie(request)
        self.blacklist_refresh_cookie(request.COOKIES.get('refresh_token'))
        CookieJWTAuthentication().store_access_token_in_custom_storage(access_token)
        response = Response(
            {"detail": "Log-Out successfully! All Tokens will be deleted. Refresh token is now invalid."}, 
            status=status.HTTP_200_OK)
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')
        return response

    def blacklist_refresh_cookie(self, refresh_token):
        """Blacklist a valid refresh cookie; tolerate its absence or invalidity."""
        try:
            RefreshToken(refresh_token).blacklist()
        except TokenError:
            return None