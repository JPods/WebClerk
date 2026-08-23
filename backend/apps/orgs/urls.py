from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.orgs.views import (
    CustomerViewSet,
    EmployeeViewSet,
    ManufacturerViewSet,
    OrgBaseViewSet,
    RepViewSet,
    VendorViewSet,
)

app_name = 'orgs'

router = DefaultRouter()
router.register(r'orgs', OrgBaseViewSet, basename='org')
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'vendors', VendorViewSet, basename='vendor')
router.register(r'reps', RepViewSet, basename='rep')
router.register(r'employees', EmployeeViewSet, basename='employee')
router.register(r'manufacturers', ManufacturerViewSet, basename='manufacturer')

urlpatterns = [
    path('', include(router.urls)),
]