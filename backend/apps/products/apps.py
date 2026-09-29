from django.apps import AppConfig


class ProductsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.products'
    def ready(self):  # pragma: no cover
        # Allocate and release: commands on an item (services/inventory/inventory_allocate.py).
        from .services.inventory import inventory_allocate
        inventory_allocate.register()
        from .behaviours import register_products
        register_products()
