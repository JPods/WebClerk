from django.urls import path
from .views import (
    AddressView, AddressDetailView,
    EmailView, EmailDetailView,
    PhoneView, PhoneDetailView,
    DomainView, DomainDetailView,
)

app_name = 'communications'

urlpatterns = [
    # All communications management handled by Universal API
# managed in core/urls.py
   ] 
