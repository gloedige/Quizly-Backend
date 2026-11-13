# Third-party
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.models import User


class RegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration, including password confirmation."""
    confirmed_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'confirmed_password']
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'write_only': True}
        }

    def validate_username(self, value):
        """Trim the username and reject exact duplicates."""
        value = value.strip()
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('This username is already in use.')
        return value
    
    def validate_email(self, value):
        """Trim and normalize the email, and reject duplicates."""
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Email is already in use")
        return value

    def validate(self, attrs):
        """Ensure the confirmed password matches the original password."""
        password = attrs.get('password')
        confirmed_password = attrs.get('confirmed_password')
        if password and confirmed_password and password != confirmed_password:
            raise serializers.ValidationError({"confirmed_password": "Passwords do not match"})
        return attrs

    def save(self):
        """Create and save a new user account with the validated data."""
        try:
            pw = self.validated_data['password']
            account = User(email=self.validated_data['email'], username=self.validated_data['username'])
            account.set_password(pw)
            account.save()
            return account
        except KeyError:
            raise serializers.ValidationError("Password is required")

class LoginSerializer(TokenObtainPairSerializer):
    """Serializer for user login."""
    class Meta:
        model = User
        fields = ['username', 'password']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def __init__(self, *args, **kwargs):
        """Make credentials optional at field level for custom missing-field validation."""
        super().__init__(*args, **kwargs)
        self.fields['username'].required = False
        self.fields['password'].required = False

    def validate(self, attrs):
        """
        Validate the login credentials.
        """
        username = attrs.get('username')
        password = attrs.get('password')

        if not username or not password:
            raise AuthenticationFailed("Username and password are required")

        return super().validate(attrs)