from django.urls import path
from . import views

app_name = 'category'

urlpatterns = [
    # Dashboard
    path('', views.category_dashboard, name='category_dashboard'),

    # Category CRUD (use pk for URL params)
    path('add/', views.add_category, name='add_category'),
    path('edit/<int:pk>/', views.edit_category, name='edit_category'),
    path('delete/<int:pk>/', views.delete_category, name='delete_category'),

    # PriceType CRUD
    path('<int:category_pk>/pricetype/add/', views.add_pricetype, name='add_pricetype'),
    path('pricetype/edit/<int:pk>/', views.edit_pricetype, name='edit_pricetype'),
    path('pricetype/delete/<int:pk>/', views.delete_pricetype, name='delete_pricetype'),
]
