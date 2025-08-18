#Tip: You can call load_keyword_requirements() in your 
# AppConfig’s ready() method and cache the result.

from core.models import Setting
from django.db.utils import ProgrammingError, OperationalError

def get_keyword_requirements():
    """Load keyword requirements lazily from DB."""
    try:
        return {
            s.value: s.extra_data
            for s in Setting.objects.filter(purpose="keywords_from", is_active=True)
        }
    except (ProgrammingError, OperationalError):
        # Happens during first migrate (table not created yet)
        return {}