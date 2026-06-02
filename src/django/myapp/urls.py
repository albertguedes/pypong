from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('health', views.health, name='health'),
    path('database', views.database, name='database'),
    path('metrics', views.metrics, name='metrics'),
    path('django', views.django_info, name='django_info'),
]