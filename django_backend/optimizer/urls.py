# users/urls.py

from django.conf.urls import include
from django.urls import path
from .views import index, AddDataView, DashboardView, DataSettingsSerializerView
from django.contrib import admin
from django.urls import path, include
from rest_framework import routers

router = routers.DefaultRouter()
router.register(r'data-settings', DataSettingsSerializerView, 'data-settings')

urlpatterns = [
    path('', index, name='index'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('add-data/', AddDataView.as_view(), name='add-data'),
    # path('dashboard/add-data/', AddDataView.as_view(), name='add-data'),
    # path('dashboard/optimize/', OptimizeView.as_view(), name='optimize'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('api/', include(router.urls))
]