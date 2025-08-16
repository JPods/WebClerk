# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/communications/urls.py
from django.urls import path
from .views import (
    LocationView, LocationDetailView,
    EmailView, EmailDetailView,
    PhoneView, PhoneDetailView,
    DomainView, DomainDetailView,
)

app_name = 'communications'

urlpatterns = [
    # All communications management handled by Universal API
# managed in core/urls.py
   ] 
