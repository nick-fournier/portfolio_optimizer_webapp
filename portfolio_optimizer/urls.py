# users/urls.py

from .views import IndexView, AddDataView, DashboardView, DataSettingsSerializerView
from django.urls import path, include
from rest_framework import routers

router = routers.DefaultRouter()
router.register(r'data-settings/1', DataSettingsSerializerView, 'data-settings')

urlpatterns = [
    # path('', index, name='index'),
    path('', IndexView.as_view(), name='portfolio-optimizer-index'),
    path('dashboard/', DashboardView.as_view(), name='portfolio-optimizer-dashboard'),
    path('add-data/', AddDataView.as_view(), name='portfolio-optimizer-add-data'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('api/', include(router.urls))
]