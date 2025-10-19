from __future__ import annotations

from django.apps import apps as django_apps
from django.utils.text import slugify
from rest_framework.routers import DefaultRouter

from apps.core.wcapi.viewsets import WCAPIModelViewSet
from apps.products import serializers as product_serializers


router = DefaultRouter()


def _register(model_label: str, serializer_cls):
    model_cls = django_apps.get_model("products", model_label)
    basename = slugify(model_cls._meta.model_name.replace("_", "-"))
    viewset_cls = type(
        f"{model_label}WCAPIViewSet",
        (WCAPIModelViewSet,),
        {
            "queryset": model_cls._default_manager.all(),
            "serializer_class": serializer_cls,
        },
    )
    router.register(basename, viewset_cls, basename=f"wcapi-{basename}")


_register("Item", product_serializers.ItemSerializer)
_register("Variant", product_serializers.VariantSerializer)
_register("Service", product_serializers.ServiceSerializer)
_register("ItemXref", product_serializers.ItemXrefSerializer)
_register("Serial", product_serializers.SerialSerializer)
_register("Specification", product_serializers.SpecificationSerializer)
_register("BillOfMaterial", product_serializers.BillOfMaterialSerializer)
_register("Catalog", product_serializers.CatalogSerializer)
_register("OrgItem", product_serializers.OrgItemSerializer)
_register("Warehouse", product_serializers.WarehouseSerializer)
_register("Usage", product_serializers.UsageSerializer)
_register("InventoryReservation", product_serializers.InventoryReservationSerializer)
_register("Flow", product_serializers.FlowSerializer)

urlpatterns = router.urls