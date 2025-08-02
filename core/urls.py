# 
# PURPOSE: URL routing for Universal API endpoints and standard Django views
# UNIVERSAL API: Routes /WCapi/ URLs to universal views that handle any table
# REPLACES: Individual URL patterns for each table management interface
# TEAM NOTE: These patterns enable Universal API to work with any table name dynamically
# ARCHITECTURE: Implements 4D-style universal table access via URLs
# URL PATTERNS:
#   - /WCapi/<table_name>/manage/ -> Universal management interface
#   - /WCapi/query/ -> Universal query endpoint
#   - /WCapi/save/ -> Universal save endpoint
#   - /WCapi/get/ -> Universal get endpoint
#   - /WCapi/delete/ -> Universal delete endpoint
#   - /WCapi/clone/ -> Universal clone endpoint
# SECURITY: All Universal API endpoints require authentication
# TABLES: Works with any table registered in UniversalCRUDView.TABLE_REGISTRY

from django.urls import path
from django.contrib.auth import views as auth_views
from .views import generic_views

urlpatterns = [
    # Authentication URLs - Essential for Universal API security
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Universal API Endpoints - Core of the 4D-style system
    path('<str:table_name>/manage/', generic_views.UniversalCRUDView.as_view(), name='universal_manage'),
    path('query/', generic_views.UniversalQueryView.as_view(), name='universal_query'),
    path('save/', generic_views.UniversalSaveView.as_view(), name='universal_save'),
    path('get/', generic_views.UniversalGetView.as_view(), name='universal_get'),
    path('delete/', generic_views.UniversalDeleteView.as_view(), name='universal_delete'),
    path('clone/', generic_views.UniversalCloneView.as_view(), name='universal_clone'),
]