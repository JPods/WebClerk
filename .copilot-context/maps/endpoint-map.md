# API Endpoint Map

> Auto-generated from Django URL configuration.
> Generated: 2026-02-22 13:25

---

| URL Pattern | Method | View | Name |
|-------------|--------|------|------|
| `/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | root |
| `/wcapi/schema/` | GET | `drf_spectacular.views.SpectacularAPIView` | schema |
| `/wcapi/swagger/` | GET | `drf_spectacular.views.SpectacularSwaggerView` | swagger-ui |
| `/wcapi/redoc/` | GET | `drf_spectacular.views.SpectacularRedocView` | redoc |
| `/wcapi/upload/` | POST | `apps.docs.views_upload.DocumentUploadView` | document-upload |
| `/wcapi/document/<int:document_id>/` | GET | `apps.docs.views_upload.DocumentDownloadView` | document-download |
| `/wcapi/document/<int:document_id>/delete/` | DELETE | `apps.docs.views_upload.DocumentDeleteView` | document-delete |
| `/wcapi/register/` | POST | `apps.core.views.auth_views.AuthRegisterView` | api-auth-register |
| `/wcapi/signup/` | POST | `apps.core.views.auth_views.AuthRegisterView` | api-auth-signup |
| `/wcapi/login/` | POST | `apps.core.views.auth_views.AuthLoginView` | api-auth-login |
| `/wcapi/logout/` | POST | `apps.core.views.auth_views.AuthLogoutView` | api-auth-logout |
| `/wcapi/me/` | GET | `apps.core.views.auth_views.AuthMeView` | api-auth-me |
| `/wcapi/token/` | POST | `apps.core.token_views.RoleTokenObtainPairView` | token_obtain_pair |
| `/wcapi/token_refresh/` | POST | `apps.core.views.cookie_token_refresh.CookieTokenRefreshView` | token_refresh |
| `/wcapi/get/` | GET | `apps.core.views.wcapi.WCAPIGetView` | wcapi-get |
| `/wcapi/get/<str:model_name>/` | GET | `apps.core.views.wcapi.WCAPIGetViewWithModel` | wcapi-get-with-model |
| `/wcapi/<str:model_name>/get/` | GET | `apps.core.views.wcapi.WCAPIGetViewWithModel` | wcapi-model-get |
| `/wcapi/save/` | POST | `apps.core.views.save_view.SaveWcapiView` | wcapi-save |
| `/wcapi/save/<str:model_name>/` | POST | `apps.core.views.save_view.SaveWcapiViewWithModel` | wcapi-save-with-model |
| `/wcapi/transaction/save/` | POST | `apps.transactions.views.wcapi.WCAPITransactionSaveView` | wcapi-transaction-save |
| `/wcapi/<str:model_name>/save/` | POST | `apps.core.views.save_view.SaveWcapiViewWithModel` | wcapi-model-save |
| `/wcapi/delete/` | GET, POST | `apps.core.views.wcapi.WCAPIDeleteView` | wcapi-delete |
| `/wcapi/model_name/list/` | GET | `apps.core.views.wcapi.ModelNameListView` | model-name-list |
| `/wcapi/model_name/detail/` | GET | `apps.core.views.wcapi.ModelDetailView` | model-detail |
| `/wcapi/choices/` | GET | `apps.core.views.choices.ChoiceCatalogView` | wcapi-choice-catalog |
| `/wcapi/system-info/` | GET | `apps.core.views.system_info.SystemInfoView` | system-info |
| `/wcapi/qa/apply/` | POST | `apps.docs.views_qa.ApplyQuestionsView` | wcapi-qa-apply |
| `/wcapi/qa/groups/` | GET | `apps.docs.views_qa.ListQuestionGroupsView` | wcapi-qa-groups |
| `/wcapi/qa/<str:parent_model>/<int:parent_id>/` | GET | `apps.docs.views_qa.ParentQAView` | wcapi-qa-parent |
| `/wcapi/dev/config/` | — | `apps.core.views.dev_tools.dev_config_status` | dev-config |
| `/wcapi/dev/sync-status/` | — | `apps.core.views.dev_tools.dev_sync_status` | dev-sync-status |
| `/wcapi/dev/switch/` | — | `apps.core.views.dev_tools.dev_switch_mode` | dev-switch |
| `/wcapi/dev/sync/` | — | `apps.core.views.dev_tools.dev_sync_data` | dev-sync |
| `/wcapi/dev/restart/` | — | `apps.core.views.dev_tools.dev_restart_servers` | dev-restart |
| `/wcapi/refs-mismatch/` | GET, POST | `apps.core.views.refs_mismatch_view.RefsMismatchView` | refs-mismatch |
| `/wcapi/ai/ask/` | POST | `apps.ai_assistant.views.AskView` | ai-ask |
| `/wcapi/ai/feedback/` | POST | `apps.ai_assistant.views.FeedbackView` | ai-feedback |
| `/wcapi/ai/health/` | GET | `apps.ai_assistant.views.HealthView` | ai-health |
| `/wcapi/ai/history/` | GET | `apps.ai_assistant.views.HistoryView` | ai-history |
| `/wcapi/ai/modes/` | GET | `apps.ai_assistant.views.ModesView` | ai-modes |
| `/wcapi/ai/debug/` | POST | `apps.ai_assistant.views.DebugView` | ai-debug |
| `/wcapi/ai/review/` | POST | `apps.ai_assistant.views.ReviewView` | ai-review |
| `/wcapi/ai/generate/` | POST | `apps.ai_assistant.views.GenerateView` | ai-generate |
| `/wcapi/ai/reindex/` | POST | `apps.ai_assistant.views.ReindexView` | ai-reindex |
| `/api/orgs/^orgs/$` | — | `apps.orgs.views.customer_viewset.OrgBaseViewSet` | org-list |
| `/api/orgs/^orgs\.(?P<format>[a-z0-9]+)/?$` | — | `apps.orgs.views.customer_viewset.OrgBaseViewSet` | org-list |
| `/api/orgs/^orgs/(?P<pk>[^/.]+)/$` | — | `apps.orgs.views.customer_viewset.OrgBaseViewSet` | org-detail |
| `/api/orgs/^orgs/(?P<pk>[^/.]+)\.(?P<format>[a-z0-9]+)/?$` | — | `apps.orgs.views.customer_viewset.OrgBaseViewSet` | org-detail |
| `/api/orgs/^customers/$` | — | `apps.orgs.views.customer_viewset.CustomerViewSet` | customer-list |
| `/api/orgs/^customers\.(?P<format>[a-z0-9]+)/?$` | — | `apps.orgs.views.customer_viewset.CustomerViewSet` | customer-list |
| `/api/orgs/^customers/(?P<pk>[^/.]+)/$` | — | `apps.orgs.views.customer_viewset.CustomerViewSet` | customer-detail |
| `/api/orgs/^customers/(?P<pk>[^/.]+)\.(?P<format>[a-z0-9]+)/?$` | — | `apps.orgs.views.customer_viewset.CustomerViewSet` | customer-detail |
| `/api/orgs/^vendors/$` | — | `apps.orgs.views.customer_viewset.VendorViewSet` | vendor-list |
| `/api/orgs/^vendors\.(?P<format>[a-z0-9]+)/?$` | — | `apps.orgs.views.customer_viewset.VendorViewSet` | vendor-list |
| `/api/orgs/^vendors/(?P<pk>[^/.]+)/$` | — | `apps.orgs.views.customer_viewset.VendorViewSet` | vendor-detail |
| `/api/orgs/^vendors/(?P<pk>[^/.]+)\.(?P<format>[a-z0-9]+)/?$` | — | `apps.orgs.views.customer_viewset.VendorViewSet` | vendor-detail |
| `/api/orgs/^reps/$` | — | `apps.orgs.views.customer_viewset.RepViewSet` | rep-list |
| `/api/orgs/^reps\.(?P<format>[a-z0-9]+)/?$` | — | `apps.orgs.views.customer_viewset.RepViewSet` | rep-list |
| `/api/orgs/^reps/(?P<pk>[^/.]+)/$` | — | `apps.orgs.views.customer_viewset.RepViewSet` | rep-detail |
| `/api/orgs/^reps/(?P<pk>[^/.]+)\.(?P<format>[a-z0-9]+)/?$` | — | `apps.orgs.views.customer_viewset.RepViewSet` | rep-detail |
| `/api/orgs/^employees/$` | — | `apps.orgs.views.customer_viewset.EmployeeViewSet` | employee-list |
| `/api/orgs/^employees\.(?P<format>[a-z0-9]+)/?$` | — | `apps.orgs.views.customer_viewset.EmployeeViewSet` | employee-list |
| `/api/orgs/^employees/(?P<pk>[^/.]+)/$` | — | `apps.orgs.views.customer_viewset.EmployeeViewSet` | employee-detail |
| `/api/orgs/^employees/(?P<pk>[^/.]+)\.(?P<format>[a-z0-9]+)/?$` | — | `apps.orgs.views.customer_viewset.EmployeeViewSet` | employee-detail |
| `/api/orgs/^manufacturers/$` | — | `apps.orgs.views.customer_viewset.ManufacturerViewSet` | manufacturer-list |
| `/api/orgs/^manufacturers\.(?P<format>[a-z0-9]+)/?$` | — | `apps.orgs.views.customer_viewset.ManufacturerViewSet` | manufacturer-list |
| `/api/orgs/^manufacturers/(?P<pk>[^/.]+)/$` | — | `apps.orgs.views.customer_viewset.ManufacturerViewSet` | manufacturer-detail |
| `/api/orgs/^manufacturers/(?P<pk>[^/.]+)\.(?P<format>[a-z0-9]+)/?$` | — | `apps.orgs.views.customer_viewset.ManufacturerViewSet` | manufacturer-detail |
| `/api/orgs/` | GET | `rest_framework.routers.APIRootView` | api-root |
| `/api/orgs/<drf_format_suffix:format>` | GET | `rest_framework.routers.APIRootView` | api-root |
| `/api/docs/stats/` | GET | `apps.docs.views_stats.DocsStatsView` | docs-stats |
| `/api/docs/qa/apply/` | POST | `apps.docs.views_qa.ApplyQuestionsView` | qa-apply |
| `/api/docs/qa/groups/` | GET | `apps.docs.views_qa.ListQuestionGroupsView` | qa-groups |
| `/api/docs/qa/<str:parent_model>/<int:parent_id>/` | GET | `apps.docs.views_qa.ParentQAView` | qa-parent |
| `/api/transactions/^proposals/$` | — | `apps.transactions.views.transaction_views.ProposalViewSet` | proposal-list |
| `/api/transactions/^proposals\.(?P<format>[a-z0-9]+)/?$` | — | `apps.transactions.views.transaction_views.ProposalViewSet` | proposal-list |
| `/api/transactions/^proposals/(?P<pk>[^/.]+)/$` | — | `apps.transactions.views.transaction_views.ProposalViewSet` | proposal-detail |
| `/api/transactions/^proposals/(?P<pk>[^/.]+)\.(?P<format>[a-z0-9]+)/?$` | — | `apps.transactions.views.transaction_views.ProposalViewSet` | proposal-detail |
| `/api/transactions/^proposals/(?P<pk>[^/.]+)/convert_to_order/$` | — | `apps.transactions.views.transaction_views.ProposalViewSet` | proposal-convert-to-order |
| `/api/transactions/^proposals/(?P<pk>[^/.]+)/convert_to_order\.(?P<format>[a-z0-9]+)/?$` | — | `apps.transactions.views.transaction_views.ProposalViewSet` | proposal-convert-to-order |
| `/api/transactions/^orders/$` | — | `apps.transactions.views.transaction_views.OrderViewSet` | order-list |
| `/api/transactions/^orders\.(?P<format>[a-z0-9]+)/?$` | — | `apps.transactions.views.transaction_views.OrderViewSet` | order-list |
| `/api/transactions/^orders/(?P<pk>[^/.]+)/$` | — | `apps.transactions.views.transaction_views.OrderViewSet` | order-detail |
| `/api/transactions/^orders/(?P<pk>[^/.]+)\.(?P<format>[a-z0-9]+)/?$` | — | `apps.transactions.views.transaction_views.OrderViewSet` | order-detail |
| `/api/transactions/^orders/(?P<pk>[^/.]+)/convert_to_invoice/$` | — | `apps.transactions.views.transaction_views.OrderViewSet` | order-convert-to-invoice |
| `/api/transactions/^orders/(?P<pk>[^/.]+)/convert_to_invoice\.(?P<format>[a-z0-9]+)/?$` | — | `apps.transactions.views.transaction_views.OrderViewSet` | order-convert-to-invoice |
| `/api/transactions/^orders/(?P<pk>[^/.]+)/create_purchase/$` | — | `apps.transactions.views.transaction_views.OrderViewSet` | order-create-purchase |
| `/api/transactions/^orders/(?P<pk>[^/.]+)/create_purchase\.(?P<format>[a-z0-9]+)/?$` | — | `apps.transactions.views.transaction_views.OrderViewSet` | order-create-purchase |
| `/api/transactions/^orders/(?P<pk>[^/.]+)/reserve_inventory/$` | — | `apps.transactions.views.transaction_views.OrderViewSet` | order-reserve-inventory |
| `/api/transactions/^orders/(?P<pk>[^/.]+)/reserve_inventory\.(?P<format>[a-z0-9]+)/?$` | — | `apps.transactions.views.transaction_views.OrderViewSet` | order-reserve-inventory |
| `/api/transactions/^purchases/$` | — | `apps.transactions.views.transaction_views.PurchaseViewSet` | purchase-list |
| `/api/transactions/^purchases\.(?P<format>[a-z0-9]+)/?$` | — | `apps.transactions.views.transaction_views.PurchaseViewSet` | purchase-list |
| `/api/transactions/^purchases/(?P<pk>[^/.]+)/$` | — | `apps.transactions.views.transaction_views.PurchaseViewSet` | purchase-detail |
| `/api/transactions/^purchases/(?P<pk>[^/.]+)\.(?P<format>[a-z0-9]+)/?$` | — | `apps.transactions.views.transaction_views.PurchaseViewSet` | purchase-detail |
| `/api/transactions/^purchases/(?P<pk>[^/.]+)/receive_goods/$` | — | `apps.transactions.views.transaction_views.PurchaseViewSet` | purchase-receive-goods |
| `/api/transactions/^purchases/(?P<pk>[^/.]+)/receive_goods\.(?P<format>[a-z0-9]+)/?$` | — | `apps.transactions.views.transaction_views.PurchaseViewSet` | purchase-receive-goods |
| `/api/transactions/^purchases/(?P<pk>[^/.]+)/totals/$` | — | `apps.transactions.views.transaction_views.PurchaseViewSet` | purchase-totals |
| `/api/transactions/^purchases/(?P<pk>[^/.]+)/totals\.(?P<format>[a-z0-9]+)/?$` | — | `apps.transactions.views.transaction_views.PurchaseViewSet` | purchase-totals |
| `/api/transactions/^invoices/$` | — | `apps.transactions.views.transaction_views.InvoiceViewSet` | invoice-list |
| `/api/transactions/^invoices\.(?P<format>[a-z0-9]+)/?$` | — | `apps.transactions.views.transaction_views.InvoiceViewSet` | invoice-list |
| `/api/transactions/^invoices/(?P<pk>[^/.]+)/$` | — | `apps.transactions.views.transaction_views.InvoiceViewSet` | invoice-detail |
| `/api/transactions/^invoices/(?P<pk>[^/.]+)\.(?P<format>[a-z0-9]+)/?$` | — | `apps.transactions.views.transaction_views.InvoiceViewSet` | invoice-detail |
| `/api/transactions/^invoices/(?P<pk>[^/.]+)/payment_status/$` | — | `apps.transactions.views.transaction_views.InvoiceViewSet` | invoice-payment-status |
| `/api/transactions/^invoices/(?P<pk>[^/.]+)/payment_status\.(?P<format>[a-z0-9]+)/?$` | — | `apps.transactions.views.transaction_views.InvoiceViewSet` | invoice-payment-status |
| `/api/transactions/^payments/$` | — | `apps.transactions.views.transaction_views.PaymentViewSet` | payment-list |
| `/api/transactions/^payments\.(?P<format>[a-z0-9]+)/?$` | — | `apps.transactions.views.transaction_views.PaymentViewSet` | payment-list |
| `/api/transactions/^payments/(?P<pk>[^/.]+)/$` | — | `apps.transactions.views.transaction_views.PaymentViewSet` | payment-detail |
| `/api/transactions/^payments/(?P<pk>[^/.]+)\.(?P<format>[a-z0-9]+)/?$` | — | `apps.transactions.views.transaction_views.PaymentViewSet` | payment-detail |
| `/api/transactions/` | GET | `rest_framework.routers.APIRootView` | api-root |
| `/api/transactions/<drf_format_suffix:format>` | GET | `rest_framework.routers.APIRootView` | api-root |
| `/api/transactions/proposals/<int:pk>/convert-to-order/` | — | `apps.transactions.views.transaction_views.ProposalViewSet` | proposal-convert-to-order |
| `/api/transactions/orders/<int:pk>/convert-to-invoice/` | — | `apps.transactions.views.transaction_views.OrderViewSet` | order-convert-to-invoice |
| `/api/transactions/orders/<int:pk>/convert-to-purchase/` | POST | `apps.transactions.views.order_views.OrderToPurchaseView` | order-convert-to-purchase |
| `/api/transactions/transfers/validate/` | POST | `apps.transactions.views.transfer_views.validate_transfer` | validate_transfer |
| `/api/transactions/transfers/execute/` | POST | `apps.transactions.views.transfer_views.execute_transfer` | execute_transfer |
| `/api/transactions/transfers/bulk/proposals-to-orders/` | POST | `apps.transactions.views.transfer_views.bulk_transfer_proposals` | bulk_transfer_proposals |
| `/api/transactions/transfers/bulk/orders-to-invoices/` | POST | `apps.transactions.views.transfer_views.bulk_transfer_orders` | bulk_transfer_orders |
| `/api/transactions/payments/process/` | POST | `apps.transactions.views.payment_views.process_payment` | process_payment |
| `/api/transactions/payments/paypal/execute/` | POST | `apps.transactions.views.payment_views.execute_paypal_payment` | execute_paypal_payment |
| `/api/transactions/payments/apply/` | POST | `apps.transactions.views.transfer_views.apply_payment` | apply_payment |
| `/api/transactions/payments/webhooks/stripe/` | — | `apps.transactions.views.payment_views.stripe_webhook` | stripe_webhook |
| `/api/transactions/payments/webhooks/paypal/` | — | `apps.transactions.views.payment_views.paypal_webhook` | paypal_webhook |
| `/api/transactions/payments/reconcile/` | POST | `apps.transactions.views.payment_views.reconcile_payments` | reconcile_payments |
| `/api/transactions/payments/<int:payment_id>/status/` | GET | `apps.transactions.views.payment_views.payment_status` | payment_status |
| `/api/transactions/payments/history/` | GET | `apps.transactions.views.payment_views.payment_history` | payment_history |
| `/api/transactions/inventory/reserve/` | POST | `apps.transactions.views.transfer_views.reserve_inventory` | reserve_inventory |
| `/api/transactions/inventory/release/<int:invoice_id>/` | POST | `apps.transactions.views.transfer_views.release_inventory` | release_inventory |
| `/api/products/items/<int:parent_id>/bom/` | GET, POST | `apps.products.views.bom_views.BOMListCreateView` | bom-list-create |
| `/api/products/items/<int:parent_id>/bom/recalc-cost/` | POST | `apps.products.views.bom_views.BOMRecalcCostView` | bom-recalc-cost |
| `/api/products/bom/<int:pk>/` | GET, PATCH, DELETE | `apps.products.views.bom_views.BOMDetailView` | bom-detail |
| `/admin/swagger/` | GET | `drf_spectacular.views.SpectacularSwaggerView` | admin-swagger |
| `/admin/threepane/` | — | `apps.core.admin._threepane_view` | threepane |
| `/admin/threepane/<str:app_label>/<str:model_name>/list/` | — | `apps.core.admin._threepane_model_list` | threepane_model_list |
| `/admin/threepane/<str:app_label>/<str:model_name>/<str:object_id>/` | — | `apps.core.admin._threepane_model_detail` | threepane_model_detail |
| `/admin/` | — | `apps.core.admin._threepane_redirect` | index |
| `/admin/login/` | — | `django.contrib.admin.sites.login` | login |
| `/admin/logout/` | — | `django.contrib.admin.sites.logout` | logout |
| `/admin/password_change/` | — | `django.contrib.admin.sites.password_change` | password_change |
| `/admin/password_change/done/` | — | `django.contrib.admin.sites.password_change_done` | password_change_done |
| `/admin/autocomplete/` | — | `django.contrib.admin.sites.autocomplete_view` | autocomplete |
| `/admin/jsi18n/` | — | `django.contrib.admin.sites.i18n_javascript` | jsi18n |
| `/admin/r/<path:content_type_id>/<path:object_id>/` | — | `django.contrib.contenttypes.views.shortcut` | view_on_site |
| `/admin/accounts/glaccount/` | — | `django.contrib.admin.options.changelist_view` | accounts_glaccount_changelist |
| `/admin/accounts/glaccount/add/` | — | `django.contrib.admin.options.add_view` | accounts_glaccount_add |
| `/admin/accounts/glaccount/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | accounts_glaccount_history |
| `/admin/accounts/glaccount/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | accounts_glaccount_delete |
| `/admin/accounts/glaccount/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | accounts_glaccount_change |
| `/admin/accounts/glaccount/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/accounts/currency/` | — | `django.contrib.admin.options.changelist_view` | accounts_currency_changelist |
| `/admin/accounts/currency/add/` | — | `django.contrib.admin.options.add_view` | accounts_currency_add |
| `/admin/accounts/currency/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | accounts_currency_history |
| `/admin/accounts/currency/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | accounts_currency_delete |
| `/admin/accounts/currency/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | accounts_currency_change |
| `/admin/accounts/currency/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/accounts/exchangerate/` | — | `django.contrib.admin.options.changelist_view` | accounts_exchangerate_changelist |
| `/admin/accounts/exchangerate/add/` | — | `django.contrib.admin.options.add_view` | accounts_exchangerate_add |
| `/admin/accounts/exchangerate/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | accounts_exchangerate_history |
| `/admin/accounts/exchangerate/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | accounts_exchangerate_delete |
| `/admin/accounts/exchangerate/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | accounts_exchangerate_change |
| `/admin/accounts/exchangerate/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/accounts/exchangetransaction/` | — | `django.contrib.admin.options.changelist_view` | accounts_exchangetransaction_changelist |
| `/admin/accounts/exchangetransaction/add/` | — | `django.contrib.admin.options.add_view` | accounts_exchangetransaction_add |
| `/admin/accounts/exchangetransaction/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | accounts_exchangetransaction_history |
| `/admin/accounts/exchangetransaction/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | accounts_exchangetransaction_delete |
| `/admin/accounts/exchangetransaction/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | accounts_exchangetransaction_change |
| `/admin/accounts/exchangetransaction/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/accounts/term/` | — | `django.contrib.admin.options.changelist_view` | accounts_term_changelist |
| `/admin/accounts/term/add/` | — | `django.contrib.admin.options.add_view` | accounts_term_add |
| `/admin/accounts/term/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | accounts_term_history |
| `/admin/accounts/term/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | accounts_term_delete |
| `/admin/accounts/term/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | accounts_term_change |
| `/admin/accounts/term/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/accounts/ledger/` | — | `django.contrib.admin.options.changelist_view` | accounts_ledger_changelist |
| `/admin/accounts/ledger/add/` | — | `django.contrib.admin.options.add_view` | accounts_ledger_add |
| `/admin/accounts/ledger/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | accounts_ledger_history |
| `/admin/accounts/ledger/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | accounts_ledger_delete |
| `/admin/accounts/ledger/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | accounts_ledger_change |
| `/admin/accounts/ledger/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/accounts/taxjurisdiction/` | — | `django.contrib.admin.options.changelist_view` | accounts_taxjurisdiction_changelist |
| `/admin/accounts/taxjurisdiction/add/` | — | `django.contrib.admin.options.add_view` | accounts_taxjurisdiction_add |
| `/admin/accounts/taxjurisdiction/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | accounts_taxjurisdiction_history |
| `/admin/accounts/taxjurisdiction/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | accounts_taxjurisdiction_delete |
| `/admin/accounts/taxjurisdiction/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | accounts_taxjurisdiction_change |
| `/admin/accounts/taxjurisdiction/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/accounts/gljournal/` | — | `django.contrib.admin.options.changelist_view` | accounts_gljournal_changelist |
| `/admin/accounts/gljournal/add/` | — | `django.contrib.admin.options.add_view` | accounts_gljournal_add |
| `/admin/accounts/gljournal/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | accounts_gljournal_history |
| `/admin/accounts/gljournal/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | accounts_gljournal_delete |
| `/admin/accounts/gljournal/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | accounts_gljournal_change |
| `/admin/accounts/gljournal/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/accounts/audit/` | — | `django.contrib.admin.options.changelist_view` | accounts_audit_changelist |
| `/admin/accounts/audit/add/` | — | `django.contrib.admin.options.add_view` | accounts_audit_add |
| `/admin/accounts/audit/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | accounts_audit_history |
| `/admin/accounts/audit/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | accounts_audit_delete |
| `/admin/accounts/audit/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | accounts_audit_change |
| `/admin/accounts/audit/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/ai_assistant/conversation/` | — | `django.contrib.admin.options.changelist_view` | ai_assistant_conversation_changelist |
| `/admin/ai_assistant/conversation/add/` | — | `django.contrib.admin.options.add_view` | ai_assistant_conversation_add |
| `/admin/ai_assistant/conversation/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | ai_assistant_conversation_history |
| `/admin/ai_assistant/conversation/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | ai_assistant_conversation_delete |
| `/admin/ai_assistant/conversation/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | ai_assistant_conversation_change |
| `/admin/ai_assistant/conversation/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/ai_assistant/message/` | — | `django.contrib.admin.options.changelist_view` | ai_assistant_message_changelist |
| `/admin/ai_assistant/message/add/` | — | `django.contrib.admin.options.add_view` | ai_assistant_message_add |
| `/admin/ai_assistant/message/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | ai_assistant_message_history |
| `/admin/ai_assistant/message/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | ai_assistant_message_delete |
| `/admin/ai_assistant/message/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | ai_assistant_message_change |
| `/admin/ai_assistant/message/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/communications/address/` | — | `django.contrib.admin.options.changelist_view` | communications_address_changelist |
| `/admin/communications/address/add/` | — | `django.contrib.admin.options.add_view` | communications_address_add |
| `/admin/communications/address/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | communications_address_history |
| `/admin/communications/address/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | communications_address_delete |
| `/admin/communications/address/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | communications_address_change |
| `/admin/communications/address/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/communications/email/` | — | `django.contrib.admin.options.changelist_view` | communications_email_changelist |
| `/admin/communications/email/add/` | — | `django.contrib.admin.options.add_view` | communications_email_add |
| `/admin/communications/email/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | communications_email_history |
| `/admin/communications/email/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | communications_email_delete |
| `/admin/communications/email/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | communications_email_change |
| `/admin/communications/email/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/communications/phone/` | — | `django.contrib.admin.options.changelist_view` | communications_phone_changelist |
| `/admin/communications/phone/add/` | — | `django.contrib.admin.options.add_view` | communications_phone_add |
| `/admin/communications/phone/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | communications_phone_history |
| `/admin/communications/phone/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | communications_phone_delete |
| `/admin/communications/phone/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | communications_phone_change |
| `/admin/communications/phone/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/communications/domain/` | — | `django.contrib.admin.options.changelist_view` | communications_domain_changelist |
| `/admin/communications/domain/add/` | — | `django.contrib.admin.options.add_view` | communications_domain_add |
| `/admin/communications/domain/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | communications_domain_history |
| `/admin/communications/domain/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | communications_domain_delete |
| `/admin/communications/domain/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | communications_domain_change |
| `/admin/communications/domain/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/auth/group/` | — | `django.contrib.admin.options.changelist_view` | auth_group_changelist |
| `/admin/auth/group/add/` | — | `django.contrib.admin.options.add_view` | auth_group_add |
| `/admin/auth/group/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | auth_group_history |
| `/admin/auth/group/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | auth_group_delete |
| `/admin/auth/group/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | auth_group_change |
| `/admin/auth/group/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/core/contact/<id>/password/` | — | `django.contrib.auth.admin.user_change_password` | auth_user_password_change |
| `/admin/core/contact/` | — | `django.contrib.admin.options.changelist_view` | core_contact_changelist |
| `/admin/core/contact/add/` | — | `django.contrib.auth.admin.add_view` | core_contact_add |
| `/admin/core/contact/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | core_contact_history |
| `/admin/core/contact/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | core_contact_delete |
| `/admin/core/contact/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | core_contact_change |
| `/admin/core/contact/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/core/action/` | — | `django.contrib.admin.options.changelist_view` | core_action_changelist |
| `/admin/core/action/add/` | — | `django.contrib.admin.options.add_view` | core_action_add |
| `/admin/core/action/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | core_action_history |
| `/admin/core/action/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | core_action_delete |
| `/admin/core/action/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | core_action_change |
| `/admin/core/action/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/core/setting/` | — | `django.contrib.admin.options.changelist_view` | core_setting_changelist |
| `/admin/core/setting/add/` | — | `django.contrib.admin.options.add_view` | core_setting_add |
| `/admin/core/setting/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | core_setting_history |
| `/admin/core/setting/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | core_setting_delete |
| `/admin/core/setting/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | core_setting_change |
| `/admin/core/setting/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/core/template/` | — | `django.contrib.admin.options.changelist_view` | core_template_changelist |
| `/admin/core/template/add/` | — | `django.contrib.admin.options.add_view` | core_template_add |
| `/admin/core/template/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | core_template_history |
| `/admin/core/template/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | core_template_delete |
| `/admin/core/template/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | core_template_change |
| `/admin/core/template/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/core/pending/` | — | `django.contrib.admin.options.changelist_view` | core_pending_changelist |
| `/admin/core/pending/add/` | — | `django.contrib.admin.options.add_view` | core_pending_add |
| `/admin/core/pending/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | core_pending_history |
| `/admin/core/pending/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | core_pending_delete |
| `/admin/core/pending/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | core_pending_change |
| `/admin/core/pending/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/core/softdeleteledger/` | — | `django.contrib.admin.options.changelist_view` | core_softdeleteledger_changelist |
| `/admin/core/softdeleteledger/add/` | — | `django.contrib.admin.options.add_view` | core_softdeleteledger_add |
| `/admin/core/softdeleteledger/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | core_softdeleteledger_history |
| `/admin/core/softdeleteledger/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | core_softdeleteledger_delete |
| `/admin/core/softdeleteledger/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | core_softdeleteledger_change |
| `/admin/core/softdeleteledger/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/core/notification/` | — | `django.contrib.admin.options.changelist_view` | core_notification_changelist |
| `/admin/core/notification/add/` | — | `django.contrib.admin.options.add_view` | core_notification_add |
| `/admin/core/notification/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | core_notification_history |
| `/admin/core/notification/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | core_notification_delete |
| `/admin/core/notification/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | core_notification_change |
| `/admin/core/notification/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/core/report/` | — | `django.contrib.admin.options.changelist_view` | core_report_changelist |
| `/admin/core/report/add/` | — | `django.contrib.admin.options.add_view` | core_report_add |
| `/admin/core/report/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | core_report_history |
| `/admin/core/report/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | core_report_delete |
| `/admin/core/report/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | core_report_change |
| `/admin/core/report/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/docs/document/` | — | `django.contrib.admin.options.changelist_view` | docs_document_changelist |
| `/admin/docs/document/add/` | — | `django.contrib.admin.options.add_view` | docs_document_add |
| `/admin/docs/document/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | docs_document_history |
| `/admin/docs/document/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | docs_document_delete |
| `/admin/docs/document/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | docs_document_change |
| `/admin/docs/document/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/docs/questionanswer/` | — | `django.contrib.admin.options.changelist_view` | docs_questionanswer_changelist |
| `/admin/docs/questionanswer/add/` | — | `django.contrib.admin.options.add_view` | docs_questionanswer_add |
| `/admin/docs/questionanswer/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | docs_questionanswer_history |
| `/admin/docs/questionanswer/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | docs_questionanswer_delete |
| `/admin/docs/questionanswer/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | docs_questionanswer_change |
| `/admin/docs/questionanswer/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/docs/tag/` | — | `django.contrib.admin.options.changelist_view` | docs_tag_changelist |
| `/admin/docs/tag/add/` | — | `django.contrib.admin.options.add_view` | docs_tag_add |
| `/admin/docs/tag/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | docs_tag_history |
| `/admin/docs/tag/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | docs_tag_delete |
| `/admin/docs/tag/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | docs_tag_change |
| `/admin/docs/tag/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/docs/linkageentry/` | — | `django.contrib.admin.options.changelist_view` | docs_linkageentry_changelist |
| `/admin/docs/linkageentry/add/` | — | `django.contrib.admin.options.add_view` | docs_linkageentry_add |
| `/admin/docs/linkageentry/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | docs_linkageentry_history |
| `/admin/docs/linkageentry/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | docs_linkageentry_delete |
| `/admin/docs/linkageentry/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | docs_linkageentry_change |
| `/admin/docs/linkageentry/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/orgs/orgbase/` | — | `django.contrib.admin.options.changelist_view` | orgs_orgbase_changelist |
| `/admin/orgs/orgbase/add/` | — | `django.contrib.admin.options.add_view` | orgs_orgbase_add |
| `/admin/orgs/orgbase/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | orgs_orgbase_history |
| `/admin/orgs/orgbase/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | orgs_orgbase_delete |
| `/admin/orgs/orgbase/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | orgs_orgbase_change |
| `/admin/orgs/orgbase/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/orgs/customer/` | — | `django.contrib.admin.options.changelist_view` | orgs_customer_changelist |
| `/admin/orgs/customer/add/` | — | `django.contrib.admin.options.add_view` | orgs_customer_add |
| `/admin/orgs/customer/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | orgs_customer_history |
| `/admin/orgs/customer/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | orgs_customer_delete |
| `/admin/orgs/customer/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | orgs_customer_change |
| `/admin/orgs/customer/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/orgs/vendor/` | — | `django.contrib.admin.options.changelist_view` | orgs_vendor_changelist |
| `/admin/orgs/vendor/add/` | — | `django.contrib.admin.options.add_view` | orgs_vendor_add |
| `/admin/orgs/vendor/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | orgs_vendor_history |
| `/admin/orgs/vendor/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | orgs_vendor_delete |
| `/admin/orgs/vendor/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | orgs_vendor_change |
| `/admin/orgs/vendor/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/orgs/rep/` | — | `django.contrib.admin.options.changelist_view` | orgs_rep_changelist |
| `/admin/orgs/rep/add/` | — | `django.contrib.admin.options.add_view` | orgs_rep_add |
| `/admin/orgs/rep/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | orgs_rep_history |
| `/admin/orgs/rep/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | orgs_rep_delete |
| `/admin/orgs/rep/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | orgs_rep_change |
| `/admin/orgs/rep/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/orgs/employee/` | — | `django.contrib.admin.options.changelist_view` | orgs_employee_changelist |
| `/admin/orgs/employee/add/` | — | `django.contrib.admin.options.add_view` | orgs_employee_add |
| `/admin/orgs/employee/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | orgs_employee_history |
| `/admin/orgs/employee/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | orgs_employee_delete |
| `/admin/orgs/employee/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | orgs_employee_change |
| `/admin/orgs/employee/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/orgs/manufacturer/` | — | `django.contrib.admin.options.changelist_view` | orgs_manufacturer_changelist |
| `/admin/orgs/manufacturer/add/` | — | `django.contrib.admin.options.add_view` | orgs_manufacturer_add |
| `/admin/orgs/manufacturer/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | orgs_manufacturer_history |
| `/admin/orgs/manufacturer/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | orgs_manufacturer_delete |
| `/admin/orgs/manufacturer/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | orgs_manufacturer_change |
| `/admin/orgs/manufacturer/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/products/item/` | — | `django.contrib.admin.options.changelist_view` | products_item_changelist |
| `/admin/products/item/add/` | — | `django.contrib.admin.options.add_view` | products_item_add |
| `/admin/products/item/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | products_item_history |
| `/admin/products/item/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | products_item_delete |
| `/admin/products/item/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | products_item_change |
| `/admin/products/item/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/products/itemxref/` | — | `django.contrib.admin.options.changelist_view` | products_itemxref_changelist |
| `/admin/products/itemxref/add/` | — | `django.contrib.admin.options.add_view` | products_itemxref_add |
| `/admin/products/itemxref/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | products_itemxref_history |
| `/admin/products/itemxref/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | products_itemxref_delete |
| `/admin/products/itemxref/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | products_itemxref_change |
| `/admin/products/itemxref/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/products/billofmaterial/` | — | `django.contrib.admin.options.changelist_view` | products_billofmaterial_changelist |
| `/admin/products/billofmaterial/add/` | — | `django.contrib.admin.options.add_view` | products_billofmaterial_add |
| `/admin/products/billofmaterial/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | products_billofmaterial_history |
| `/admin/products/billofmaterial/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | products_billofmaterial_delete |
| `/admin/products/billofmaterial/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | products_billofmaterial_change |
| `/admin/products/billofmaterial/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/products/warehouse/` | — | `django.contrib.admin.options.changelist_view` | products_warehouse_changelist |
| `/admin/products/warehouse/add/` | — | `django.contrib.admin.options.add_view` | products_warehouse_add |
| `/admin/products/warehouse/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | products_warehouse_history |
| `/admin/products/warehouse/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | products_warehouse_delete |
| `/admin/products/warehouse/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | products_warehouse_change |
| `/admin/products/warehouse/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/products/inventorylayer/` | — | `django.contrib.admin.options.changelist_view` | products_inventorylayer_changelist |
| `/admin/products/inventorylayer/add/` | — | `django.contrib.admin.options.add_view` | products_inventorylayer_add |
| `/admin/products/inventorylayer/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | products_inventorylayer_history |
| `/admin/products/inventorylayer/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | products_inventorylayer_delete |
| `/admin/products/inventorylayer/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | products_inventorylayer_change |
| `/admin/products/inventorylayer/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/products/siteinventory/` | — | `django.contrib.admin.options.changelist_view` | products_siteinventory_changelist |
| `/admin/products/siteinventory/add/` | — | `django.contrib.admin.options.add_view` | products_siteinventory_add |
| `/admin/products/siteinventory/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | products_siteinventory_history |
| `/admin/products/siteinventory/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | products_siteinventory_delete |
| `/admin/products/siteinventory/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | products_siteinventory_change |
| `/admin/products/siteinventory/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/products/inventorymovement/` | — | `django.contrib.admin.options.changelist_view` | products_inventorymovement_changelist |
| `/admin/products/inventorymovement/add/` | — | `django.contrib.admin.options.add_view` | products_inventorymovement_add |
| `/admin/products/inventorymovement/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | products_inventorymovement_history |
| `/admin/products/inventorymovement/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | products_inventorymovement_delete |
| `/admin/products/inventorymovement/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | products_inventorymovement_change |
| `/admin/products/inventorymovement/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/products/orgitem/` | — | `django.contrib.admin.options.changelist_view` | products_orgitem_changelist |
| `/admin/products/orgitem/add/` | — | `django.contrib.admin.options.add_view` | products_orgitem_add |
| `/admin/products/orgitem/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | products_orgitem_history |
| `/admin/products/orgitem/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | products_orgitem_delete |
| `/admin/products/orgitem/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | products_orgitem_change |
| `/admin/products/orgitem/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/products/serial/` | — | `django.contrib.admin.options.changelist_view` | products_serial_changelist |
| `/admin/products/serial/add/` | — | `django.contrib.admin.options.add_view` | products_serial_add |
| `/admin/products/serial/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | products_serial_history |
| `/admin/products/serial/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | products_serial_delete |
| `/admin/products/serial/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | products_serial_change |
| `/admin/products/serial/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/products/seriallog/` | — | `django.contrib.admin.options.changelist_view` | products_seriallog_changelist |
| `/admin/products/seriallog/add/` | — | `django.contrib.admin.options.add_view` | products_seriallog_add |
| `/admin/products/seriallog/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | products_seriallog_history |
| `/admin/products/seriallog/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | products_seriallog_delete |
| `/admin/products/seriallog/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | products_seriallog_change |
| `/admin/products/seriallog/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/products/catalog/` | — | `django.contrib.admin.options.changelist_view` | products_catalog_changelist |
| `/admin/products/catalog/add/` | — | `django.contrib.admin.options.add_view` | products_catalog_add |
| `/admin/products/catalog/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | products_catalog_history |
| `/admin/products/catalog/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | products_catalog_delete |
| `/admin/products/catalog/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | products_catalog_change |
| `/admin/products/catalog/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/products/catalogline/` | — | `django.contrib.admin.options.changelist_view` | products_catalogline_changelist |
| `/admin/products/catalogline/add/` | — | `django.contrib.admin.options.add_view` | products_catalogline_add |
| `/admin/products/catalogline/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | products_catalogline_history |
| `/admin/products/catalogline/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | products_catalogline_delete |
| `/admin/products/catalogline/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | products_catalogline_change |
| `/admin/products/catalogline/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/products/inventorycheck/` | — | `django.contrib.admin.options.changelist_view` | products_inventorycheck_changelist |
| `/admin/products/inventorycheck/add/` | — | `django.contrib.admin.options.add_view` | products_inventorycheck_add |
| `/admin/products/inventorycheck/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | products_inventorycheck_history |
| `/admin/products/inventorycheck/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | products_inventorycheck_delete |
| `/admin/products/inventorycheck/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | products_inventorycheck_change |
| `/admin/products/inventorycheck/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/products/inventorycheckline/` | — | `django.contrib.admin.options.changelist_view` | products_inventorycheckline_changelist |
| `/admin/products/inventorycheckline/add/` | — | `django.contrib.admin.options.add_view` | products_inventorycheckline_add |
| `/admin/products/inventorycheckline/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | products_inventorycheckline_history |
| `/admin/products/inventorycheckline/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | products_inventorycheckline_delete |
| `/admin/products/inventorycheckline/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | products_inventorycheckline_change |
| `/admin/products/inventorycheckline/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/products/deliveryvisit/` | — | `django.contrib.admin.options.changelist_view` | products_deliveryvisit_changelist |
| `/admin/products/deliveryvisit/add/` | — | `django.contrib.admin.options.add_view` | products_deliveryvisit_add |
| `/admin/products/deliveryvisit/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | products_deliveryvisit_history |
| `/admin/products/deliveryvisit/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | products_deliveryvisit_delete |
| `/admin/products/deliveryvisit/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | products_deliveryvisit_change |
| `/admin/products/deliveryvisit/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/products/deliveryline/` | — | `django.contrib.admin.options.changelist_view` | products_deliveryline_changelist |
| `/admin/products/deliveryline/add/` | — | `django.contrib.admin.options.add_view` | products_deliveryline_add |
| `/admin/products/deliveryline/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | products_deliveryline_history |
| `/admin/products/deliveryline/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | products_deliveryline_delete |
| `/admin/products/deliveryline/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | products_deliveryline_change |
| `/admin/products/deliveryline/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/products/itemusage/` | — | `django.contrib.admin.options.changelist_view` | products_itemusage_changelist |
| `/admin/products/itemusage/add/` | — | `django.contrib.admin.options.add_view` | products_itemusage_add |
| `/admin/products/itemusage/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | products_itemusage_history |
| `/admin/products/itemusage/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | products_itemusage_delete |
| `/admin/products/itemusage/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | products_itemusage_change |
| `/admin/products/itemusage/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/products/service/` | — | `django.contrib.admin.options.changelist_view` | products_service_changelist |
| `/admin/products/service/add/` | — | `django.contrib.admin.options.add_view` | products_service_add |
| `/admin/products/service/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | products_service_history |
| `/admin/products/service/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | products_service_delete |
| `/admin/products/service/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | products_service_change |
| `/admin/products/service/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/products/inventorymetricssnapshot/` | — | `django.contrib.admin.options.changelist_view` | products_inventorymetricssnapshot_changelist |
| `/admin/products/inventorymetricssnapshot/add/` | — | `django.contrib.admin.options.add_view` | products_inventorymetricssnapshot_add |
| `/admin/products/inventorymetricssnapshot/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | products_inventorymetricssnapshot_history |
| `/admin/products/inventorymetricssnapshot/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | products_inventorymetricssnapshot_delete |
| `/admin/products/inventorymetricssnapshot/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | products_inventorymetricssnapshot_change |
| `/admin/products/inventorymetricssnapshot/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/products/inventoryadjustmentprocessorrun/` | — | `django.contrib.admin.options.changelist_view` | products_inventoryadjustmentprocessorrun_changelist |
| `/admin/products/inventoryadjustmentprocessorrun/add/` | — | `django.contrib.admin.options.add_view` | products_inventoryadjustmentprocessorrun_add |
| `/admin/products/inventoryadjustmentprocessorrun/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | products_inventoryadjustmentprocessorrun_history |
| `/admin/products/inventoryadjustmentprocessorrun/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | products_inventoryadjustmentprocessorrun_delete |
| `/admin/products/inventoryadjustmentprocessorrun/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | products_inventoryadjustmentprocessorrun_change |
| `/admin/products/inventoryadjustmentprocessorrun/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/products/variant/` | — | `django.contrib.admin.options.changelist_view` | products_variant_changelist |
| `/admin/products/variant/add/` | — | `django.contrib.admin.options.add_view` | products_variant_add |
| `/admin/products/variant/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | products_variant_history |
| `/admin/products/variant/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | products_variant_delete |
| `/admin/products/variant/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | products_variant_change |
| `/admin/products/variant/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/products/inventoryreservation/` | — | `django.contrib.admin.options.changelist_view` | products_inventoryreservation_changelist |
| `/admin/products/inventoryreservation/add/` | — | `django.contrib.admin.options.add_view` | products_inventoryreservation_add |
| `/admin/products/inventoryreservation/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | products_inventoryreservation_history |
| `/admin/products/inventoryreservation/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | products_inventoryreservation_delete |
| `/admin/products/inventoryreservation/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | products_inventoryreservation_change |
| `/admin/products/inventoryreservation/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/products/specification/` | — | `django.contrib.admin.options.changelist_view` | products_specification_changelist |
| `/admin/products/specification/add/` | — | `django.contrib.admin.options.add_view` | products_specification_add |
| `/admin/products/specification/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | products_specification_history |
| `/admin/products/specification/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | products_specification_delete |
| `/admin/products/specification/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | products_specification_change |
| `/admin/products/specification/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/sync/connection/` | — | `django.contrib.admin.options.changelist_view` | sync_connection_changelist |
| `/admin/sync/connection/add/` | — | `django.contrib.admin.options.add_view` | sync_connection_add |
| `/admin/sync/connection/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | sync_connection_history |
| `/admin/sync/connection/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | sync_connection_delete |
| `/admin/sync/connection/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | sync_connection_change |
| `/admin/sync/connection/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/sync/bundle/` | — | `django.contrib.admin.options.changelist_view` | sync_bundle_changelist |
| `/admin/sync/bundle/add/` | — | `django.contrib.admin.options.add_view` | sync_bundle_add |
| `/admin/sync/bundle/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | sync_bundle_history |
| `/admin/sync/bundle/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | sync_bundle_delete |
| `/admin/sync/bundle/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | sync_bundle_change |
| `/admin/sync/bundle/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/transactions/invoice/` | — | `django.contrib.admin.options.changelist_view` | transactions_invoice_changelist |
| `/admin/transactions/invoice/add/` | — | `django.contrib.admin.options.add_view` | transactions_invoice_add |
| `/admin/transactions/invoice/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | transactions_invoice_history |
| `/admin/transactions/invoice/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | transactions_invoice_delete |
| `/admin/transactions/invoice/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | transactions_invoice_change |
| `/admin/transactions/invoice/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/transactions/invoiceline/` | — | `django.contrib.admin.options.changelist_view` | transactions_invoiceline_changelist |
| `/admin/transactions/invoiceline/add/` | — | `django.contrib.admin.options.add_view` | transactions_invoiceline_add |
| `/admin/transactions/invoiceline/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | transactions_invoiceline_history |
| `/admin/transactions/invoiceline/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | transactions_invoiceline_delete |
| `/admin/transactions/invoiceline/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | transactions_invoiceline_change |
| `/admin/transactions/invoiceline/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/transactions/workorderline/` | — | `django.contrib.admin.options.changelist_view` | transactions_workorderline_changelist |
| `/admin/transactions/workorderline/add/` | — | `django.contrib.admin.options.add_view` | transactions_workorderline_add |
| `/admin/transactions/workorderline/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | transactions_workorderline_history |
| `/admin/transactions/workorderline/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | transactions_workorderline_delete |
| `/admin/transactions/workorderline/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | transactions_workorderline_change |
| `/admin/transactions/workorderline/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/transactions/order/` | — | `django.contrib.admin.options.changelist_view` | transactions_order_changelist |
| `/admin/transactions/order/add/` | — | `django.contrib.admin.options.add_view` | transactions_order_add |
| `/admin/transactions/order/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | transactions_order_history |
| `/admin/transactions/order/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | transactions_order_delete |
| `/admin/transactions/order/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | transactions_order_change |
| `/admin/transactions/order/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/transactions/orderline/` | — | `django.contrib.admin.options.changelist_view` | transactions_orderline_changelist |
| `/admin/transactions/orderline/add/` | — | `django.contrib.admin.options.add_view` | transactions_orderline_add |
| `/admin/transactions/orderline/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | transactions_orderline_history |
| `/admin/transactions/orderline/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | transactions_orderline_delete |
| `/admin/transactions/orderline/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | transactions_orderline_change |
| `/admin/transactions/orderline/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/transactions/purchase/` | — | `django.contrib.admin.options.changelist_view` | transactions_purchase_changelist |
| `/admin/transactions/purchase/add/` | — | `django.contrib.admin.options.add_view` | transactions_purchase_add |
| `/admin/transactions/purchase/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | transactions_purchase_history |
| `/admin/transactions/purchase/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | transactions_purchase_delete |
| `/admin/transactions/purchase/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | transactions_purchase_change |
| `/admin/transactions/purchase/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/transactions/project/` | — | `django.contrib.admin.options.changelist_view` | transactions_project_changelist |
| `/admin/transactions/project/add/` | — | `django.contrib.admin.options.add_view` | transactions_project_add |
| `/admin/transactions/project/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | transactions_project_history |
| `/admin/transactions/project/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | transactions_project_delete |
| `/admin/transactions/project/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | transactions_project_change |
| `/admin/transactions/project/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/transactions/purchaseline/` | — | `django.contrib.admin.options.changelist_view` | transactions_purchaseline_changelist |
| `/admin/transactions/purchaseline/add/` | — | `django.contrib.admin.options.add_view` | transactions_purchaseline_add |
| `/admin/transactions/purchaseline/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | transactions_purchaseline_history |
| `/admin/transactions/purchaseline/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | transactions_purchaseline_delete |
| `/admin/transactions/purchaseline/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | transactions_purchaseline_change |
| `/admin/transactions/purchaseline/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/transactions/proposal/` | — | `django.contrib.admin.options.changelist_view` | transactions_proposal_changelist |
| `/admin/transactions/proposal/add/` | — | `django.contrib.admin.options.add_view` | transactions_proposal_add |
| `/admin/transactions/proposal/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | transactions_proposal_history |
| `/admin/transactions/proposal/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | transactions_proposal_delete |
| `/admin/transactions/proposal/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | transactions_proposal_change |
| `/admin/transactions/proposal/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/transactions/proposalline/` | — | `django.contrib.admin.options.changelist_view` | transactions_proposalline_changelist |
| `/admin/transactions/proposalline/add/` | — | `django.contrib.admin.options.add_view` | transactions_proposalline_add |
| `/admin/transactions/proposalline/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | transactions_proposalline_history |
| `/admin/transactions/proposalline/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | transactions_proposalline_delete |
| `/admin/transactions/proposalline/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | transactions_proposalline_change |
| `/admin/transactions/proposalline/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/transactions/requisition/` | — | `django.contrib.admin.options.changelist_view` | transactions_requisition_changelist |
| `/admin/transactions/requisition/add/` | — | `django.contrib.admin.options.add_view` | transactions_requisition_add |
| `/admin/transactions/requisition/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | transactions_requisition_history |
| `/admin/transactions/requisition/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | transactions_requisition_delete |
| `/admin/transactions/requisition/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | transactions_requisition_change |
| `/admin/transactions/requisition/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/transactions/requisitionline/` | — | `django.contrib.admin.options.changelist_view` | transactions_requisitionline_changelist |
| `/admin/transactions/requisitionline/add/` | — | `django.contrib.admin.options.add_view` | transactions_requisitionline_add |
| `/admin/transactions/requisitionline/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | transactions_requisitionline_history |
| `/admin/transactions/requisitionline/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | transactions_requisitionline_delete |
| `/admin/transactions/requisitionline/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | transactions_requisitionline_change |
| `/admin/transactions/requisitionline/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/transactions/receipt/` | — | `django.contrib.admin.options.changelist_view` | transactions_receipt_changelist |
| `/admin/transactions/receipt/add/` | — | `django.contrib.admin.options.add_view` | transactions_receipt_add |
| `/admin/transactions/receipt/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | transactions_receipt_history |
| `/admin/transactions/receipt/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | transactions_receipt_delete |
| `/admin/transactions/receipt/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | transactions_receipt_change |
| `/admin/transactions/receipt/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/transactions/workorder/` | — | `django.contrib.admin.options.changelist_view` | transactions_workorder_changelist |
| `/admin/transactions/workorder/add/` | — | `django.contrib.admin.options.add_view` | transactions_workorder_add |
| `/admin/transactions/workorder/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | transactions_workorder_history |
| `/admin/transactions/workorder/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | transactions_workorder_delete |
| `/admin/transactions/workorder/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | transactions_workorder_change |
| `/admin/transactions/workorder/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/transactions/payment/` | — | `django.contrib.admin.options.changelist_view` | transactions_payment_changelist |
| `/admin/transactions/payment/add/` | — | `django.contrib.admin.options.add_view` | transactions_payment_add |
| `/admin/transactions/payment/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | transactions_payment_history |
| `/admin/transactions/payment/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | transactions_payment_delete |
| `/admin/transactions/payment/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | transactions_payment_change |
| `/admin/transactions/payment/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/transactions/paymentmethod/` | — | `django.contrib.admin.options.changelist_view` | transactions_paymentmethod_changelist |
| `/admin/transactions/paymentmethod/add/` | — | `django.contrib.admin.options.add_view` | transactions_paymentmethod_add |
| `/admin/transactions/paymentmethod/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | transactions_paymentmethod_history |
| `/admin/transactions/paymentmethod/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | transactions_paymentmethod_delete |
| `/admin/transactions/paymentmethod/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | transactions_paymentmethod_change |
| `/admin/transactions/paymentmethod/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/transactions/paymentterm/` | — | `django.contrib.admin.options.changelist_view` | transactions_paymentterm_changelist |
| `/admin/transactions/paymentterm/add/` | — | `django.contrib.admin.options.add_view` | transactions_paymentterm_add |
| `/admin/transactions/paymentterm/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | transactions_paymentterm_history |
| `/admin/transactions/paymentterm/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | transactions_paymentterm_delete |
| `/admin/transactions/paymentterm/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | transactions_paymentterm_change |
| `/admin/transactions/paymentterm/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/transactions/paymentapplication/` | — | `django.contrib.admin.options.changelist_view` | transactions_paymentapplication_changelist |
| `/admin/transactions/paymentapplication/add/` | — | `django.contrib.admin.options.add_view` | transactions_paymentapplication_add |
| `/admin/transactions/paymentapplication/<path:object_id>/history/` | — | `django.contrib.admin.options.history_view` | transactions_paymentapplication_history |
| `/admin/transactions/paymentapplication/<path:object_id>/delete/` | — | `django.contrib.admin.options.delete_view` | transactions_paymentapplication_delete |
| `/admin/transactions/paymentapplication/<path:object_id>/change/` | — | `django.contrib.admin.options.change_view` | transactions_paymentapplication_change |
| `/admin/transactions/paymentapplication/<path:object_id>/` | GET, POST, PUT, PATCH, DELETE, HEAD | `django.views.generic.base.RedirectView` | — |
| `/admin/^(?P<app_label>accounts|ai_assistant|communications|auth|core|docs|orgs|products|sync|transactions)/$` | — | `apps.core.admin._threepane_app_index` | app_list |
| `/admin/(?P<url>.*)$` | — | `django.contrib.admin.sites.catch_all_view` | — |
| `/^static/(?P<path>.*)$` | — | `django.views.static.serve` | — |