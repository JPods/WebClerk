from apps.core.constants.keyword_requirements import get_keyword_requirements
from apps.core.services.cache_service import cache_service
from django.apps import apps
from common.ignore_fields import IGNORE_WORDS

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
    Extract keywords from a field path (supports nested access like 'action.en' or 'assigned_to.name').
    Returns a list of keyword strings.
    """
    try:
        # Handle nested field access (e.g., 'action.en', 'assigned_to.name')
        if '.' in field_path:
            parts = field_path.split('.')
            value = record

            for i, part in enumerate(parts):
                if isinstance(value, dict):
                    # Handle dictionary access (for JSONField values)
                    value = value.get(part)
                elif isinstance(value, list) and part.isdigit():
                    # Handle array indexing like assigned_to.0
                    index = int(part)
                    if 0 <= index < len(value):
                        value = value[index]
                    else:
                        return []
                elif hasattr(value, part):
                    # Handle Django model attributes
                    value = getattr(value, part, None)
                else:
                    # Special handling for extracting nested properties from arrays of objects
                    # e.g., 'assigned_to.name' should extract 'name' from each object in the array
                    if isinstance(value, list) and all(isinstance(item, dict) for item in value):
                        # Extract the nested property from each object in the array
                        nested_values = []
                        remaining_parts = parts[i:]
                        for item in value:
                            item_value = item
                            for nested_part in remaining_parts:
                                if isinstance(item_value, dict):
                                    item_value = item_value.get(nested_part)
                                elif hasattr(item_value, nested_part):
                                    item_value = getattr(item_value, nested_part, None)
                                else:
                                    item_value = None
                                    break
                            if item_value is not None:
                                nested_values.append(item_value)
                        return _extract_keywords_from_value(nested_values)
                    return []

                if value is None:
                    return []
        else:
            # Handle simple field access on Django model
            value = getattr(record, field_path, None)

        return _extract_keywords_from_value(value)

    except Exception:
        return []


def build_keywords_for_record(model_name, record_id):
    """
    Build keywords for a record using prioritized field configuration.
    Processes self fields first, then related model fields in priority order.
    """
    try:
        # Get the model class
        model = apps.get_model('core', model_name)
        record = model.objects.get(id=record_id)

        # Get settings from cache
        cache_key = cache_service.make_key('settings', 'refs_setup')
        requirements = cache_service.get(cache_key)
        if requirements is None:
            # Fallback to loading from DB if cache miss
            requirements = get_keyword_requirements()
        if model_name not in requirements:
            return []

        model_config = requirements[model_name]
        keywords = set()  # Use set for automatic deduplication

        # Process self fields first (highest priority)
        self_fields = model_config.get('self_fields', [])
        for field_path in self_fields:
            field_keywords = _extract_keywords_from_field(record, field_path)
            keywords.update(field_keywords)

        # Process related models in configuration order
        related_models = model_config.get('related_models', [])
        related_keywords = model_config.get('related_keywords', {})
        refs_data = getattr(record, 'refs', None)

        if refs_data and isinstance(refs_data, dict):
            links = refs_data.get('links', {})

            # Process related_models (legacy format - list of model names with field paths)
            if isinstance(related_models, dict):
                for related_model_name, related_fields in related_models.items():
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

                    # Query related records
                    try:
                        related_model = apps.get_model('core', related_model_name)
                        related_records = related_model.objects.filter(id__in=related_ids)

                        # Extract keywords from each related record's specified fields
                        for related_record in related_records:
                            for field_path in related_fields:
                                field_keywords = _extract_keywords_from_field(related_record, field_path)
                                keywords.update(field_keywords)

                    except Exception:
                        # Skip if related model doesn't exist or query fails
                        continue

            # Process related_keywords (new format - dict of model names to field arrays)
            for related_model_name, field_paths in related_keywords.items():
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

                # Query related records
                try:
                    related_model = apps.get_model('core', related_model_name)
                    related_records = related_model.objects.filter(id__in=related_ids)

                    # Extract keywords from each related record's specified fields
                    for related_record in related_records:
                        for field_path in field_paths:
                            field_keywords = _extract_keywords_from_field(related_record, field_path)
                            keywords.update(field_keywords)

                except Exception:
                    # Skip if related model doesn't exist or query fails
                    continue

        return list(keywords)  # Convert set back to list

    except Exception as e:
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