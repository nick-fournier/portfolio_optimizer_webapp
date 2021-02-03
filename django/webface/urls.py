# users/urls.py

from django.conf.urls import url
from django.urls import path
from .views import dashboard, index

urlpatterns = [
    path('', index, name='index'),
    url(r"^dashboard/", dashboard, name="dashboard"),
]