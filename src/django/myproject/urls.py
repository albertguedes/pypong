from django.urls import path
from myapp import views

urlpatterns = [
    path('', views.index, name='index'),
    path('health', views.health, name='health'),
    path('database', views.database, name='database'),
    path('metrics', views.metrics, name='metrics'),
    path('v1', views.v1_info, name='v1_info'),
    path('django', views.django_info, name='django_info'),
    path('v1/auth/register', views.auth_register, name='auth_register'),
    path('v1/auth/token', views.auth_token, name='auth_token'),
    path('v1/protected', views.protected, name='protected'),
]