from django.urls import include, path

from .router import accounts_router, profile_router

urlpatterns = [
    path('', include(accounts_router.urls)),
    path('', include(profile_router.urls)),
]
