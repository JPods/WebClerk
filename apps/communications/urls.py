# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/communications/urls.py
from django.urls import path
from .views.domain import DomainView, DomainDetailView, DomainSearchView
from .views.email import EmailView, EmailDetailView

app_name = 'communications'

urlpatterns = [
    path('domains/', DomainView.as_view(), name='domain-list'),
    path('domains/<int:pk>/', DomainDetailView.as_view(), name='domain-detail'),
    path('domains/search/', DomainSearchView.as_view(), name='domain-search'),
    # Email endpoints (now using unified response envelope)
    path('emails/', EmailView.as_view(), name='email-list'),
    path('emails/<int:pk>/', EmailDetailView.as_view(), name='email-detail'),
] 
