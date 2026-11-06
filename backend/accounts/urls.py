from django.shortcuts import redirect
from django.urls import path
from django.views.generic import RedirectView

from .views import logout_view

app_name = 'accounts'

urlpatterns = [
    path('login/', RedirectView.as_view(url='/login', permanent=False), name='login'),
    path('logout/', logout_view, name='logout'),
]
