# users/urls.py

from .views import IndexView, MetaDataView, DashboardView
from django.urls import path, include

urlpatterns = [
    # path('', index, name='index'),
    path('', IndexView.as_view(), name='portfolio-optimizer-index'),
    path('dashboard/', DashboardView.as_view(), name='portfolio-optimizer-dashboard'),
    path('meta-data/', MetaDataView.as_view(), name='portfolio-optimizer-meta-data'),
    path('accounts/', include('django.contrib.auth.urls')),
]