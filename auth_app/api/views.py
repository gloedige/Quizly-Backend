from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


class RegistrationView(APIView):
    def post(self, request):
        # Implement registration logic here
        # return Response({"message": "User registered successfully"}, status=status.HTTP_201_CREATED)
        pass


class CookieTokenObtainPairView(TokenObtainPairView):
    pass

class CookieRefreshView(TokenRefreshView):
    pass

class CookieLogoutView(APIView):
    def post(self, request):
        # Implement logout logic here
        # return Response({"message": "User logged out successfully"}, status=status.HTTP_200_OK)
        pass