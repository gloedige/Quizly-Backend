from rest_framework.permissions import BasePermission

class RefreshTokenPermission(BasePermission):
    def has_permission(self, request, view):
        """Check if the request has a valid refresh token."""
        has_refresh_token = bool(request.COOKIES.get('refresh_token'))
        return has_refresh_token