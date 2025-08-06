from django.urls import path
from core.views import (
    HomeView, AboutView,
    WebSignupView, WebLoginView, WebLogoutView,
    UniversalCRUDView
    
)
from django.views.generic import TemplateView

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Home and About pages
    path('', HomeView.as_view(), name='home'),
    path('about/', AboutView.as_view(), name='about'),
    
    # Authentication
    path('signup/', WebSignupView.as_view(), name='signup'),
    path('login/', WebLoginView.as_view(), name='login'),
    path('logout/', WebLogoutView.as_view(), name='logout'),
    
   
        # Dedicated Management Pages
    path('manage/actions/', TemplateView.as_view(template_name='core/manage_actions.html'), name='manage-actions'),
    path('user/', TemplateView.as_view(template_name='core/user.html'), name='users'),
    path('manager/', TemplateView.as_view(template_name='core/manager.html'), name='manager'),
    # Universal API endpoints
    # Rare for sockets. We will more likely create an api app for websockets
    

    path('wcapi/connect/', UniversalCRUDView.as_view(template_name='core/connect.html'), name='connect'),
    
    # delete
    path('wcapi/delete/', UniversalCRUDView.as_view(), name='delete-crud'),
    
    # list/read records
    path('wcapi/get/', UniversalCRUDView.as_view(), name='get'),
    
    # Headers only
    path('wcapi/head/', UniversalCRUDView.as_view(), name='head'),
    
    # Help page for wcapi - could be a static page, duplicate of options and root? QQQ
    path('wcapi/help/', UniversalCRUDView.as_view(), name='core/help.html'),
    
    # list/read records
    path('wcapi/keywords/', UniversalCRUDView.as_view(), name='keywords'),


    # do not know
    path('wcapi/manage/', UniversalCRUDView.as_view(), name='manage'),
    
    # options, supports CORS preflight, method to get allowed methods, meta info
    path('wcapi/options/', UniversalCRUDView.as_view(), name='options'),
    
    # partial update
    path('wcapi/patch/', UniversalCRUDView.as_view(), name='patch'),
    
    # create or full update
    path('wcapi/post/', UniversalCRUDView.as_view(), name='post'),
    
    path('wcapi/query/', UniversalCRUDView.as_view(), name='query'),

    # full update
    path('wcapi/save/', UniversalCRUDView.as_view(), name='save'),
 
    path('wcapi/put/', UniversalCRUDView.as_view(), name='put'),
    # save was used in 4D, replace with post/put
    # path('wcapi/save/', UniversalSaveView.as_view(), name='save'),
    # Root endpoint for wcapi
    # Diagnostic endpoint for tracing
    path('wcapi/trace/', UniversalCRUDView.as_view(), name='trace'),
]
