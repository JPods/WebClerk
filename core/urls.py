from django.urls import path
from .views.contact_view import WebContactView
from .views.action_view import ActionView, ActionDetailView
from .views.web_auth_views import WebSignupView, WebLoginView, WebLogoutView
from .views.edit_views import EditContactView, ManageAddressesView, AddAddressView, EditAddressView, DeleteAddressView

app_name = 'core'

urlpatterns = [
    # Web-based authentication pages
    path('web-signup/', WebSignupView.as_view(), name='web-signup'),
    path('web-login/', WebLoginView.as_view(), name='web-login'),
    path('web-logout/', WebLogoutView.as_view(), name='logout'),
    path('web-contact/', WebContactView.as_view(), name='web-contact'),
    
    # Contact editing pages
    path('edit-contact/', EditContactView.as_view(), name='edit-contact'),
    
    # Actions
    path('actions/', ActionView.as_view(), name='action-list'),
    path('actions/<int:pk>/', ActionDetailView.as_view(), name='action-detail'),
    
    # Address management pages
    path('manage-addresses/', ManageAddressesView.as_view(), name='manage-addresses'),
    path('add-address/', AddAddressView.as_view(), name='add-address'),
    path('edit-address/<int:pk>/', EditAddressView.as_view(), name='edit-address'),
    path('delete-address/<int:pk>/', DeleteAddressView.as_view(), name='delete-address'),
    
    # API endpoints commented out until Universal API is implemented
    # These will be replaced by Universal API endpoints:
    # POST /WCapi/query/     - Query any table
    # POST /WCapi/save/      - Save any record  
    # POST /WCapi/get/       - Get single record
    # POST /WCapi/delete/    - Delete any record
    # POST /WCapi/clone/     - Clone any record
]
