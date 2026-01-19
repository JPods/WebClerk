# Core app URLs - cleaned up to keep only essential endpoints
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from apps.core.token_views import RoleTokenObtainPairView

from apps.core.views.save_view import SaveWcapiView
from apps.core.views.auth_views import AuthLoginView, AuthLogoutView, AuthMeView, AuthRegisterView
from apps.core.views.wcapi import WCAPIGetView, ModelNameListView, ModelDetailView
from apps.core.views.choices import ChoiceCatalogView
from apps.core.views.system_info import SystemInfoView
from apps.core.views.dev_tools import dev_config_status, dev_switch_mode, dev_restart_servers
from apps.transactions.views.wcapi import WCAPITransactionSaveView

urlpatterns = [
    # Auth API
    path("wcapi/register/", AuthRegisterView.as_view(), name="api-auth-register"),
    path("wcapi/signup/", AuthRegisterView.as_view(), name="api-auth-signup"),
    path("wcapi/login/", AuthLoginView.as_view(), name="api-auth-login"),
    path("wcapi/logout/", AuthLogoutView.as_view(), name="api-auth-logout"),
    path("wcapi/me/", AuthMeView.as_view(), name="api-auth-me"),
    # Standard JWT endpoints (optional but useful)
    path("wcapi/token/", RoleTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("wcapi/token_refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # Core WCAPI endpoints
    path("wcapi/get/", WCAPIGetView.as_view(), name="wcapi-get"),
    path("wcapi/save/", SaveWcapiView.as_view(), name="wcapi-save"),
    path("wcapi/transaction/save/", WCAPITransactionSaveView.as_view(), name="wcapi-transaction-save"),
    path("wcapi/model_name/list/", ModelNameListView.as_view(), name="model-name-list"),
    path("wcapi/model_name/detail/", ModelDetailView.as_view(), name="model-detail"),
    path("wcapi/choices/", ChoiceCatalogView.as_view(), name="wcapi-choice-catalog"),
    path("wcapi/system-info/", SystemInfoView.as_view(), name="system-info"),
    # Dev tools endpoints (development only)
    path("wcapi/dev/config/", dev_config_status, name="dev-config"),
    path("wcapi/dev/switch/", dev_switch_mode, name="dev-switch"),
    path("wcapi/dev/restart/", dev_restart_servers, name="dev-restart"),
]
