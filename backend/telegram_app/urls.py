"""
URL configuration for telegram_app.
"""
from django.urls import path
from . import views

app_name = 'telegram_app'

urlpatterns = [
    path('send-message/', views.send_message_view, name='send_message'),
    path('default-settings/', views.default_settings_view, name='default_settings'),
]
