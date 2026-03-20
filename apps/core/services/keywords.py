from apps.core.constants.keyword_requirements import get_keyword_requirements
from apps.core.services.cache_service import cache_service
from django.apps import apps
from django.db import models
from common.ignore_fields import IGNORE_WORDS


DEFAULT_TEXT_SCALAR_FIELD_TYPES = (
    models.CharField,
    models.TextField,
    models.EmailField,
    models.URLField,
    models.SlugField,
    models.UUIDField,
)

EXCLUDED_SCALAR_KEYWORD_FIELDS = {
    "password",
    "comment",
}


def _default_scalar_keyword_fields(model):
    """Return text-like scalar field names used for baseline keyword extraction."""
    fields = []
    for field in getattr(model._meta, "concrete_fields", []):
        if (
            isinstance(field, DEFAULT_TEXT_SCALAR_FIELD_TYPES)
            and field.name not in EXCLUDED_SCALAR_KEYWORD_FIELDS
        ):
            fields.append(field.name)
    return fields


def _extract_keywords_from_value(value):
    """
    Extract keywords from a value, handling various data types including JSON structures.
    Applies filtering for common words and minimum length.
    """
    keywords = []

    if value is None:
        return keywords

    if isinstance(value, str):
        # Split by space and comma, strip, lowercase, filter empty and apply word filtering
        for word in value.replace(',', ' ').split():
            word = word.strip().lower()
            if word:
                # Split by punctuation and process each token
                for raw in word.split():
                    token = raw.strip('.,!?;:"()[]{}')
                    # Filter common words and apply minimum length
                    if len(token) > 2 and token not in IGNORE_WORDS:
                        keywords.append(token)
    elif isinstance(value, list):
        # Handle JSON arrays
        for item in value:
            keywords.extend(_extract_keywords_from_value(item))
    elif isinstance(value, dict):
        # Handle JSON objects - extract all string values recursively
        for key, val in value.items():
            keywords.extend(_extract_keywords_from_value(val))
    else:
        # Convert other types to string and apply filtering
        str_value = str(value).strip().lower()
        if str_value:
            for raw in str_value.split():
                token = raw.strip('.,!?;:"()[]{}')
                if len(token) > 2 and token not in IGNORE_WORDS:
                    keywords.append(token)

    return keywords


def _extract_keywords_from_field(record, field_path):
    """
    Extract keywords from a field path (supports immediate nested access only, e.g., 'action.en' or 'refs.keywords').
    Returns a list of keyword strings.
    """
    try:
        # Handle immediate nested field access (e.g., 'action.en', 'refs.keywords')
        # But don't go deeper than one level
        if '.' in field_path:
            parts = field_path.split('.')
            if len(parts) > 2:
                # Only handle up to 2 levels deep
                return []
            
            value = record
            for part in parts:
                if isinstance(value, dict):
                    # Handle dictionary access (for JSONField values)
                    value = value.get(part)
                elif hasattr(value, part):
                    # Handle Django model attributes
                    value = getattr(value, part, None)
                else:
                    # Field doesn't exist
                    return []
                
                if value is None:
                    return []
        else:
            # Handle simple field access on Django model
            value = getattr(record, field_path, None)
            
            # Special handling for 'ida' field - this might be a custom field
            # that should be treated as a keyword directly
            if field_path == 'ida' and value is not None:
                return [str(value).lower()]

        return _extract_keywords_from_value(value)

    except Exception:
        return []


def build_keywords_for_record(model_name, record_id):
    """
    Build keywords for a record using prioritized field configuration.
    Processes self fields first, then related model fields in priority order.
    """
    try:
        # Get settings from cache first to determine the app
        cache_key = cache_service.make_key('settings', 'refs_setup')
        requirements = cache_service.get(cache_key)
        if requirements is None:
            # Fallback to loading from DB if cache miss
            requirements = get_keyword_requirements()
        
        model_config = requirements.get(model_name, {})
        
        # Try to find the model in any app
        model = None
        for app_config in apps.get_app_configs():
            try:
                model = app_config.get_model(model_name)
                break
            except Exception:
                continue
        
        if not model:
            return []
            
        # Check if record exists first to avoid query exceptions
        try:
            record = model.objects.get(id=record_id)
        except model.DoesNotExist:
            return []
        
        keywords = set()  # Use set for automatic deduplication

        # Baseline extraction: always include scalar text-like model fields.
        # This keeps keyword search useful even when refs_setup is missing.
        for field_name in _default_scalar_keyword_fields(model):
            keywords.update(_extract_keywords_from_field(record, field_name))

        refs_data = getattr(record, 'refs', None)
        if refs_data and isinstance(refs_data, dict):
            # Aggregate refs.tags into refs.keywords.
            keywords.update(_extract_keywords_from_value(refs_data.get('tags', [])))

        # Process self fields first (highest priority)
        self_fields = model_config.get('self_fields', [])
        for field_path in self_fields:
            field_keywords = _extract_keywords_from_field(record, field_path)
            keywords.update(field_keywords)

        # Process related models with safety limits
        related_keywords = model_config.get('related_keywords', {})

        if refs_data and isinstance(refs_data, dict):
            links = refs_data.get('links', {})
            processed_models = set()  # Prevent infinite loops

            # Process related_keywords (new format - dict of model names to field arrays)
            for related_model_name, field_paths in related_keywords.items():
                # Prevent infinite loops by tracking processed models
                if related_model_name in processed_models:
                    continue
                processed_models.add(related_model_name)
                
                # Limit the number of related models processed to prevent infinite loops
                if len(processed_models) > 10:  # Reasonable limit
                    break

                # Get related record IDs from refs.links
                # Try both singular and plural forms
                link_keys = [related_model_name, related_model_name + 's']
                related_ids = []
                for link_key in link_keys:
                    if link_key in links:
                        ids = links[link_key]
                        if isinstance(ids, list):
                            related_ids.extend(ids)
                        break

                if not related_ids:
                    continue

                # Try to find the related model in any app
                related_model = None
                for app_config in apps.get_app_configs():
                    try:
                        related_model = app_config.get_model(related_model_name)
                        break
                    except Exception:
                        continue

                if not related_model:
                    continue

                # Query related records with limit to prevent performance issues
                try:
                    related_records = related_model.objects.filter(id__in=related_ids)[:100]  # Limit query size

                    # Extract keywords from each related record's specified fields
                    for related_record in related_records:
                        for field_path in field_paths:
                            # Handle special case for refs.keywords
                            if field_path == 'refs.keywords':
                                refs = getattr(related_record, 'refs', None)
                                if refs and isinstance(refs, dict):
                                    kw = refs.get('keywords', [])
                                    if isinstance(kw, list):
                                        keywords.update(kw)
                            else:
                                field_keywords = _extract_keywords_from_field(related_record, field_path)
                                keywords.update(field_keywords)

                except Exception:
                    # Skip if related model doesn't exist or query fails
                    continue

        return sorted(keywords)

    except Exception as e:
        # Log the error for debugging but don't fail the save operation
        import logging
        logging.getLogger(__name__).warning(f"Failed to build keywords for {model_name}:{record_id} - {str(e)}")
        return []

def create_pending_keyword_update(model_name, record_id, data):
    # Create a Pending record for later processing (local import to avoid circular dependency)
    from apps.core.models.pending import Pending
    cache = Pending.objects.create(
        ida=f"{model_name}:{record_id}",
        model_name=model_name,
        data=data
    )
    return cache