from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.orgs.views import CustomerViewSet

app_name = 'orgs'

router = DefaultRouter()
router.register(r'customers', CustomerViewSet, basename='customer')

urlpatterns = [
    path('', include(router.urls)),
]