from django.urls import path
from core.views import (
    HomeView, AboutView,
    WebSignupView, WebLoginView, WebLogoutView,
    UniversalCRUDView, UniversalGetView, UniversalQueryView,
    UniversalSaveView, UniversalDeleteView
)
from django.views.generic import TemplateView

urlpatterns = [
    # Home and About pages
    path('', HomeView.as_view(), name='home'),
    path('about/', AboutView.as_view(), name='about'),
    
    # Authentication
    path('signup/', WebSignupView.as_view(), name='signup'),
    path('login/', WebLoginView.as_view(), name='login'),
    path('logout/', WebLogoutView.as_view(), name='logout'),
    
    # Contact Management Pages
    path('profile/', TemplateView.as_view(template_name='core/contact_user.html'), name='user-profile'),
    path('contacts/', TemplateView.as_view(template_name='core/contact_admin.html'), name='admin-contacts'),
    
        # Dedicated Management Pages
    path('manage/actions/', TemplateView.as_view(template_name='core/manage_actions.html'), name='manage-actions'),
    

    # Universal API endpoints
    path('WCapi/manage/', UniversalCRUDView.as_view(), name='universal-manage'),
    path('WCapi/get/', UniversalGetView.as_view(), name='universal-get'),
    path('WCapi/query/', UniversalQueryView.as_view(), name='universal-query'),
    path('WCapi/save/', UniversalSaveView.as_view(), name='universal-save'),
    path('WCapi/delete/', UniversalDeleteView.as_view(), name='universal-delete'),
]