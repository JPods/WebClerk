"""
Frontend Dropdown Service

Provides dropdown options for React frontend components.
Reads from Setting records with purpose="front_end-ddl", falls back to hardcoded defaults.
"""

from typing import Dict, List, Any, Optional
from django.core.cache import cache
from apps.core.models.contact import Contact
from apps.core.models.setting import Setting
from apps.core.services.cache_service import cache_service


class FrontendDropdownsService:
    """Service for managing frontend dropdown options."""

    CACHE_KEY = "frontend_dropdowns"
    CACHE_TTL = 3600  # 1 hour

    # Hardcoded fallback defaults
    DEFAULT_DROPDOWNS = {
        "assigned_to_ddl": [],  # Will be populated dynamically
        "difficulty_ddl": ["1", "5", "25", "50", "101"],
        "priority_ddl": ["UKN", "Low", "Medium", "High", "Immediate"],
    }

    @classmethod
    def _get_setting_dropdown(cls, name: str) -> Optional[Any]:
        """Get dropdown from Setting records."""
        try:
            setting = Setting.objects.filter(
                purpose='front_end-ddl',
                name=f'frontend-dropdown-{name}',
                is_active=True
            ).first()
            return setting.data if setting else None
        except Exception:
            return None

    @staticmethod
    def get_assigned_to_ddl() -> List[Dict[str, Any]]:
        """Get dropdown options for assigned_to field.

        Returns list of contacts formatted as:
        [{"label": "Full Name", "value": id}, ...]
        """
        contacts = Contact.objects.filter(is_active=True).order_by('name_last', 'name_first')
        return [
            {
                "label": contact.get_full_name(),
                "value": contact.id
            }
            for contact in contacts
        ]

    @classmethod
    def get_difficulty_ddl(cls) -> List[str]:
        """Get dropdown options for difficulty field."""
        return cls._get_setting_dropdown('difficulty_ddl') or cls.DEFAULT_DROPDOWNS['difficulty_ddl']

    @classmethod
    def get_priority_ddl(cls) -> List[str]:
        """Get dropdown options for priority field."""
        return cls._get_setting_dropdown('priority_ddl') or cls.DEFAULT_DROPDOWNS['priority_ddl']

    @classmethod
    def get_all_dropdowns(cls) -> Dict[str, Any]:
        """Get all frontend dropdowns.

        Returns:
            Dict with dropdown names as keys and options as values.
        """
        # Try cache first
        cached = cache_service.get(cls.CACHE_KEY)
        if cached:
            return cached

        # Generate dropdowns (assigned_to is always dynamic)
        dropdowns = {
            "assigned_to_ddl": cls.get_assigned_to_ddl(),
            "difficulty_ddl": cls.get_difficulty_ddl(),
            "priority_ddl": cls.get_priority_ddl(),
        }

        # Cache the result
        cache_service.set(cls.CACHE_KEY, dropdowns, cls.CACHE_TTL)

        return dropdowns

    @classmethod
    def invalidate_cache(cls) -> None:
        """Invalidate the dropdowns cache."""
        cache_service.delete(cls.CACHE_KEY)

    @classmethod
    def get_dropdown(cls, name: str) -> Any:
        """Get a specific dropdown by name."""
        dropdowns = cls.get_all_dropdowns()
        return dropdowns.get(name)


# Global instance
frontend_dropdowns_service = FrontendDropdownsService()