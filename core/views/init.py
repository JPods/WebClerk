# Import only the views that actually exist
from .contact_view import WebContactView
from .edit_views import EditContactView
from .web_auth_views import WebSignupView, WebLoginView, WebLogoutView

# Remove imports for views that don't exist yet:
# from .edit_views import ManageAddressesView, AddAddressView, EditAddressView, DeleteAddressView

# Universal API views
from .generic_views import (
    UniversalQueryView,
    UniversalSaveView, 
    UniversalGetView,
    UniversalDeleteView,
    UniversalCloneView,
    UniversalCRUDView
)

__all__ = [
    'WebContactView',
    'EditContactView', 
    'WebSignupView',
    'WebLoginView', 
    'WebLogoutView',
    'UniversalQueryView',
    'UniversalSaveView',
    'UniversalGetView', 
    'UniversalDeleteView',
    'UniversalCloneView',
    'UniversalCRUDView',
]