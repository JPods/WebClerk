# Core app URLs - cleaned up to keep only essential endpoints
from django.urls import path
from apps.core.views.cookie_token_refresh import CookieTokenRefreshView
from apps.core.token_views import RoleTokenObtainPairView

from apps.core.views.save_view import SaveWcapiView, SaveWcapiViewWithModel
from apps.core.views.auth_views import AuthLoginView, AuthLogoutView, AuthMeView, AuthRegisterView
from apps.core.views.wcapi import WCAPIGetView, WCAPIGetViewWithModel, WCAPIDeleteView, ModelNameListView, ModelDetailView
from apps.core.views.manage_view import ManageWcapiView
from apps.core.views.choices import ChoiceCatalogView
from apps.core.views.system_info import SystemInfoView
from apps.core.views.dev_tools import dev_config_status, dev_switch_mode, dev_restart_servers, dev_sync_status, dev_sync_data
from apps.core.views.refs_mismatch_view import RefsMismatchView
from apps.transactions.views.wcapi import WCAPITransactionSaveView
from apps.docs.views_qa import ApplyQuestionsView, ListQuestionGroupsView, ParentQAView

urlpatterns = [
    # Auth API
    path("wcapi/register/", AuthRegisterView.as_view(), name="api-auth-register"),
    path("wcapi/signup/", AuthRegisterView.as_view(), name="api-auth-signup"),
    path("wcapi/login/", AuthLoginView.as_view(), name="api-auth-login"),
    path("wcapi/logout/", AuthLogoutView.as_view(), name="api-auth-logout"),
    path("wcapi/me/", AuthMeView.as_view(), name="api-auth-me"),
    # Standard JWT endpoints (optional but useful)
    path("wcapi/token/", RoleTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("wcapi/token_refresh/", CookieTokenRefreshView.as_view(), name="token_refresh"),
    # Core WCAPI endpoints
    path("wcapi/get/", WCAPIGetView.as_view(), name="wcapi-get"),
    path("wcapi/get/<str:model_name>/", WCAPIGetViewWithModel.as_view(), name="wcapi-get-with-model"),
    path("wcapi/<str:model_name>/get/", WCAPIGetViewWithModel.as_view(), name="wcapi-model-get"),
    path("wcapi/save/", SaveWcapiView.as_view(), name="wcapi-save"),
    path("wcapi/save/<str:model_name>/", SaveWcapiViewWithModel.as_view(), name="wcapi-save-with-model"),
    path("wcapi/transaction/save/", WCAPITransactionSaveView.as_view(), name="wcapi-transaction-save"),
    path("wcapi/<str:model_name>/save/", SaveWcapiViewWithModel.as_view(), name="wcapi-model-save"),
    path("wcapi/delete/", WCAPIDeleteView.as_view(), name="wcapi-delete"),
    path("wcapi/manage/", ManageWcapiView.as_view(), name="wcapi-manage"),
    path("wcapi/model_name/list/", ModelNameListView.as_view(), name="model-name-list"),
    path("wcapi/model_name/detail/", ModelDetailView.as_view(), name="model-detail"),
    path("wcapi/choices/", ChoiceCatalogView.as_view(), name="wcapi-choice-catalog"),
    path("wcapi/system-info/", SystemInfoView.as_view(), name="system-info"),
    # QA endpoints
    path("wcapi/qa/apply/", ApplyQuestionsView.as_view(), name="wcapi-qa-apply"),
    path("wcapi/qa/groups/", ListQuestionGroupsView.as_view(), name="wcapi-qa-groups"),
    path("wcapi/qa/<str:parent_model>/<int:parent_id>/", ParentQAView.as_view(), name="wcapi-qa-parent"),
    # Dev tools endpoints (development only)
    path("wcapi/dev/config/", dev_config_status, name="dev-config"),
    path("wcapi/dev/sync-status/", dev_sync_status, name="dev-sync-status"),
    path("wcapi/dev/switch/", dev_switch_mode, name="dev-switch"),
    path("wcapi/dev/sync/", dev_sync_data, name="dev-sync"),
    path("wcapi/dev/restart/", dev_restart_servers, name="dev-restart"),
    # Refs mismatch audit
    path("wcapi/refs-mismatch/", RefsMismatchView.as_view(), name="refs-mismatch"),
]
