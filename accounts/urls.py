from django.urls import path
from .views import CustomLoginView, CustomLogoutView, DashboardView, logout_view

app_name = 'accounts'

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path("logout/", logout_view, name="logout"),
    # path('logout/', CustomLogoutView.as_view(), name='logout'),
]
