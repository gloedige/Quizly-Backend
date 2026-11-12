# Standard library
from datetime import datetime, timezone

# Third-party
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

# Local imports
from auth_app.models import AccessTokenStorage

class CookieJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication class that retrieves the access token from HttpOnly cookies if not present in the header.
    """
    def authenticate(self, request):
        """
        Authenticate the request using the access token from the header or HttpOnly cookies.
        """
        header = self.get_header(request)
        if header is None:
            access_token = request.COOKIES.get('access_token')
        else:
            access_token = self.get_raw_token(header)

        if access_token is None:
            return None

        return self.authenticate_access_token(access_token)

    def authenticate_access_cookie(self, request):
        """Authenticate specifically with the access-token cookie."""
        access_token = request.COOKIES.get('access_token')
        if access_token is None:
            return None
        return self.authenticate_access_token(access_token)

    def authenticate_access_token(self, access_token):
        """Validate a raw JWT and return its user and validated token."""
        validated_access_token = self.get_validated_token(access_token)
        self.validate_access_token_not_in_custom_storage(validated_access_token)
        return self.get_user(validated_access_token), validated_access_token

    def store_access_token_in_custom_storage(self, validated_token):
        """Store a validated token's JTI and expiry as a revocation record."""
        jti = validated_token['jti']
        expires_at = datetime.fromtimestamp(validated_token['exp'], tz=timezone.utc)
        AccessTokenStorage.objects.get_or_create(access_token=jti, defaults={'expires_at': expires_at})

    def validate_access_token_not_in_custom_storage(self, validated_access_token):
        """Reject access tokens whose JTI is present in the revocation table."""
        if AccessTokenStorage.objects.filter(access_token=validated_access_token['jti']).exists():
            raise AuthenticationFailed('Access token has been revoked.')

    def clear_deprecated_access_token(self):
        """Remove expired access tokens from the custom storage."""
        AccessTokenStorage.objects.filter(expires_at__lt=datetime.now(timezone.utc)).delete()