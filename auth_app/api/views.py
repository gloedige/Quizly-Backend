from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
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

        data = {}
        if serializer.is_valid():
            save_account = serializer.save()
            data = {
                'username': save_account.username,
                'email': save_account.email,
                'user_id': save_account.id
            }
            return Response({"detail": "User created successfully!"}, status=status.HTTP_201_CREATED)


        # Implement registration logic here
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class CookieTokenObtainPairView(TokenObtainPairView):
    permission_classes = PUBLIC_PERMISSIONS

    pass

class CookieRefreshView(TokenRefreshView):
    permission_classes = REFRESH_PERMISSIONS
    pass

class CookieLogoutView(APIView):
    permission_classes = AUTHENTICATED_PERMISSIONS
    def post(self, request):
        # Implement logout logic here
        # return Response({"message": "User logged out successfully"}, status=status.HTTP_200_OK)
        pass