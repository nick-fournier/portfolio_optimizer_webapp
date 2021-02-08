# users/urls.py

from django.conf.urls import url, include
from django.urls import path
from .views import index, AddSecurityView, DashboardView, DataSettingsView

urlpatterns = [
    path('', index, name='index'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('dashboard/add-security/', AddSecurityView.as_view(), name='add-security'),
    path('dashboard/data-settings/<int:pk>', DataSettingsView.as_view(), name='data-settings'),
    path('accounts/', include('django.contrib.auth.urls')),
]