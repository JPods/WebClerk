from apps.core.models.pending import Pending

def process_pending_keywords():
    # Query all pending Pending records and process them
    pending = Pending.objects.all()
    for record in pending:
        # Process record.data and update keywords
        pass

def clear_processed_pending():
    # Remove processed Pending records
    Pending.objects.filter(...).delete()

def get_pending_count():
    return Pending.objects.count()