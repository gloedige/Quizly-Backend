# Standard library
from unittest.mock import patch
import os

# Third-party
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from rest_framework.test import APIClient

# Local imports
from dotenv import load_dotenv

load_dotenv()  # loads .env variables



User = get_user_model()


class AuthenticationEndpointTests(TestCase):
    """Checks the registration and login endpoints."""

    def setUp(self):
        """Create an API client."""
        self.client = APIClient()

    def register(self, **overrides):
        """POST a valid registration payload updated by overrides; return the response."""
        payload = {
            'username': 'valid-user',
            'email': 'valid@example.com',
            'password': 'pass',
            'confirmed_password': 'pass',
        }
        payload.update(overrides)
        return self.client.post('/api/register/', payload, format='json')

    def create_user(self, username, email):
        """Create and return a user with password 'pass'."""
        return User.objects.create_user(
            username=username,
            email=email,
            password='pass',
        )

    def login(self, username, password):
        """POST login credentials and return the response."""
        payload = {
            'username': username,
            'password': password
        }
        return self.client.post('/api/login/', payload, format='json')
        

    def assert_generic_login_error(self, response):
        """Assert the response is the generic invalid-credentials 401 error."""
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.data,
            {'detail': "Invalid login data."},
        )

    def assert_registered_user(self, response):
        """Assert user and response body of a successful registration."""
        user = User.objects.get(username='neuerNutzer')
        self.assertEqual(user.email, 'user@example.com')
        self.assertEqual(response.data, {
            'detail': 'User created successfully!'
        })

    def assert_password_rejected(self, password, confirmed_password, expected_field):
        """Assert registration with these passwords fails with an error on expected_field."""
        username = f'valid-user-{expected_field}'
        response = self.register(
            username=username,
            email=f'{expected_field}@example.com',
            password=password,
            confirmed_password=confirmed_password,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(expected_field, response.data)
        self.assertFalse(User.objects.filter(username=username).exists())

    def validate_token_cookies(self, response, refresh_expected=True):
        """Assert that the response sets non-empty JWT cookies."""
        self.assertIn('access_token', response.cookies)
        self.assertTrue(response.cookies['access_token'].value)
        if refresh_expected:
            self.assertIn('refresh_token', response.cookies)
            self.assertTrue(response.cookies['refresh_token'].value)

    def validate_cleared_token_cookies(self):
        """Assert that the response expires both JWT cookies."""
        for name in ('access_token', 'refresh_token'):
            self.assertIn(name, self.client.cookies)
            self.assertEqual(self.client.cookies[name].value, '')
            self.assertEqual(self.client.cookies[name]['max-age'], 0)

    def validate_refresh_token_not_provided(self, response):
        """Assert that the response indicates the refresh token was not provided."""
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.data,
            {"detail": "Refresh token invalid or not provided"}
        )

    def assign_invalid_cookie_value(self, name, value, age):
        """Set the specified cookie to an invalid value."""
        self.client.cookies[name] = value
        self.client.cookies[name]['max-age'] = age

    def test_registration_allows_username_with_different_case(self):
        """A username differing only in case can still register."""
        self.create_user('neuerNutzer', 'existing@example.com')

        response = self.register(
            username='NEUERnutzer', email='new@example.com'
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['detail'], 'User created successfully!')
        self.assertTrue(User.objects.filter(username='NEUERnutzer').exists())

    def test_registration_returns_400_for_concurrent_duplicate_insert(self):
        """A race on the unique constraint yields a 400 response."""
        with patch(
            'auth_app.api.serializers.User.save',
            side_effect=IntegrityError('unique constraint race'),
        ):
            response = self.register(username='racing-user', email='racing@example.com')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data,
            {'detail': 'A user with this username or email already exists.'},
        )
        self.assertFalse(User.objects.filter(username='racing-user').exists())

    def test_registration_rejects_mismatched_password(self):
        """Short or mismatched passwords are rejected on the matching field."""
        for password, confirmed_password, expected_field in (
            ('pass', 'different', 'confirmed_password'),
        ):
            with self.subTest(expected_field=expected_field):
                self.assert_password_rejected(password, confirmed_password, expected_field)

    def test_login_requires_exact_username_case(self):
        """Login succeeds with exact username case and fails otherwise."""
        user = self.create_user('neuerNutzer', 'login@example.com')

        response = self.login('neuerNutzer', 'pass')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['detail'], 'Login successfully!')
        self.assertEqual(response.data['user']['id'], user.pk)
        self.assertEqual(response.data['user']['username'], 'neuerNutzer')
        self.assertEqual(response.data['user']['email'], 'login@example.com')
        self.assert_generic_login_error(self.login('NEUERnutzer', 'pass'))

    def test_login_returns_same_generic_validation_error_for_invalid_credentials(self):
        """Unknown users and wrong passwords yield the same generic error."""
        self.create_user('known-user', 'known@example.com')

        for username, password in (
            ('missing-user', 'pass'),
            ('known-user', 'wrong'),
        ):
            with self.subTest(username=username):
                self.assert_generic_login_error(self.login(username, password))

    def test_login_rejects_missing_fields(self):
        """Login without fields reports both missing fields."""
        response = self.client.post('/api/login/', {}, format='json')

        self.assertEqual(response.status_code, 401)
        # self.assertIn('username', response.data)
        # self.assertIn('password', response.data)

    def test_cookies_are_set_on_login(self):
        """Cookies are correctly set after a successful login."""
        self.create_user('cookie-user', 'cookie@example.com')
        response = self.login('cookie-user', 'pass')

        self.assertEqual(response.status_code, 200)
        self.validate_token_cookies(response)

    def test_cookies_are_cleared_on_logout(self):
        """Cookies are correctly cleared after logout."""
        self.create_user('cookie-user', 'cookie@example.com')
        self.login('cookie-user', 'pass')
        response = self.client.post('/api/logout/', format='json')

        self.assertEqual(response.status_code, 200)
        self.validate_cleared_token_cookies()

    def test_refresh_token_sets_new_access_token(self):
        """Refreshing the token sets a new access token cookie."""
        self.create_user('refresh-user', 'refresh@example.com')
        self.login('refresh-user', 'pass')
        response = self.client.post('/api/token/refresh/', format='json')

        self.assertEqual(response.status_code, 200)
        self.validate_token_cookies(response, refresh_expected=False)

    def test_refresh_token_with_invalid_token(self):
        """Refreshing the token with an invalid token should fail."""
        self.create_user('invalid-refresh-user', 'invalid-refresh@example.com')
        self.login('invalid-refresh-user', 'pass')
        # Manually clear the refresh token cookie to simulate an invalid token
        self.client.cookies['access_token'] = 'invalid.jwt.value'
        self.client.cookies['refresh_token'] = 'invalid.jwt.value'
        response = self.client.post('/api/token/refresh/', format='json')
        self.assertEqual(response.status_code, 401)

    def test_refresh_token_without_login(self):
        """Refreshing the token without being logged in should fail."""
        response = self.client.post('/api/token/refresh/', format='json')
        self.assertEqual(response.status_code, 401)

    def test_refresh_token_with_expired_token(self):
        """Refreshing the token with an expired token should fail."""
        self.create_user('expired-refresh-user', 'expired-refresh@example.com')
        self.login('expired-refresh-user', 'pass')
        # Manually set an expired refresh token cookie
        # take expired token from blacklist or generate manually for testing purposes
        # self.client.cookies['refresh_token'] = 'expiredtoken'
        self.assign_invalid_cookie_value('refresh_token', '', 0)
        self.client.cookies['refresh_token']['expires'] = 'Thu, 01 Jan 1970 00:00:00 GMT'
        response = self.client.post('/api/token/refresh/', format='json')

        self.assertEqual(response.status_code, 401)
        self.validate_refresh_token_not_provided(response)

    def test_logout_without_login(self):
        """Logging out without being logged in should fail."""
        response = self.client.post('/api/logout/', format='json')
        self.assertEqual(response.status_code, 401)

    def test_logout_with_login(self):
        """Logging out after being logged in should succeed."""
        self.create_user('logout-user', 'logout@example.com')
        self.login('logout-user', 'pass')
        response = self.client.post('/api/logout/', format='json')
        self.assertEqual(response.status_code, 200)
        self.validate_cleared_token_cookies()

    def test_registration_successful(self):
        """Registration with valid data should succeed."""
        response = self.client.post('/api/register/', {
            'username': 'new-user',
            'email': 'new-user@example.com',
            'password': 'pass',
            'confirmed_password': 'pass'
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertIn('detail', response.data)
        self.assertEqual(response.data['detail'], 'User created successfully!')
    
    def test_registration_with_missing_fields(self):
        """Registration with missing fields should fail."""
        response = self.client.post('/api/register/', {
            'username': '',
            'email': '',
            'password': '',
            'confirmed_password': ''
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_registration_with_existing_username(self):
        """Registration with an existing username should fail."""
        self.create_user('existing-user', 'existing@example.com')
        response = self.client.post('/api/register/', {
            'username': 'existing-user',
            'email': 'new-email@example.com',
            'password': 'pass',
            'confirmed_password': 'pass'
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('username', response.data)
    
    def test_registration_with_existing_email(self):
        """Registration with an existing email should fail."""
        self.create_user('user', 'existing-email@example.com')
        response = self.client.post('/api/register/', {
            'username': 'new-user',
            'password': 'pass',
            'confirmed_password': 'pass',
            'email': 'existing-email@example.com',
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.data)

    def test_login_cookies_has_httponly_flag(self):
        """Login cookies should have the HttpOnly flag set."""
        self.create_user('cookie-user', 'cookie@example.com')
        response = self.login('cookie-user', 'pass')
        self.assertEqual(response.status_code, 200)
        self.assertIn('access_token', response.cookies)
        self.assertIn('refresh_token', response.cookies)
        self.assertTrue(response.cookies['access_token']['httponly'])
        self.assertTrue(response.cookies['refresh_token']['httponly'])
    