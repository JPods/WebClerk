# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/core/services/keywords.py
from core.models.pending import Pending

def build_keywords_for_contact(contact_id):
    # Query related records and build keywords for a contact
    pass

def create_pending_keyword_update(table_name, record_id, data):
    # Create a Pending record for later processing
    cache = Pending.objects.create(
        ida=f"{table_name}:{record_id}",
        table_name=table_name,
        data=data
    )
    return cache