from django.shortcuts import render


def landing_page(request):
    """
    Public marketing/landing page that explains what Sarafi Pardis Panel can do.
    """
    return render(request, "landing/landing.html")


