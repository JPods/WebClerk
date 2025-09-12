# path: apps/core/urls.py
from django.urls import path

from apps.core.views import (
    HomeView, AboutView,
    SignupView, WebLoginView, WebLogoutView,
)
from django.views.generic import TemplateView
from apps.core.services.wcapi import WcapiView, wcapi_metrics_response


from rest_framework_simplejwt.views import (
    TokenRefreshView,
)
from apps.core.views.auth_token import LoginTokenObtainPairView
from apps.core.views.api_auth import ApiLoginView, ApiSignupView
from apps.core.views.related_view import RelatedDataView, RelatedDataAdvancedView
# from apps.core.views.utilities import FieldAccessView
from apps.core.views.utilities_view import AllowedFieldsView
from apps.core.views.save_view import SaveWcapiView
from apps.core.views.get_view import WcapiGetView
from apps.core.views.keyword import KeywordSearchView
from apps.products.views.item_variants import ItemVariantsView
# Deprecated dynamic query endpoint (replaced by registry-based wcapi) - retained commented for historical context
# from apps.core.views.query_any import QueryAnyView
from apps.core.views.model_info import ModelInfoView
from apps.core.views.model_fields import ModelFieldsView
from apps.core.views.table_registry_view import TableRegistryView
from apps.core.views.model_name_view import ModelNameListView, ModelNameDetailView
from django.views.generic import TemplateView
from apps.core.views.pending import PendingListView, PendingDetailView, PendingSearchView
from apps.core.views.action import ActionListView, ActionDetailView, ActionSearchView
from apps.core.views.setting import SettingListView, SettingDetailView, SettingSearchView
from apps.core.views.template import TemplateListView, TemplateDetailView, TemplateSearchView
from apps.core.views import auth_views, admin_view
from apps.core.views.contact_api import (
    ContactListView as ContactApiListView,
    ContactDetailView as ContactApiDetailView,
    ContactSearchView as ContactApiSearchView,
)

