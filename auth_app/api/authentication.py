from datetime import datetime, timezone

from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

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
            raw_token = request.COOKIES.get('access_token')
        else:
            raw_token = self.get_raw_token(header)

        if raw_token is None:
            return None

        return self.authenticate_token(raw_token)

    def authenticate_access_cookie(self, request):
        """Authenticate specifically with the access-token cookie."""
        raw_token = request.COOKIES.get('access_token')
        if raw_token is None:
            return None
        return self.authenticate_token(raw_token)

    def authenticate_token(self, raw_token):
        """Validate a raw JWT and return its user and validated token."""
        validated_token = self.get_validated_token(raw_token)
        self.validate_access_token_not_in_custom_storage(validated_token)
        return self.get_user(validated_token), validated_token

    def store_access_token_in_custom_storage(self, validated_token):
        """Store a validated token's JTI and expiry as a revocation record."""
        jti = validated_token['jti']
        expires_at = datetime.fromtimestamp(validated_token['exp'], tz=timezone.utc)
        AccessTokenStorage.objects.get_or_create(access_token=jti, defaults={'expires_at': expires_at})

    def validate_access_token_not_in_custom_storage(self, validated_token):
        """Reject access tokens whose JTI is present in the revocation table."""
        if AccessTokenStorage.objects.filter(access_token=validated_token['jti']).exists():
            raise AuthenticationFailed('Access token has been revoked.')