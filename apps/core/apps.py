from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "apps.core"
    label = "core"

    def ready(self):
        # Initialize WCAPI registry
        try:
            from .wcapi import registry
            registry.refresh_from_settings()
        except Exception:
            pass

        # Initialize constants from database settings
        try:
            from .constants.constants_init import refresh_cached_constants
            from .constants.mandatory_constants import ensure_mandatory_constants_exist
            refresh_cached_constants()
            # Ensure mandatory constants exist
            result = ensure_mandatory_constants_exist()
            if result['created']:
                print(f"Created mandatory constants: {', '.join(result['created'])}")
        except Exception as e:
            print(f"Warning: Failed to initialize constants: {e}")
            pass
