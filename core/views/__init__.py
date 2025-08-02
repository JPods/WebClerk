# Import only the views that actually exist
from .contact_view import WebContactView
from .edit_views import EditContactView
from .web_auth_views import WebSignupView, WebLoginView, WebLogoutView

# Import Universal API views if they exist
try:
    from .generic_views import (
        UniversalQueryView,
        UniversalSaveView, 
        UniversalGetView,
        UniversalDeleteView,
        UniversalCloneView,
        UniversalCRUDView
    )
    GENERIC_VIEWS_AVAILABLE = True
except ImportError:
    GENERIC_VIEWS_AVAILABLE = False

__all__ = [
    'WebContactView',
    'EditContactView', 
    'WebSignupView',
    'WebLoginView', 
    'WebLogoutView',
]

if GENERIC_VIEWS_AVAILABLE:
    __all__.extend([
        'UniversalQueryView',
        'UniversalSaveView',
        'UniversalGetView', 
        'UniversalDeleteView',
        'UniversalCloneView',
        'UniversalCRUDView',
    ])