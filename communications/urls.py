from django.urls import path
from .views import (
    AddressView, AddressDetailView,
    EmailView, EmailDetailView,
    PhoneView, PhoneDetailView,
    DomainView, DomainDetailView,
)

app_name = 'communications'

urlpatterns = [
    path('addresses/', AddressView.as_view(), name='address-list'),
    path('addresses/<int:pk>/', AddressDetailView.as_view(), name='address-detail'),

    path('emails/', EmailView.as_view(), name='email-list'),
    path('emails/<int:pk>/', EmailDetailView.as_view(), name='email-detail'),

    path('phones/', PhoneView.as_view(), name='phone-list'),
    path('phones/<int:pk>/', PhoneDetailView.as_view(), name='phone-detail'),
    
    path('domains/', DomainView.as_view(), name='domain-list'),
    path('domains/<int:pk>/', DomainDetailView.as_view(), name='domain-detail'),
]