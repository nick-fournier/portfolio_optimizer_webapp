# users/urls.py

from django.conf.urls import url, include
from django.urls import path
from .views import index, DashboardView#, DataSettingsView#, AddDataView, OptimizeView

urlpatterns = [
    path('', index, name='index'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    # path('dashboard/add-data/', AddDataView.as_view(), name='add-data'),
    # path('dashboard/optimize/', OptimizeView.as_view(), name='optimize'),
    # path('dashboard/data-settings/<int:pk>', DataSettingsView.as_view(), name='data-settings'),
    path('accounts/', include('django.contrib.auth.urls')),
]