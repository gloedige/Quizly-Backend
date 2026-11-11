from rest_framework.views import APIView
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework import status
from django.db import IntegrityError, transaction
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from .serializers import RegistrationSerializer
from rest_framework.permissions import AllowAny, IsAuthenticated
from .permissions import RefreshTokenPermission


PUBLIC_PERMISSIONS = (AllowAny,)
AUTHENTICATED_PERMISSIONS = (IsAuthenticated,)
REFRESH_PERMISSIONS = (RefreshTokenPermission,)

class RegistrationView(APIView):
    permission_classes = PUBLIC_PERMISSIONS
    def post(self, request):
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
        
        # Implement registration logic here
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class CookieTokenObtainPairView(TokenObtainPairView):
    from .serializers import LoginSerializer
    permission_classes = PUBLIC_PERMISSIONS
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except AuthenticationFailed:
            return Response(
                {"detail": "Invalid login data."},
                status=status.HTTP_401_UNAUTHORIZED
            )

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
        response.set_cookie(
            key='refresh_token',
            value=serializer.validated_data['refresh'],
            httponly=True,
            secure=False,
            samesite='Lax',
        )
        response.set_cookie(
            key='access_token',
            value=serializer.validated_data['access'],
            httponly=True,
            secure=False,
            samesite='Lax',
        )
        return response


class CookieRefreshView(TokenRefreshView):
    permission_classes = PUBLIC_PERMISSIONS
    
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get('refresh_token')

        if refresh_token is None:
            return Response(
                {"detail": "Refresh token invalid or not provided"}, 
                status=status.HTTP_401_UNAUTHORIZED
                )
        
        serializer = self.get_serializer(data={'refresh': refresh_token})
        try:
            serializer.is_valid(raise_exception=True)
        except (TokenError, AuthenticationFailed):
            return Response(
                {"detail": "Refresh token invalid or not provided"}, 
                status=status.HTTP_401_UNAUTHORIZED
                )

        access_token = serializer.validated_data.get('access')

        response = Response({"detail": "Token refreshed"})

        if access_token:
            response.set_cookie(
                key='access_token',
                value=access_token,
                httponly=True,
                secure=False, # TODO: Set to True in production with HTTPS
                samesite='Lax')

        new_refresh_token = serializer.validated_data.get('refresh')
        if new_refresh_token:
            response.set_cookie(
                key='refresh_token',
                value=new_refresh_token,
                httponly=True,
                secure=False, # TODO: Set to True in production with HTTPS
                samesite='Lax'
            )

        return response

class CookieLogoutView(APIView):
    permission_classes = AUTHENTICATED_PERMISSIONS
    def post(self, request):
        RefreshToken(request.COOKIES['refresh_token']).blacklist()
        response = Response(
            {"detail": "Log-Out successfully! All Tokens will be deleted. Refresh token is now invalid."}, 
            status=status.HTTP_200_OK)
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')
        return response