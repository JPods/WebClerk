from apps.core.models.pending import Pending

def build_keywords_for_contact(contact_id):
    # Query related records and build keywords for a contact
    pass

def create_pending_keyword_update(model_name, record_id, data):
    # Create a Pending record for later processing
    cache = Pending.objects.create(
    ida=f"{model_name}:{record_id}",
    model_name=model_name,
        data=data
    )
    return cache