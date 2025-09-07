# path: apps/communications/urls.py
from django.urls import path
from .views.domain import DomainView, DomainDetailView, DomainSearchView
from .views.email import EmailView, EmailDetailView
from .views.phone import PhoneView, PhoneDetailView
from .views.address import LocationView, LocationDetailView

app_name = 'communications'

urlpatterns = [
    path('domains/', DomainView.as_view(), name='domain-list'),
    path('domains/<int:pk>/', DomainDetailView.as_view(), name='domain-detail'),
    path('domains/search/', DomainSearchView.as_view(), name='domain-search'),
    # Email endpoints (now using unified response envelope)
    path('emails/', EmailView.as_view(), name='email-list'),
    path('emails/<int:pk>/', EmailDetailView.as_view(), name='email-detail'),
    # Phone endpoints
    path('phones/', PhoneView.as_view(), name='phone-list'),
    path('phones/<int:pk>/', PhoneDetailView.as_view(), name='phone-detail'),
    # Address (Location) endpoints
    path('addresses/', LocationView.as_view(), name='address-list'),
    path('addresses/<int:pk>/', LocationDetailView.as_view(), name='address-detail'),
] 
