from django.urls import path
from . import views

app_name = 'change_price'

urlpatterns = [
    path('', views.price_dashboard, name='dashboard'),
    path('update/<int:price_type_id>/', views.update_price, name='update_price'),
    path('history/<int:price_type_id>/', views.price_history, name='price_history'),
    path('category/<int:category_id>/update/', views.update_category_prices, name='update_category_prices'),
]