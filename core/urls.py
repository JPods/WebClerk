# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/core/urls.py
from django.urls import path

from core.views import (
    HomeView, AboutView,
    SignupView, WebLoginView, WebLogoutView,
)
from django.views.generic import TemplateView
from core.services.wcapi import WcapiView


from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from core.views.related_view import RelatedDataView, RelatedDataAdvancedView
# from core.views.utilities import FieldAccessView
from core.views.utilities_view import AllowedFieldsView
from core.views.save_view import SaveWcapiView
from core.views.get_view import WcapiGetView
from core.views.keyword import KeywordSearchView
from core.views.query_any import QueryAnyView
from core.views.model_info import ModelInfoView
from django.views.generic import TemplateView

urlpatterns = [
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Home and About pages
    path('', HomeView.as_view(), name='home'),
    path('about/', AboutView.as_view(), name='about'),
    
    # Authentication
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', WebLoginView.as_view(), name='login'),
    path('logout/', WebLogoutView.as_view(), name='logout'),
    
   
        # Dedicated Management Pages
    path('manage/actions/', TemplateView.as_view(template_name='manage_actions.html'), name='manage-actions'),
    path('user/', TemplateView.as_view(template_name='user.html'), name='user'),
    path('manager/', TemplateView.as_view(template_name='manager.html'), name='manager'),

    #path('manager/related/', RelatedDataView.as_view(), name='manager-related'),
    # Universal API endpoints
    # Rare for sockets. We will more likely create an api app for websockets
    


    path('wcapi/connect/', WcapiView.as_view(), name='connect'),
    # delete
    path('wcapi/delete/', WcapiView.as_view(), name='delete'),
    
    # list/read records
    path('wcapi/get/', WcapiGetView.as_view(), name='get'),
    # GET /wcapi/get/?table_name=contacts
    # GET  /wcapi/get/?table_name=contacts&id=6    
    # Headers only
    path('wcapi/head/', WcapiView.as_view(), name='head'),
    
    # Help page for wcapi - could be a static page, duplicate of options and root? QQQ
    path('wcapi/help/', WcapiView.as_view(), name='help'),
    
    # list/read records
    path('wcapi/keywords/', WcapiView.as_view(), name='keywords'),


    # do not know
    path('wcapi/manage/', WcapiView.as_view(), name='manage'),
    
    # options, supports CORS preflight, method to get allowed methods, meta info
    path('wcapi/options/', WcapiView.as_view(), name='options'),
    
    # partial update
    path('wcapi/patch/', WcapiView.as_view(), name='patch'),
    
    # create or full update
    path('wcapi/post/', WcapiView.as_view(), name='post'),
    
    path('wcapi/query/', WcapiView.as_view(), name='query'),

 # full update
    path('wcapi/related/', RelatedDataView.as_view(), name='related'),
    #path('wcapi/related/advanced/', RelatedDataAdvancedView.as_view(), name='related-data-advanced'),
  
    path('wcapi/put/', WcapiView.as_view(), name='put'),
    # save was used in 4D, replace with post/put
    path('wcapi/save/', SaveWcapiView.as_view(), name='wcapi_save'),
    # pass table_name and id wcapi/save/?table_name=<table_name>&id=<id>
    # Root endpoint for wcapi
    # Diagnostic endpoint for tracing
    path('wcapi/trace/', WcapiView.as_view(), name='trace'),
    
    # path('wcapi/utilities/field-access/', FieldAccessView.as_view(), name='field-access'),

    path('wcapi/utilities/allowed-fields/', AllowedFieldsView.as_view(), name='allowed-fields'),
    
    path('wcapi/keyword/', KeywordSearchView.as_view(), name='wcapi-keyword'),

    path('wcapi/query-any/', QueryAnyView.as_view(), name='wcapi-query-any'),
    
    path('wcapi/models/', ModelInfoView.as_view(), name='wcapi-models'),

    # GET /wcapi/models/?table_name=contacts&related_tables=actions,phones
    # Returns info for contacts, actions, and phones.
]
