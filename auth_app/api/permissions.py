from rest_framework.permissions import BasePermission

class RefreshTokenPermission(BasePermission):
    def has_permission(self, request, view):
        # Implement your refresh token validation logic here
        return True