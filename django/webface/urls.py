# users/urls.py

from django.conf.urls import url, include
from django.urls import path
from .views import index, AddSecurityView

urlpatterns = [
    path('', index, name='index'),
    path('data/add-security', AddSecurityView.as_view(), name='add-security'),
    path('accounts/', include('django.contrib.auth.urls')),
]