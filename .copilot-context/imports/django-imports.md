# Django Canonical Import Paths

> Auto-generated. Every public class/function with its exact import path.
> Generated: 2026-02-22 13:25

---

## Models

| Class | Import |
|-------|--------|
| `Action` | `from apps.core.models.action import Action` |
| `Address` | `from apps.communications.models.address import Address` |
| `Audit` | `from apps.accounts.models.audit import Audit` |
| `AuditLog` | `from apps.core.models.audit import AuditLog` |
| `BillOfMaterial` | `from apps.products.models.bill_of_material import BillOfMaterial` |
| `Bundle` | `from apps.sync.models.bundle import Bundle` |
| `Catalog` | `from apps.products.models.catalog import Catalog` |
| `CatalogLine` | `from apps.products.models.catalog import CatalogLine` |
| `Connection` | `from apps.sync.models.connection import Connection` |
| `Contact` | `from apps.core.models.contact import Contact` |
| `Conversation` | `from apps.ai_assistant.models import Conversation` |
| `Currency` | `from apps.accounts.models.currency import Currency` |
| `Customer` | `from apps.orgs.models.proxies import Customer` |
| `DeliveryLine` | `from apps.products.models.flow import DeliveryLine` |
| `DeliveryVisit` | `from apps.products.models.flow import DeliveryVisit` |
| `Document` | `from apps.docs.models.document import Document` |
| `Domain` | `from apps.communications.models.domain import Domain` |
| `Email` | `from apps.communications.models.email import Email` |
| `Employee` | `from apps.orgs.models.proxies import Employee` |
| `ExchangeRate` | `from apps.accounts.models.exchange_rate import ExchangeRate` |
| `ExchangeTransaction` | `from apps.accounts.models.exchange_transaction import ExchangeTransaction` |
| `GlAccount` | `from apps.accounts.models.gl_account import GlAccount` |
| `GlJournal` | `from apps.accounts.models.gl_journal import GlJournal` |
| `InventoryAdjustmentProcessorRun` | `from apps.products.models.processor_runs import InventoryAdjustmentProcessorRun` |
| `InventoryCheck` | `from apps.products.models.inventory_check import InventoryCheck` |
| `InventoryCheckLine` | `from apps.products.models.inventory_check import InventoryCheckLine` |
| `InventoryLayer` | `from apps.products.models.inventory_layer import InventoryLayer` |
| `InventoryMetricsSnapshot` | `from apps.products.models.metrics import InventoryMetricsSnapshot` |
| `InventoryMovement` | `from apps.products.models.inventory_layer import InventoryMovement` |
| `InventoryReservation` | `from apps.products.models.inventory_reservation import InventoryReservation` |
| `Invoice` | `from apps.transactions.models.invoice import Invoice` |
| `InvoiceLine` | `from apps.transactions.models.invoice_line import InvoiceLine` |
| `Item` | `from apps.products.models.item import Item` |
| `ItemUsage` | `from apps.products.models.usage import ItemUsage` |
| `ItemXRef` | `from apps.products.models.item_xref import ItemXRef` |
| `Ledger` | `from apps.accounts.models.ledger import Ledger` |
| `LinkageEntry` | `from apps.docs.models.linkage_entry import LinkageEntry` |
| `Manufacturer` | `from apps.orgs.models.proxies import Manufacturer` |
| `Message` | `from apps.ai_assistant.models import Message` |
| `Notification` | `from apps.core.models.notification import Notification` |
| `Order` | `from apps.transactions.models.order import Order` |
| `OrderLine` | `from apps.transactions.models.order_line import OrderLine` |
| `OrgBase` | `from apps.orgs.models.base import OrgBase` |
| `OrgItem` | `from apps.products.models.org_item import OrgItem` |
| `Payment` | `from apps.transactions.models.payment import Payment` |
| `PaymentApplication` | `from apps.transactions.models.payment_application import PaymentApplication` |
| `PaymentMethod` | `from apps.transactions.models.payment import PaymentMethod` |
| `PaymentTerm` | `from apps.transactions.models.payment import PaymentTerm` |
| `Pending` | `from apps.core.models.pending import Pending` |
| `PendingInventoryAdjustment` | `from apps.products.models.inventory_layer import PendingInventoryAdjustment` |
| `Phone` | `from apps.communications.models.phone import Phone` |
| `Project` | `from apps.transactions.models.project import Project` |
| `Proposal` | `from apps.transactions.models.proposal import Proposal` |
| `ProposalLine` | `from apps.transactions.models.proposal_line import ProposalLine` |
| `Purchase` | `from apps.transactions.models.purchase import Purchase` |
| `PurchaseLine` | `from apps.transactions.models.purchase_line import PurchaseLine` |
| `QuestionAnswer` | `from apps.docs.models.question_answer import QuestionAnswer` |
| `Receipt` | `from apps.transactions.models.receipt import Receipt` |
| `ReceiptLine` | `from apps.transactions.models.receipt_line import ReceiptLine` |
| `RefsMismatchLog` | `from apps.core.models.refs_mismatch_log import RefsMismatchLog` |
| `Rep` | `from apps.orgs.models.proxies import Rep` |
| `Report` | `from apps.core.models.report import Report` |
| `Requisition` | `from apps.transactions.models.requisition import Requisition` |
| `RequisitionLine` | `from apps.transactions.models.requisition_line import RequisitionLine` |
| `Serial` | `from apps.products.models.serial import Serial` |
| `SerialLog` | `from apps.products.models.serial import SerialLog` |
| `Service` | `from apps.products.models.service import Service` |
| `Setting` | `from apps.core.models.setting import Setting` |
| `SiteInventory` | `from apps.products.models.inventory_layer import SiteInventory` |
| `SoftDeleteLedger` | `from apps.core.models.soft_delete import SoftDeleteLedger` |
| `Specification` | `from apps.products.models.specification import Specification` |
| `Tag` | `from apps.docs.models.tag import Tag` |
| `TaxJurisdiction` | `from apps.accounts.models.tax_jurisdiction import TaxJurisdiction` |
| `Template` | `from apps.core.models.template import Template` |
| `Term` | `from apps.accounts.models.term import Term` |
| `Variant` | `from apps.products.models.variant import Variant` |
| `Vendor` | `from apps.orgs.models.proxies import Vendor` |
| `Warehouse` | `from apps.products.models.warehouse import Warehouse` |
| `WorkOrder` | `from apps.transactions.models.workorder import WorkOrder` |
| `WorkOrderLine` | `from apps.transactions.models.workorder_line import WorkOrderLine` |


