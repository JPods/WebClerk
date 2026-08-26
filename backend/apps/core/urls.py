# Core app URLs
# Convention: _ prefix = system plumbing (React-to-WC3 metadata/config)
#             no prefix = data CRUD + auth
# See: readmes/topics/architecture/wcapi-system-endpoints.md
from django.urls import path
from apps.core.views.cookie_token_refresh import CookieTokenRefreshView
from apps.core.token_views import RoleTokenObtainPairView

from apps.core.views.save_view import SaveWcapiView, SaveWcapiViewWithModel
from apps.core.views.auth_views import AuthLoginView, AuthLogoutView, AuthMeView, AuthRegisterView
from apps.core.views.wcapi import (
    WCAPIGetView,
    WCAPIGetViewWithModel,
    WCAPIDeleteView,
    ModelNameListView,
    ModelDetailView,
    SearchPresetListView,
)
from apps.core.views.range_query_view import RangeQueryView
from apps.core.views.save_search_view import SaveSearchView
from apps.core.views.manage_view import ManageWcapiView
from apps.core.views.report_view import ReportDownloadView
from apps.core.views.report_fields_view import ReportFieldsView
from apps.core.views.burndown_view import BurndownView
from apps.core.views.setting_resolve_view import SettingResolveView
from apps.core.views.choices import ChoiceCatalogView
from apps.core.views.selectlist_view import SelectListCatalogView
from apps.core.views.view_query import ViewQueryView
from apps.core.views.system_info import SystemInfoView
from apps.core.views.bootstrap_view import BootstrapView
from apps.core.views.dev_tools import dev_config_status, dev_switch_mode, dev_restart_servers, dev_sync_status, dev_sync_data
from apps.core.views.refs_mismatch_view import RefsMismatchView
from apps.core.views.permissions import UserPermissionsView, ModelPermissionsView
from apps.core.views.image_view import ImageView
from apps.core.views.template_views import ResolveTemplateView, TemplateFieldsView
from apps.core.views.sample_data_view import SampleDataView
from apps.core.views.parade_preview_view import ParadePreviewView, ParadeManifestView, ParadeFeedbackView
from apps.core.views.setting_parade_view import SettingParadeManifestView, SettingParadePreviewView, SettingParadeFeedbackView
from apps.core.views.system_dispatch import SystemDispatchView
from apps.transactions.views.wcapi import WCAPITransactionSaveView
from apps.docs.views_qa import ApplyQuestionsView, ListQuestionGroupsView, ParentQAView

