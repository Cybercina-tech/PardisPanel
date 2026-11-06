from django.urls import path

from . import api_views

urlpatterns = [
    path("summary/", api_views.DashboardSummaryAPIView.as_view(), name="api-dashboard-summary"),
]
