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
<<<<<<< HEAD:communications/urls.py
    # All communications management handled by Universal API
# managed in core/urls.py
   ] 
=======
    path('locations/', LocationView.as_view(), name='location-list'),
    path('locations/<int:pk>/', LocationDetailView.as_view(), name='location-detail'),

    path('emails/', EmailView.as_view(), name='email-list'),
    path('emails/<int:pk>/', EmailDetailView.as_view(), name='email-detail'),

    path('phones/', PhoneView.as_view(), name='phone-list'),
    path('phones/<int:pk>/', PhoneDetailView.as_view(), name='phone-detail'),
    
    path('domains/', DomainView.as_view(), name='domain-list'),
    path('domains/<int:pk>/', DomainDetailView.as_view(), name='domain-detail'),
]
>>>>>>> 01558f6ebce5d18d828e022158343627fc8162d8:apps/communications/urls.py
