# Third-party
from django.urls import path

# Local imports
from . import views
from .views import RegistrationView, CookieRefreshView, CookieTokenObtainPairView, CookieLogoutView

urlpatterns = [
    path('register/', RegistrationView.as_view(), name='registration'),
    path('login/', CookieTokenObtainPairView.as_view(), name='login'),
    path('logout/', CookieLogoutView.as_view(), name='logout'),
    path('token/refresh/', CookieRefreshView.as_view(), name='refresh'),
]