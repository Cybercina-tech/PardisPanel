"""
URL configuration for setting app.
"""
from django.urls import path
from . import views

app_name = 'setting'

urlpatterns = [
    path('', views.settings_view, name='settings'),
    path('bot/edit/<int:bot_id>/', views.edit_bot, name='edit_bot'),
    path('bot/delete/<int:bot_id>/', views.delete_bot, name='delete_bot'),
    path('channel/edit/<int:channel_id>/', views.edit_channel, name='edit_channel'),
    path('channel/delete/<int:channel_id>/', views.delete_channel, name='delete_channel'),
]
