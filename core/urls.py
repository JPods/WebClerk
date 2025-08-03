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
    path('profile/', TemplateView.as_view(template_name='core/user.html'), name='user-profile'),
    path('contacts/', TemplateView.as_view(template_name='core/manager.html'), name='admin-contacts'),
    
        # Dedicated Management Pages
    path('manage/actions/', TemplateView.as_view(template_name='core/manage_actions.html'), name='manage-actions'),
    

    # Universal API endpoints
    # Rare for sockets. We will more likely create an api app for websockets
    path('connect/', TemplateView.as_view(template_name='core/connect.html'), name='connect'),
    # delete
    path('WCapi/delete/', UniversalCRUDView.as_view(), name='delete-crud'),
    # list/read records
    # path('WCapi/query/', UniversalQueryView.as_view(), name='query'),
    path('WCapi/get/', UniversalGetView.as_view(), name='get'),
    # Headers only
    path('WCapi/head/', UniversalCRUDView.as_view(), name='head'),
    # Help page for WCapi - could be a static page, duplicate of options and root? QQQ
    path('WCapi/help/', UniversalCRUDView.as_view(), name='core/help.html'),
    # do not know
    path('WCapi/manage/', UniversalCRUDView.as_view(), name='manage'),
    # options, supports CORS preflight, method to get allowed methods, meta info
    path('WCapi/options/', UniversalCRUDView.as_view(), name='options'),
    # partial update
    path('WCapi/patch/', UniversalCRUDView.as_view(), name='patch'),
    # create or full update
    path('WCapi/post/', UniversalCRUDView.as_view(), name='post'),
    # full update
    path('WCapi/put/', UniversalCRUDView.as_view(), name='put'),
    # save was used in 4D, replace with post/put
    # path('WCapi/save/', UniversalSaveView.as_view(), name='save'),
    # Root endpoint for WCapi
    # Diagnostic endpoint for tracing
    path('WCapi/trace/', UniversalCRUDView.as_view(), name='trace'),

]
