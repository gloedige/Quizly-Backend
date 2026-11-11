from rest_framework import serializers
from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from django.contrib.auth import authenticate


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

    def validate_confirmed_password(self, value):
        """Ensure the confirmed password matches the original password."""
        password = self.initial_data.get('password')
        if password and value and value != password:
            raise serializers.ValidationError("Passwords do not match")
        return value

    def validate_email(self, value):
        """Trim and normalize the email, and reject duplicates."""
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Email is already in use")
        return value

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

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            raise AuthenticationFailed("Username and password are required")

        return super().validate(data)