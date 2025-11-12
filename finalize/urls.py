from django.urls import path
from . import views

app_name = 'finalize'

urlpatterns = [
    path('', views.finalize_dashboard, name='dashboard'),
    path('category/<int:category_id>/', views.finalize_category, name='finalize_category'),
    path('special-price/<int:special_price_history_id>/', views.finalize_special_price, name='finalize_special_price'),
]
