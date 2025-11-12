from django.urls import path
from . import views

app_name = 'special_price'

urlpatterns = [
    path('', views.special_price_dashboard, name='dashboard'),
    path('update/<int:special_price_type_id>/', views.update_special_price, name='update_price'),
    path('history/<int:special_price_type_id>/', views.special_price_history, name='price_history'),
    path('add/', views.add_special_price_type, name='add_type'),
    path('edit/<int:special_price_type_id>/', views.edit_special_price_type, name='edit_type'),
    path('delete/<int:special_price_type_id>/', views.delete_special_price_type, name='delete_type'),
]

