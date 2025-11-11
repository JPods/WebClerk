from apps.core.models.pending import Pending
from apps.core.constants.keyword_requirements import get_keyword_requirements
from django.apps import apps

def build_keywords_for_contact(contact_id):
    # Query related records and build keywords for a contact
    pass

def build_keywords_for_record(model_name, record_id):
    """
    Build keywords for a record by looping through refs.links to get denormalized data.
    """
    try:
        # Get the model class
        model = apps.get_model('core', model_name)
        record = model.objects.get(id=record_id)

        # Get keyword requirements for this model
        requirements = get_keyword_requirements()
        if model_name not in requirements:
            return []

        model_config = requirements[model_name]
        keywords = []

        # Check if record has refs data
        refs_data = getattr(record, 'refs', None)
        if refs_data and isinstance(refs_data, dict):
            links = refs_data.get('links', {})

            # Loop through each link type (emails, phones, locations, etc.)
            for link_type, ids in links.items():
                if not ids:
                    continue

                # Get the related model name from link_type (singular)
                related_model_name = link_type[:-1] if link_type.endswith('s') else link_type

                # Get keyword requirements for the related model
                if related_model_name in requirements:
                    related_config = requirements[related_model_name]

                    # Query related records
                    try:
                        related_model = apps.get_model('core', related_model_name)
                        related_records = related_model.objects.filter(id__in=ids)

                        for related_record in related_records:
                            # Get fields to include in keywords
                            # For now, assume we want all char fields, but this could be filtered
                            for field_name in dir(related_record):
                                if not field_name.startswith('_'):
                                    field_value = getattr(related_record, field_name, None)
                                    if isinstance(field_value, str) and field_value.strip():
                                        keywords.append(field_value.strip().lower())

                    except Exception as e:
                        # Skip if related model doesn't exist or query fails
                        continue

        return list(set(keywords))  # Remove duplicates

    except Exception as e:
        return []

def create_pending_keyword_update(model_name, record_id, data):
    # Create a Pending record for later processing
    cache = Pending.objects.create(
    ida=f"{model_name}:{record_id}",
    model_name=model_name,
        data=data
    )
    return cache