## Services & Business Logic

| Module | Key Exports |
|--------|-------------|
| `apps.accounts.services.gl_defaults` | `assign_gl_defaults()`, `GLDefaultsMixin` |
| `apps.accounts.services.ledger_balance` | `calculate_aging_buckets()`, `update_org_balances()`, `on_invoice_save()`, `on_payment_save()`, `reconcile_org()` + 1 more |
| `apps.accounts.services.terms_ledger` | `ScheduleEntry`, `compute_schedule()`, `create_ledger_records()`, `apply_terms_for_invoice()`, `record_payment()` |
| `apps.ai_assistant.services.ollama_client` | `OllamaClient` |
| `apps.ai_assistant.services.prompt_templates` | `get_system_prompt()`, `get_available_modes()`, `wrap_query()` |
| `apps.ai_assistant.services.rag_service` | `RAGService` |
| `apps.ai_assistant.services.vector_store` | `VectorStoreManager` |
| `apps.core.services.action_service` | `append_contact_link()`, `append_contact_link()`, `add_child_dependency()`, `add_parent_dependency()`, `remove_child_dependency()` + 7 more |
| `apps.core.services.cache_service` | `CacheService` |
| `apps.core.services.keywords` | `build_keywords_for_record()`, `create_pending_keyword_update()` |
| `apps.core.services.wcapi` | `to_dict()`, `filter_input_fields()`, `get_queryset()`, `get_item()`, `list_items()` + 2 more |
| `apps.core.services.wcapi_registry` | `get_model()`, `to_model_name()`, `normalize_table_key()` |
| `apps.docs.services.qa_service` | `QAService` |
| `apps.products.models.service` | `default_billing()`, `default_process()`, `default_travel_details()`, `Service` |
| `apps.products.services.bom_services` | `list_bom_lines()`, `create_bom_line()`, `update_bom_line()`, `delete_bom_line()`, `recalc_parent_cost()` |
| `apps.products.services.inventory_adjustment_processor` | `process_pending_inventory()`, `process_pending_for_stack()` |
| `apps.products.services.inventory_metrics` | `summarize_inventory_metrics()`, `snapshot_inventory_metrics()` |
| `apps.products.services.inventory_reservations` | `create_reservation()`, `release_expired()`, `availability_for_stack()` |
| `apps.sync.services.address_verification` | `get_verification_connection()`, `verify_address_via_connection()` |
| `apps.sync.services.decisions` | `accept_email_verification()`, `reject_bundle()` |
| `apps.sync.services.domain_verification` | `get_verification_connection()`, `verify_domain_via_connection()` |
| `apps.sync.services.email_verification` | `get_verification_connection()`, `verify_email_via_connection()` |
| `apps.sync.services.google_calendar` | `get_authorization_url()`, `exchange_code_for_tokens()`, `list_events()` |
| `apps.sync.services.incidents` | `trigger_safety_alert()` |
| `apps.sync.services.phone_verification` | `get_verification_connection()`, `verify_phone_via_connection()` |
| `apps.sync.services.standards` | `normalize_severity()`, `alert_category_for_event()`, `normalize_email_result()` |
| `apps.transactions.services.denormalize_org_links` | `denormalize_org_links()` |
| `apps.transactions.services.email_notifications` | `TransactionEmailService` |
| `apps.transactions.services.flow` | `ReceiveLine`, `ensure_linkage_for_lines()`, `proposal_to_order()`, `order_to_invoice()`, `order_to_purchase()` + 6 more |
| `apps.transactions.services.inventory_flow` | `InventoryFlowError`, `reserve_inventory_for_order()`, `release_inventory_on_invoice()`, `cancel_order_inventory_reservations()`, `create_inventory_deltas_for_order()` + 4 more |
| `apps.transactions.services.invoice_to_purchase` | `InvoiceToPurchaseTransferError`, `transfer_invoice_to_purchase()` |
| `apps.transactions.services.invoice_totals` | `compute_invoice_sell_cost_totals()` |
| `apps.transactions.services.line_item_service` | `LineItemService`, `add_item_to_transaction()` |
| `apps.transactions.services.order_to_invoice` | `OrderToInvoiceTransferError`, `transfer_order_to_invoice()` |
| `apps.transactions.services.order_to_purchase` | `OrderToPurchaseTransferError`, `transfer_order_to_purchase()` |
| `apps.transactions.services.order_totals` | `compute_order_sell_cost_totals()` |
| `apps.transactions.services.payment_application` | `PaymentApplicationError`, `apply_payment_to_invoice()`, `unapply_payment_from_invoice()`, `get_invoice_payment_status()` |
| `apps.transactions.services.payment_gateways` | `StripeService`, `PayPalService`, `PaymentReconciliationService` |
| `apps.transactions.services.pending_inventory_processor` | `ProcessingSummary`, `process_line_item_pending()`, `process_pending_for_item()` |
| `apps.transactions.services.po_totals` | `compute_purchase_cost_totals()` |
| `apps.transactions.services.proposal_to_order` | `ProposalToOrderTransferError`, `validate_proposal_for_transfer()`, `transfer_proposal_to_order()` |
| `apps.transactions.services.proposal_to_purchase` | `ProposalToPurchaseTransferError`, `transfer_proposal_to_purchase()` |
| `apps.transactions.services.proposal_totals` | `compute_proposal_sell_cost_totals()` |
| `apps.transactions.services.purchase_to_invoice` | `PurchaseToInvoiceTransferError`, `transfer_purchase_to_invoice()` |
| `apps.transactions.services.purchase_to_order` | `PurchaseToOrderTransferError`, `transfer_purchase_to_order()` |
| `apps.transactions.services.purchase_to_proposal` | `PurchaseToProposalTransferError`, `transfer_purchase_to_proposal()` |
| `apps.transactions.services.purchase_totals` | `compute_purchase_sell_cost_totals()` |
| `apps.transactions.services.tax_service` | `TaxService`, `calculate_transaction_tax()` |
| `apps.transactions.services.trace_debug` | `enable_trace()`, `disable_trace()`, `transaction_trace`, `should_trace()`, `trace_line_add()` + 5 more |
| `apps.transactions.services.transaction_save` | `CalculationMismatchError`, `ItemIdChangeError`, `calculate_line_extended()`, `verify_line_calculations()`, `calculate_header_totals()` + 2 more |
| `apps.transactions.services.transfer` | `TransferError`, `execute_transfer()` |
| `apps.transactions.services.transfer_utils` | `sum_price_extended()`, `convert_quantity_from_source()`, `select_lines()`, `build_line_payload()` |
| `apps.transactions.services.validation` | `ValidationResult`, `validate_proposal_for_conversion()`, `validate_order_for_invoicing()`, `validate_invoice_for_payment()`, `validate_transaction_flow()` |
| `apps.transactions.services.wo_totals` | `compute_work_order_cost_totals()` |


