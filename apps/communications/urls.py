# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/communications/urls.py
from django.urls import path
from .views.domain import DomainView, DomainDetailView, DomainSearchView

app_name = 'communications'

urlpatterns = [
    path('domains/', DomainView.as_view(), name='domain-list'),
    path('domains/<int:pk>/', DomainDetailView.as_view(), name='domain-detail'),
    path('domains/search/', DomainSearchView.as_view(), name='domain-search'),
] 
