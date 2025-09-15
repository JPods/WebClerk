from django.urls import path
from rest_framework import generics, permissions
from apps.transactions.models import Invoice, InvoiceLine
from apps.transactions.serializers.invoice_serializers import (
    InvoiceSerializer, InvoiceLineSerializer,
)


class BasePermission(permissions.IsAuthenticated):
    pass


class InvoiceListCreate(generics.ListCreateAPIView):
    queryset = Invoice.objects.all().order_by('-id')
    serializer_class = InvoiceSerializer
    permission_classes = [BasePermission]


class InvoiceRetrieveUpdate(generics.RetrieveUpdateDestroyAPIView):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [BasePermission]


class InvoiceLineListCreate(generics.ListCreateAPIView):
    queryset = InvoiceLine.objects.all().order_by('-id')
    serializer_class = InvoiceLineSerializer
    permission_classes = [BasePermission]
    filterset_fields = ['parent_id', 'status']
    search_fields = ['item__description', 'item__uuid_item']
    ordering_fields = ['id', 'parent_id', 'status']


class InvoiceLineRetrieveUpdate(generics.RetrieveUpdateDestroyAPIView):
    queryset = InvoiceLine.objects.all()
    serializer_class = InvoiceLineSerializer
    permission_classes = [BasePermission]


urlpatterns = [
    path('invoices/', InvoiceListCreate.as_view(), name='invoice-list'),
    path('invoices/<int:pk>/', InvoiceRetrieveUpdate.as_view(), name='invoice-detail'),
    path('invoice-lines/', InvoiceLineListCreate.as_view(), name='invoice-line-list'),
    path('invoice-lines/<int:pk>/', InvoiceLineRetrieveUpdate.as_view(), name='invoice-line-detail'),
]