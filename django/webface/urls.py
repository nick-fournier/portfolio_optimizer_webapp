# users/urls.py

from django.conf.urls import url, include
from django.urls import path
from .views import index

urlpatterns = [
    # path('', index, name='index'),
    url(r"^accounts/", include("django.contrib.auth.urls")),
    url(r"^", index, name="index"),
]