## Views

| Module | Key Exports |
|--------|-------------|
| `apps.ai_assistant.views` | `AskView`, `FeedbackView`, `HealthView`, `HistoryView`, `DebugView` + 4 more |
| `apps.core.token_views` | `RoleTokenObtainPairSerializer`, `RoleTokenObtainPairView` |
| `apps.core.views.action_views` | `ActionSerializer`, `ActionViewSet` |
| `apps.core.views.api_log` | `APILogView` |
| `apps.core.views.auth_views` | `AuthLoginView`, `AuthLogoutView`, `AuthMeView`, `AuthRegisterView` |
| `apps.core.views.choices` | `ChoiceCatalogView` |
| `apps.core.views.cookie_token_refresh` | `CookieTokenRefreshView` |
| `apps.core.views.dev_tools` | `dev_config_status()`, `dev_sync_status()`, `dev_sync_status()`, `dev_switch_mode()`, `dev_sync_data()` + 1 more |
| `apps.core.views.refs_mismatch_view` | `RefsMismatchView` |
| `apps.core.views.save_view` | `check_field_size()`, `deep_merge_dict()`, `get_nested_value()`, `set_nested_value()`, `delete_nested_value()` + 3 more |
| `apps.core.views.system_info` | `SystemInfoView` |
| `apps.core.views.token_cookie` | `set_refresh_cookie()`, `clear_refresh_cookie()` |
| `apps.core.views.wcapi` | `WCAPIDeleteView`, `WCAPIGetView`, `ModelNameListView`, `ModelDetailView`, `WCAPIGetViewWithModel` |
| `apps.orgs.views.customer_viewset` | `OrgBaseViewSet`, `CustomerViewSet`, `VendorViewSet`, `RepViewSet`, `EmployeeViewSet` + 1 more |
| `apps.products.views.bom_views` | `BOMListCreateView`, `BOMDetailView`, `BOMRecalcCostView` |
| `apps.products.views.inventory` | `ReservationListView`, `ReservationDetailView`, `ReservationCommitView`, `ReservationActionView` |
| `apps.products.views.inventory_views` | `InventoryAvailabilityView`, `InventoryReservationCreateView`, `InventoryReservationActionView`, `InventoryMetricsView`, `InventoryPrometheusMetricsView` |
| `apps.products.views.item_variants` | `ItemVariantsView` |
| `apps.sync.views.connection` | `SyncPagination`, `ConnectionListView`, `ConnectionDetailView`, `ConnectionSearchView` |
| `apps.sync.views.google_calendar` | `GCAL_StartAuthView`, `GCAL_OAuthCallbackView`, `GCAL_ListEventsView` |
| `apps.transactions.views.actions` | `ProposalToOrderView`, `OrderToInvoiceView`, `OrderToPurchaseView`, `LinkageCommentsAggregateView`, `ReceivePurchaseView` + 2 more |
| `apps.transactions.views.invoice_views` | `InvoiceViewSet`, `InvoiceLineViewSet` |
| `apps.transactions.views.line_views` | `BasePermission`, `DefaultPagination`, `ProposalListCreate`, `ProposalRetrieveUpdate`, `ProposalLineListCreate` + 27 more |
| `apps.transactions.views.linkage_views` | `LinkageCommentsView` |
| `apps.transactions.views.order_views` | `OrderViewSet`, `OrderLineViewSet`, `OrderToInvoiceView`, `OrderToPurchaseView` |
| `apps.transactions.views.payment_views` | `process_payment()`, `execute_paypal_payment()`, `stripe_webhook()`, `paypal_webhook()`, `reconcile_payments()` + 3 more |
| `apps.transactions.views.project_views` | `ProjectListView` |
| `apps.transactions.views.proposal_views` | `ProposalViewSet`, `ProposalLineViewSet` |
| `apps.transactions.views.purchase_views` | `ReceivePurchaseView` |
| `apps.transactions.views.requisition` | `RequisitionListView`, `RequisitionDetailView`, `RequisitionSearchView` |
| `apps.transactions.views.transaction_views` | `ProposalViewSet`, `OrderViewSet`, `PurchaseViewSet`, `InvoiceViewSet`, `PaymentViewSet` |
| `apps.transactions.views.transfer_views` | `validate_transfer()`, `execute_transfer()`, `apply_payment()`, `reserve_inventory()`, `release_inventory()` + 2 more |
| `apps.transactions.views.unified` | `TransactionHeaderListCreate`, `TransactionHeaderDetail`, `TransactionLineListCreate`, `TransactionLineDetail`, `TransactionTotalsPreview` + 2 more |
| `apps.transactions.views.wcapi` | `to_dict()`, `filter_input_fields()`, `inject_constraints()`, `WCAPITransactionSaveView`, `WCAPIGetView` + 4 more |