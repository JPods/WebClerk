from django.urls import path
from core.views import (
    WebContactView, WebSignupView, WebLoginView, WebLogoutView,
    EditContactView, UniversalCRUDView, UniversalQueryView,
    UniversalGetView, UniversalSaveView, UniversalDeleteView
)

urlpatterns = [
    # Authentication
    path('signup/', WebSignupView.as_view(), name='signup'),
    path('login/', WebLoginView.as_view(), name='login'),
    path('logout/', WebLogoutView.as_view(), name='logout'),
    
    # Contact management
    path('contact/', WebContactView.as_view(), name='contact'),
    path('edit-contact/<int:id_contact>/', EditContactView.as_view(), name='edit-contact'),
    
    # Universal API Management - Your PERFECT template!
    path('WCapi/<str:table_name>/manage/', UniversalCRUDView.as_view(), name='universal-manage'),
    
    # Universal API Endpoints
    path('WCapi/query/', UniversalQueryView.as_view(), name='universal-query'),
    path('WCapi/get/', UniversalGetView.as_view(), name='universal-get'),
    path('WCapi/save/', UniversalSaveView.as_view(), name='universal-save'),
    path('WCapi/delete/', UniversalDeleteView.as_view(), name='universal-delete'),
]

