from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

urlpatterns = [
    path("register/",       views.RegisterView.as_view(),      name="register"),
    path("token/",          TokenObtainPairView.as_view(),     name="token_obtain"),
    path("token/refresh/",  TokenRefreshView.as_view(),        name="token_refresh"),
    path("logout/",         views.LogoutView.as_view(),        name="logout"),
    path("profile/",        views.ProfileView.as_view(),       name="profile"),
    path("api-key/rotate/", views.RotateAPIKeyView.as_view(),  name="rotate_api_key"),
]
