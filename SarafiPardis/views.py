"""
Custom views for the SarafiPardis project.
"""
from django.shortcuts import render
from django.http import Http404, HttpResponse


def handler404(request, exception):
    """
    Custom 404 error handler.
    This view is automatically called by Django when a 404 error occurs.
    """
    return render(request, '404.html', status=404)


def favicon_view(request):
    """
    Handle favicon.ico requests to prevent 404 errors.
    Returns a 204 No Content response.
    """
    return HttpResponse(status=204)