urlpatterns = [
    # ── Auth (no prefix — user-facing) ─────────────────────────────
    path("wcapi/register/", AuthRegisterView.as_view(), name="api-auth-register"),
    path("wcapi/signup/", AuthRegisterView.as_view(), name="api-auth-signup"),
    path("wcapi/login/", AuthLoginView.as_view(), name="api-auth-login"),
    path("wcapi/logout/", AuthLogoutView.as_view(), name="api-auth-logout"),
    path("wcapi/me/", AuthMeView.as_view(), name="api-auth-me"),
    path("wcapi/token/", RoleTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("wcapi/token_refresh/", CookieTokenRefreshView.as_view(), name="token_refresh"),

    # ── Data CRUD (no prefix — business records) ───────────────────
    path("wcapi/get/", WCAPIGetView.as_view(), name="wcapi-get"),
    path("wcapi/get/<str:model_name>/", WCAPIGetViewWithModel.as_view(), name="wcapi-get-with-model"),
    path("wcapi/<str:model_name>/get/", WCAPIGetViewWithModel.as_view(), name="wcapi-model-get"),
    path("wcapi/<str:model_name>/<str:field>/<str:from_val>/<str:to_val>/", RangeQueryView.as_view(), name="wcapi-range-query"),
    path("wcapi/save/", SaveWcapiView.as_view(), name="wcapi-save"),
    path("wcapi/save/<str:model_name>/", SaveWcapiViewWithModel.as_view(), name="wcapi-save-with-model"),
    path("wcapi/transaction/save/", WCAPITransactionSaveView.as_view(), name="wcapi-transaction-save"),
    path("wcapi/<str:model_name>/save/", SaveWcapiViewWithModel.as_view(), name="wcapi-model-save"),
    path("wcapi/delete/", WCAPIDeleteView.as_view(), name="wcapi-delete"),
    path("wcapi/report/", ReportDownloadView.as_view(), name="wcapi-report"),

    # ── System plumbing (_ prefix — React-to-WC3 metadata/config) ──
    path("wcapi/_manage/", ManageWcapiView.as_view(), name="wcapi-manage"),
    path("wcapi/_report_fields/", ReportFieldsView.as_view(), name="wcapi-report-fields"),
    path("wcapi/_burndown/<int:project_id>/", BurndownView.as_view(), name="wcapi-burndown"),
    path("wcapi/_setting_resolve/", SettingResolveView.as_view(), name="wcapi-setting-resolve"),
    path("wcapi/_model_list/", ModelNameListView.as_view(), name="model-name-list"),
    path("wcapi/_model_detail/", ModelDetailView.as_view(), name="model-detail"),
    path("wcapi/_search_presets/", SearchPresetListView.as_view(), name="search-preset-list"),
    path("wcapi/_save_search/", SaveSearchView.as_view(), name="wcapi-save-search"),
    path("wcapi/_choices/", ChoiceCatalogView.as_view(), name="wcapi-choice-catalog"),
    path("wcapi/_selectlists/", SelectListCatalogView.as_view(), name="wcapi-selectlist-catalog"),
    path("wcapi/_view/", ViewQueryView.as_view(), name="wcapi-view-query"),
    path("wcapi/_bootstrap/", BootstrapView.as_view(), name="wcapi-bootstrap"),
    path("wcapi/_system_info/", SystemInfoView.as_view(), name="system-info"),
    # QA
    path("wcapi/_qa_apply/", ApplyQuestionsView.as_view(), name="wcapi-qa-apply"),
    path("wcapi/_qa_groups/", ListQuestionGroupsView.as_view(), name="wcapi-qa-groups"),
    path("wcapi/_qa/<str:parent_model>/<int:parent_id>/", ParentQAView.as_view(), name="wcapi-qa-parent"),
    # Dev tools
    path("wcapi/_dev_config/", dev_config_status, name="dev-config"),
    path("wcapi/_dev_sync_status/", dev_sync_status, name="dev-sync-status"),
    path("wcapi/_dev_switch/", dev_switch_mode, name="dev-switch"),
    path("wcapi/_dev_sync/", dev_sync_data, name="dev-sync"),
    path("wcapi/_dev_restart/", dev_restart_servers, name="dev-restart"),
    # Refs mismatch audit
    path("wcapi/_refs_mismatch/", RefsMismatchView.as_view(), name="refs-mismatch"),
    # Sample data + parade
    path("wcapi/_sample_data/", SampleDataView.as_view(), name="wcapi-sample-data"),
    path("wcapi/_parade_preview/", ParadePreviewView.as_view(), name="wcapi-parade-preview"),
    path("wcapi/_parade_manifest/", ParadeManifestView.as_view(), name="wcapi-parade-manifest"),
    path("wcapi/_parade_feedback/", ParadeFeedbackView.as_view(), name="wcapi-parade-feedback"),
    # Setting parade
    path("wcapi/_setting_parade_manifest/", SettingParadeManifestView.as_view(), name="wcapi-setting-parade-manifest"),
    path("wcapi/_setting_parade_preview/", SettingParadePreviewView.as_view(), name="wcapi-setting-parade-preview"),
    path("wcapi/_setting_parade_feedback/", SettingParadeFeedbackView.as_view(), name="wcapi-setting-parade-feedback"),
    # Template resolution
    path("wcapi/_resolve_template/", ResolveTemplateView.as_view(), name="wcapi-resolve-template"),
    path("wcapi/_template_fields/", TemplateFieldsView.as_view(), name="wcapi-template-fields"),
    # RBAC Permissions
    path("wcapi/_permissions/", UserPermissionsView.as_view(), name="wcapi-permissions"),
    path("wcapi/_permissions/<str:model_name>/", ModelPermissionsView.as_view(), name="wcapi-permissions-model"),
    # Image library
    path("wcapi/_image/<str:model_name>/<str:ida>/<str:size>", ImageView.as_view(), name="wcapi-image"),
    # System dispatcher — catch-all for _pjpv_* and future system actions
    # MUST be last so specific _ routes above take priority
    path("wcapi/_<str:action>/", SystemDispatchView.as_view(), name="wcapi-system"),
]
