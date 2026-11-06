from django.urls import path

from . import api_views
from .views import PricingDataAPIView

urlpatterns = [
    path("dashboard/", api_views.AnalysisDashboardAPIView.as_view(), name="api-analysis-dashboard"),
    path("import-commit/", api_views.AnalysisImportCommitAPIView.as_view(), name="api-analysis-import-commit"),
    path("pricing/", PricingDataAPIView.as_view(), name="api-analysis-pricing"),
]
