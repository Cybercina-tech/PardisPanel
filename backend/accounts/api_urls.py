from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import api_views
from .serializers import TokenRefreshWithVersionSerializer

urlpatterns = [
    path("login/", api_views.LoginAPIView.as_view(), name="api-login"),
    path("signup/", api_views.SignupAPIView.as_view(), name="api-signup"),
    path("verify-email/", api_views.VerifyEmailAPIView.as_view(), name="api-verify-email"),
    path(
        "verify-email/resend/",
        api_views.ResendVerificationAPIView.as_view(),
        name="api-verify-email-resend",
    ),
    path(
        "onboarding/complete/",
        api_views.CompleteOnboardingAPIView.as_view(),
        name="api-onboarding-complete",
    ),
    path("google/", api_views.GoogleAuthAPIView.as_view(), name="api-google-auth"),
    path("logout/", api_views.LogoutAPIView.as_view(), name="api-logout"),
    path("me/", api_views.MeAPIView.as_view(), name="api-me"),
    path(
        "me/password/",
        api_views.ChangePasswordAPIView.as_view(),
        name="api-me-password",
    ),
    path("token/refresh/", TokenRefreshView.as_view(serializer_class=TokenRefreshWithVersionSerializer), name="api-token-refresh"),
    path("users/", api_views.UserListCreateAPIView.as_view(), name="api-user-list"),
    path("users/<int:pk>/", api_views.UserDetailAPIView.as_view(), name="api-user-detail"),
    path("users/<int:pk>/force-logout/", api_views.ForceLogoutAPIView.as_view(), name="api-user-force-logout"),
    path("programmer/users/", api_views.ProgrammerRegisterAPIView.as_view(), name="api-programmer-register"),
    path("programmer/users/<int:pk>/", api_views.ProgrammerUserDetailAPIView.as_view(), name="api-programmer-user"),
    path("programmer/templates/", api_views.ProgrammerTemplateLibraryAPIView.as_view(), name="api-programmer-templates"),
    path("impersonate/<int:pk>/", api_views.ImpersonateAPIView.as_view(), name="api-impersonate"),
    path("activity/", api_views.ActivityLogListAPIView.as_view(), name="api-activity-list"),
]
