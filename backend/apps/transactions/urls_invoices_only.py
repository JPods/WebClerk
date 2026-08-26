from django.urls import path
from rest_framework import generics, permissions
from apps.transactions.models import Invoice, InvoiceLine, WorkOrder, WorkOrderLine, Order, OrderLine
from apps.transactions.serializers.invoice_serializers import (
    InvoiceSerializer, InvoiceLineSerializer,
)
from apps.transactions.serializers.workorder_serializers import (
    WorkOrderSerializer, WorkOrderLineSerializer,
)
from apps.transactions.serializers.order_serializers import (
    OrderSerializer, OrderLineSerializer,
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
    # Orders
    path('sales-orders/',
         generics.ListCreateAPIView.as_view(
             queryset=Order.objects.all().order_by('-id'),
             serializer_class=OrderSerializer,
             permission_classes=[BasePermission]
         ),
         name='sales-order-list'
    ),
    path('sales-orders/<int:pk>/',
         generics.RetrieveUpdateDestroyAPIView.as_view(
             queryset=Order.objects.all(),
             serializer_class=OrderSerializer,
             permission_classes=[BasePermission]
         ),
         name='sales-order-detail'
    ),
    path('sales-order-lines/',
         generics.ListCreateAPIView.as_view(
             queryset=OrderLine.objects.all().order_by('-id'),
             serializer_class=OrderLineSerializer,
             permission_classes=[BasePermission]
         ),
         name='sales-order-line-list'
    ),
    path('sales-order-lines/<int:pk>/',
         generics.RetrieveUpdateDestroyAPIView.as_view(
             queryset=OrderLine.objects.all(),
             serializer_class=OrderLineSerializer,
             permission_classes=[BasePermission]
         ),
         name='sales-order-line-detail'
    ),
    path('invoices/', InvoiceListCreate.as_view(), name='invoice-list'),
    path('invoices/<int:pk>/', InvoiceRetrieveUpdate.as_view(), name='invoice-detail'),
    path('invoice-lines/', InvoiceLineListCreate.as_view(), name='invoice-line-list'),
    path('invoice-lines/<int:pk>/', InvoiceLineRetrieveUpdate.as_view(), name='invoice-line-detail'),
    # WorkOrders
    path('work-orders/',
         generics.ListCreateAPIView.as_view(
             queryset=WorkOrder.objects.all().order_by('-id'),
             serializer_class=WorkOrderSerializer,
             permission_classes=[BasePermission]
         ),
         name='workorder-list'
    ),
    path('work-orders/<int:pk>/',
         generics.RetrieveUpdateDestroyAPIView.as_view(
             queryset=WorkOrder.objects.all(),
             serializer_class=WorkOrderSerializer,
             permission_classes=[BasePermission]
         ),
         name='workorder-detail'
    ),
    path('work-order-lines/',
         generics.ListCreateAPIView.as_view(
             queryset=WorkOrderLine.objects.all().order_by('-id'),
             serializer_class=WorkOrderLineSerializer,
             permission_classes=[BasePermission]
         ),
         name='workorder-line-list'
    ),
    path('work-order-lines/<int:pk>/',
         generics.RetrieveUpdateDestroyAPIView.as_view(
             queryset=WorkOrderLine.objects.all(),
             serializer_class=WorkOrderLineSerializer,
             permission_classes=[BasePermission]
         ),
         name='workorder-line-detail'
    ),
]