urlpatterns = [
    path('api/token/', LoginTokenObtainPairView.as_view(), name='token_obtain_pair'),
    # New API auth endpoints (JSON) - do not interfere with existing HTML /login/ & /signup/
    path('api/auth/login/', ApiLoginView.as_view(), name='api_auth_login'),
    path('api/auth/signup/', ApiSignupView.as_view(), name='api_auth_signup'),
    # Backwards-compatible wcapi auth aliases (some clients expect /wcapi/login/)
    path('wcapi/login/', ApiLoginView.as_view(), name='wcapi_login_alias'),
    path('wcapi/signup/', ApiSignupView.as_view(), name='wcapi_signup_alias'),
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
    # Admin Workbench (3-column model/records/editor with local JSON prefs)
    path('admin/workbench/', TemplateView.as_view(template_name='admin_workbench.html'), name='admin-workbench'),
    # Legacy/alt admin3 page from prior work (in admin/admin3.html)
    path('admin/workbench3/', admin_view.admin3_view, name='admin-workbench3'),

    #path('manager/related/', RelatedDataView.as_view(), name='manager-related'),
    # Universal API endpoints
    # Rare for sockets. We will more likely create an api app for websockets
    


    # Redundant verb-style wcapi endpoints intentionally disabled (we standardize on query/get/save)
    # path('wcapi/connect/', WcapiView.as_view(), name='connect'),  # legacy concept
    # path('wcapi/delete/', WcapiView.as_view(), name='delete'),    # use domain-specific delete if needed
    
    # list/read records
    path('wcapi/get/', WcapiGetView.as_view(), name='get'),
    # GET /wcapi/get/?model_name=contact
    # GET  /wcapi/get/?model_name=contact&id=6    
    # Headers only
    # path('wcapi/head/', WcapiView.as_view(), name='head'),  # HEAD handled implicitly
    
    # Help page for wcapi - could be a static page, duplicate of options and root? QQQ
    # path('wcapi/help/', WcapiView.as_view(), name='help'),  # doc now in README/OpenAPI
    
    # list/read records
    # path('wcapi/keywords/', WcapiView.as_view(), name='keywords'),  # superseded by dedicated search endpoint


    # do not know
    # path('wcapi/manage/', WcapiView.as_view(), name='manage'),  # UI layer concern
    
    # options, supports CORS preflight, method to get allowed methods, meta info
    # path('wcapi/options/', WcapiView.as_view(), name='options'),  # OPTIONS auto handled by framework
    
    # partial update
    # path('wcapi/patch/', WcapiView.as_view(), name='patch'),  # use save + version or model-specific endpoints
    
    # create or full update
    # path('wcapi/post/', WcapiView.as_view(), name='post'),  # replaced by /wcapi/save/
    
    path('wcapi/query/', WcapiView.as_view(), name='query'),  # canonical list/filter endpoint
    # Variants adapter (items, filtered by parent and/or canonical key)
    path('wcapi/items/', ItemVariantsView.as_view(), name='wcapi-items'),
    path('wcapi/metrics/', wcapi_metrics_response, name='wcapi-metrics'),

 # full update
    path('wcapi/related/', RelatedDataView.as_view(), name='related'),
    #path('wcapi/related/advanced/', RelatedDataAdvancedView.as_view(), name='related-data-advanced'),
  
    # path('wcapi/put/', WcapiView.as_view(), name='put'),  # replaced by /wcapi/save/
    # save was used in 4D, replace with post/put
    path('wcapi/save/', SaveWcapiView.as_view(), name='wcapi_save'),
    # Legacy note removed: use model_name consistently for wcapi endpoints.
    # Root endpoint for wcapi
    # Diagnostic endpoint for tracing
    # path('wcapi/trace/', WcapiView.as_view(), name='trace'),  # replaced by logging/metrics
    
    # path('wcapi/utilities/field-access/', FieldAccessView.as_view(), name='field-access'),

    path('wcapi/utilities/allowed-fields/', AllowedFieldsView.as_view(), name='allowed-fields'),
    
    path('wcapi/keyword/', KeywordSearchView.as_view(), name='wcapi-keyword'),

    # path('wcapi/query-any/', QueryAnyView.as_view(), name='wcapi-query-any'),  # deprecated dynamic model access
    
    path('wcapi/models/', ModelInfoView.as_view(), name='wcapi-models'),
    path('api/model-fields/', ModelFieldsView.as_view(), name='api-model-fields'),
    path('wcapi/tables/', TableRegistryView.as_view(), name='wcapi-tables'),
    path('wcapi/model_name/list/', ModelNameListView.as_view(), name='model-name-list'),
    path('wcapi/model_name/detail/', ModelNameDetailView.as_view(), name='model-name-detail'),

    # Standardized Pending endpoints (List/Create, Detail with optimistic PATCH, Search)
    path('pending/', PendingListView.as_view(), name='pending-list'),
    path('pending/<int:pk>/', PendingDetailView.as_view(), name='pending-detail'),
    path('pending/search/', PendingSearchView.as_view(), name='pending-search'),

    # Standardized Action endpoints (List/Create, Detail, Search)
    path('actions/std/', ActionListView.as_view(), name='action2-list'),
    path('actions/std/<int:pk>/', ActionDetailView.as_view(), name='action2-detail'),
    path('actions/std/search/', ActionSearchView.as_view(), name='action2-search'),

    # Settings endpoints
    path('settings/', SettingListView.as_view(), name='setting-list'),
    path('settings/<int:pk>/', SettingDetailView.as_view(), name='setting-detail'),
    path('settings/search/', SettingSearchView.as_view(), name='setting-search'),

    # Templates endpoints
    path('templates/', TemplateListView.as_view(), name='template-list'),
    path('templates/<int:pk>/', TemplateDetailView.as_view(), name='template-detail'),
    path('templates/search/', TemplateSearchView.as_view(), name='template-search'),

    # Example: GET /wcapi/models/?model_name=contact&related_models=actions,phones
    # Returns info for contacts, actions, and phones.
    
        # Contacts API endpoints (standardized)
        path('contacts/', ContactApiListView.as_view(), name='contact-list'),
        path('contacts/<int:pk>/', ContactApiDetailView.as_view(), name='contact-detail'),
        path('contacts/search/', ContactApiSearchView.as_view(), name='contact-search'),
]
