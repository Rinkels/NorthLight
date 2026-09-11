"""URL configuration for NorthLight.

Authentication uses Django's built-in views (login, logout, password reset)
under /accounts/. Application routes live in the `planning` app.
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("planning.urls")),
]
