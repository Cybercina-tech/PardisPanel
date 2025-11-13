from django.urls import path

from .views import AnalyticsDashboardView

app_name = "analysis"

urlpatterns = [
    path("", AnalyticsDashboardView.as_view(), name="dashboard"),
]

