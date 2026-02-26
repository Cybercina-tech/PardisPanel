from django.shortcuts import render

from . import services as dashboard_services


def home(request):
    """Renders the home dashboard with categories, price types, and latest prices."""
    context = dashboard_services.get_home_context()
    return render(request, "dashboard/dashboard.html", context)


def dashboard2(request):
    """Renders the improved dashboard2 with Tailwind, charts, and enhanced features."""
    context = dashboard_services.get_dashboard2_context()
    return render(request, "dashboard/dashboard2.html", context)
