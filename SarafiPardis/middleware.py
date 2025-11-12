"""
Custom middleware for SarafiPardis project.
"""
from django.shortcuts import render
from django.http import Http404
from django.conf import settings


class Custom404Middleware:
    """
    Middleware to show custom 404 page even when DEBUG=True.
    This ensures users see the custom 404 page during development.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip for static/media files and admin
        path = request.path_info
        if (path.startswith('/static/') or 
            path.startswith('/media/') or 
            path.startswith('/admin/')):
            return self.get_response(request)
        
        response = self.get_response(request)
        
        # If we get a 404 response, render our custom template
        if response.status_code == 404:
            try:
                # Check if it's Django's debug 404 page (contains specific text)
                # or just a regular 404
                response_content = ''
                if hasattr(response, 'content'):
                    response_content = response.content.decode('utf-8', errors='ignore')
                
                # Replace with our custom 404 page
                return render(request, '404.html', status=404)
            except Exception:
                # If template rendering fails, return original response
                return response
        
        return response

