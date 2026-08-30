# Alice Schema Watch Report

- Timestamp (UTC): 2026-03-14 20:07:39
- Commit: working-tree
- Schema files touched: 1
- Models touched: item, order, invoice, document, contact, payment, customer, vendor, requisition, audit, report, connection
- Drift issues: total=949, high=148, medium=309, low=492

## Schema Files
- apps/orgs/models.py

## Likely Impacted Pages (Field-Level)
- [item] src/apps/products/models/item/pages/ItemDetail.tsx (score=52)
  fields: allocated, attributes, available, avg, back_order_allowed, base, catalog, categories, category, code, components, cost
- [contact] src/apps/core/models/contact/pages/ContactDetail3.tsx (score=33)
  fields: address, address_full, address_id, categories, contact, customer, dataProp, depends_on, document, domain, domain_id, email_id
- [contact] src/apps/core/models/contact/pages/ContactDetail2.tsx (score=33)
  fields: address, address_full, address_id, categories, contact, customer, dataProp, depends_on, document, domain, domain_id, email_id
- [contact] src/apps/core/models/contact/pages/ContactDetail.tsx (score=33)
  fields: address, address_full, address_id, categories, contact, customer, dataProp, depends_on, document, domain, domain_id, email_id
- [invoice] src/apps/transactions/models/invoice/pages/qqq_InvoiceDetailLegacy.tsx (score=28)
  fields: actions, cost, dataProp, description, finance, flow, hideBreadcrumb, ida_item, inline, item, itemId, itemNum
- [contact] src/apps/core/models/contact/pages/qqq_ContactDetail_RijuButtons.tsx (score=27)
  fields: address, categories, contact, customer, dataProp, depends_on, document, domain, hideBreadcrumb, inline, item, keywords
- [contact] src/apps/core/models/contact/pages/qqq_ContactDetailTwoColumn.tsx (score=27)
  fields: address, categories, contact, customer, dataProp, depends_on, document, domain, hideBreadcrumb, inline, item, keywords
- [contact] src/apps/core/models/contact/pages/qqq_ContactDetailStart.tsx (score=27)
  fields: address, categories, contact, customer, dataProp, depends_on, document, domain, hideBreadcrumb, inline, item, keywords
- [contact] src/apps/core/models/contact/pages/qqq_ContactDetailHorizontal.tsx (score=27)
  fields: address, categories, contact, customer, dataProp, depends_on, document, domain, hideBreadcrumb, inline, item, keywords
- [vendor] src/apps/orgs/models/vendor/pages/VendorDetail.tsx (score=25)
  fields: address_full, address_id, addresses, contacts, dataProp, docs, domain, domain_id, domains, email_id, emails, financial
- [customer] src/apps/orgs/models/customer/pages/CustomerDetail.tsx (score=25)
  fields: address_full, address_id, addresses, contacts, dataProp, docs, domain, domain_id, domains, email_id, emails, financial
- [document] src/apps/docs/models/document/pages/DocumentDetail.tsx (score=23)
  fields: TODO, body, checksum, comment, confidential, content, copyright, count_accessed, data, dataProp, description, hideBreadcrumb
- [document] src/apps/docs/models/document/pages/DocumentDisplay.tsx (score=20)
  fields: TODO, body, checksum, comment, confidential, content, count_accessed, data, dataProp, description, history, inline
- [order] src/apps/transactions/models/order/pages/OrderDetail.tsx (score=19)
  fields: dataProp, description, inline, isAdmin, is_locked, item, key, lines, modeProp, name, onCancelInline, onSaved
- [payment] src/apps/transactions/models/payment/pages/PaymentDetailPage.tsx (score=16)
  fields: amount_available, applied_at, contact_name, customer_name, dt_created, dt_modified, dt_payment, gateway, invoice_ids, invoice_number, metadata, name
- [report] src/apps/core/models/report/pages/ReportDetail.tsx (score=12)
  fields: TODO, data, dataProp, hideBreadcrumb, id, inline, modeProp, onCancelInline, onSaved, parameters, title, type
- [connection] src/apps/sync/models/connection/pages/qqq_ConnectionDetail.tsx (score=12)
  fields: TODO, dataProp, database, hideBreadcrumb, host, inline, modeProp, onCancelInline, onSaved, password, port, username
- [audit] src/apps/accounts/models/audit/pages/AuditList.tsx (score=12)
  fields: TODO, action, dataProp, date, description, id, inline, modeProp, name, onCancelInline, onSaved, user
- [audit] src/apps/accounts/models/audit/pages/AuditDetail.tsx (score=12)
  fields: TODO, action, dataProp, date, description, hideBreadcrumb, id, inline, modeProp, onCancelInline, onSaved, user
- [report] src/apps/core/models/report/pages/ReportList.tsx (score=11)
  fields: TODO, data, dataProp, id, inline, modeProp, name, onCancelInline, onSaved, title, type
- [connection] src/apps/sync/models/connection/pages/qqq_ConnectionList.tsx (score=11)
  fields: TODO, dataProp, database, host, inline, modeProp, onCancelInline, onSaved, port, status, username
- [requisition] src/apps/transactions/models/requisition/pages/RequisitionDetail.tsx (score=10)
  fields: actions, dataProp, hideBreadcrumb, inline, lines, modeProp, onCancelInline, onSaved, priority, status
- [report] src/apps/core/models/report/pages/ReportDisplay.tsx (score=10)
  fields: TODO, data, dataProp, id, inline, modeProp, onCancelInline, onSaved, title, type
- [item] src/apps/products/models/item/pages/ItemList.tsx (score=10)
  fields: category, components, dataProp, inline, key, kind, modeProp, onCancelInline, onSaved, price
- [contact] src/apps/core/models/contact/pages/qqq_ContactDetailDense.tsx (score=10)
  fields: address, contact, dataProp, hideBreadcrumb, inline, modeProp, name, number, onCancelInline, onSaved
- [payment] src/apps/transactions/models/payment/pages/PaymentListPage.tsx (score=9)
  fields: amount_available, customer_name, dt_created, dt_payment, gateway, invoice_number, name, payment_method_name, status
- [order] src/apps/transactions/models/order/pages/OrderList.tsx (score=9)
  fields: dataProp, inline, key, lines, modeProp, name, onCancelInline, onSaved, order_id
- [item] src/apps/products/models/item/pages/ItemDashboard.tsx (score=9)
  fields: available, catalog, cost, flags, kind, price, quantity, serialized, tax_code
- [customer] src/apps/orgs/models/customer/pages/CustomerDataPanel.tsx (score=9)
  fields: addresses, contacts, docs, domains, emails, financial, metrics, phones, relations
- [contact] src/apps/core/models/contact/pages/qqq_ContactList1.tsx (score=9)
  fields: contact, dataProp, getContactData, inline, modeProp, name, number, onCancelInline, onSaved
- [contact] src/apps/core/models/contact/pages/ContactList.tsx (score=9)
  fields: contact, dataProp, inline, item, modeProp, name, number, onCancelInline, onSaved
- [audit] src/apps/accounts/models/audit/pages/AuditDisplay.tsx (score=9)
  fields: TODO, dataProp, description, id, inline, modeProp, name, onCancelInline, onSaved
- [requisition] src/apps/transactions/models/requisition/pages/RequisitionList.tsx (score=8)
  fields: actions, dataProp, inline, modeProp, name, onCancelInline, onSaved, status
- [invoice] src/apps/transactions/models/invoice/pages/InvoiceDetail.tsx (score=8)
  fields: actions, invoice_id, is_locked, key, lines, status, tax, totals
- [document] src/apps/docs/models/document/pages/DocumentList.tsx (score=8)
  fields: TODO, data, dataProp, inline, modeProp, model_name, onCancelInline, onSaved
- [vendor] src/apps/orgs/models/vendor/pages/VendorList.tsx (score=7)
  fields: dataProp, inline, modeProp, onCancelInline, onSaved, org_type, terms
- [customer] src/apps/orgs/models/customer/pages/CustomerList.tsx (score=7)
  fields: dataProp, inline, modeProp, onCancelInline, onSaved, org_type, terms
- [customer] src/apps/orgs/models/customer/pages/CustomerDashboard.tsx (score=7)
  fields: addresses, contacts, domains, emails, financial, phones, relations
- [contact] src/apps/core/models/contact/pages/ContactListMob.tsx (score=6)
  fields: contact, dataProp, document, item, name, number
- [customer] src/apps/orgs/models/customer/pages/CustomerHeader.tsx (score=5)
  fields: addresses, contacts, docs, inline, org_type
- [invoice] src/apps/transactions/models/invoice/pages/InvoiceList.tsx (score=4)
  fields: key, lines, name, status
- [vendor] src/apps/orgs/models/vendor/pages/VendorListMob.tsx (score=3)
  fields: dataProp, org_type, terms
- [customer] src/apps/orgs/models/customer/pages/CustomerListMob.tsx (score=3)
  fields: dataProp, org_type, terms
- [contact] src/apps/core/models/contact/pages/qqq_ContactDetailWithSelector.tsx (score=3)
  fields: hideBreadcrumb, inline, modeProp
- [report] src/apps/core/models/report/pages/Report.tsx (score=1)
  fields: TODO
- [document] src/apps/docs/models/document/pages/DocumentIndex.tsx (score=1)
  fields: TODO
- [audit] src/apps/accounts/models/audit/pages/Audit.tsx (score=1)
  fields: TODO

## Per-Model Drift Summary
- address: 18 issues
- audit: 28 issues
- bundle: 28 issues
- catalog: 24 issues
- connection: 28 issues
- contact: 38 issues
- currency: 18 issues
- customer: 30 issues
- document: 41 issues
- domain: 21 issues
- email: 16 issues
- employee: 25 issues
- invoice: 52 issues
- item: 53 issues
- manufacturer: 25 issues
- notification: 21 issues
- order: 52 issues
- payment: 38 issues
- phone: 17 issues
- project: 20 issues
- proposal: 28 issues
- purchase: 24 issues
- receipt: 9 issues
- rep: 25 issues
- report: 28 issues
- requisition: 30 issues
- serial: 20 issues
- service: 24 issues
- setting: 16 issues
- specification: 21 issues
- tag: 24 issues
- template: 17 issues
- variant: 19 issues
- vendor: 30 issues
- warehouse: 17 issues
- workorder: 24 issues

## Admin.py Field Usage

### item
- apps/core/admin.py
  - L47: list_display = scalar_fields
  - L49: search_fields = ('email', 'name_first', 'name_last', 'company')
  - L50: readonly_fields = ('id', 'uuid', 'ida', 'dt_created', 'dt_modified', 'dt_joined', 'version')
  - L64: # Specify the fields to be used in displaying the User model
  - L65: # These are the fields that inherit from BaseUserAdmin but we override for our Contact model
  - L69: 'fields': ('email', 'password1', 'password2'),
  - L73: 'fields': ('name_first', 'name_last', 'name_middle', 'name_prefix', 'name_suffix'),
  - L77: 'fields': (
  - L91: 'fields': ('role', 'is_active', 'is_staff'),
  - L95: fieldsets = (
  - L96: (None, {'fields': ('email', 'password')}),
  - L97: ('Scalar fields', {'fields': (
  - L106: ('JSONB fields', {
  - L107: 'fields': ('actions', 'comment', 'comments', 'groups', 'metadata', 'prefs', 'refs', 'user_permissions'),
  - L111: 'fields': ('id', 'uuid', 'ida', 'dt_created', 'dt_modified', 'dt_joined', 'version'),
  - L116: # Override the get_fieldsets method to use our custom fieldsets
  - L138: list_display = ('id', 'get_action_title', 'project_id', 'project_name', 'kanban_column', 'status', 'priority', 'dt_deadline')
  - L140: search_fields = ('project_id', 'action')
  - L141: readonly_fields = ('uuid', 'dt_created', 'dt_modified')
  - L142: # Keep scalar then object fields alphabetical for detail view coherence.
- apps/products/admin.py
  - L15: """Dynamically build fieldsets: scalar fields alphabetically, then JSON/object fields."""
  - L29: """Get scalar (non-JSON, non-relation) fields alphabetically."""
  - L31: for field in self.model._meta.fields:
  - L40: """Get JSON and relation fields alphabetically."""
  - L42: for field in self.model._meta.fields:
  - L52: fieldsets = []
  - L54: fieldsets.append((self.scalar_fieldset_title, {"fields": scalar_fields}))
  - L56: fieldsets.append((self.object_fieldset_title, {"fields": object_fields, "classes": ("collapse",)}))
  - L57: if fieldsets:
  - L58: return tuple(fieldsets)
  - L64: list_display = ("id", "ida", "name", "sku", "description", "kind", "on_hand", "on_p", "on_so", "on_in", "on_po", "allocated", "available", "is_active", "dt_created")
  - L66: search_fields = ("ida", "name", "sku", "description")
  - L67: readonly_fields = ("uuid", "dt_created", "dt_modified")
  - L72: list_display = ("id", "ida", "is_active", "dt_created")
  - L74: search_fields = ("ida", "description")
  - L79: list_display = ("id", "ida", "is_active", "dt_created")
  - L81: search_fields = ("ida", "description")
  - L86: list_display = ("id", "ida", "description", "is_active", "dt_created")
  - L88: search_fields = ("ida", "description")
  - L93: list_display = ("id", "ida", "description", "is_active", "dt_created")
- apps/transactions/admin.py
  - L68: """Display computed fields from JSON item and quantity fields for line models."""
  - L102: """Group JSON-heavy fields at the end of the admin form."""
  - L127: for field in self.model._meta.fields:
  - L136: fieldsets: list[tuple[str, dict]] = []
  - L138: fieldsets.append((self.details_fieldset_title, {"fields": detail_fields}))
  - L140: fieldsets.append((self.jsonb_fieldset_title, {"fields": json_fields}))
  - L141: if fieldsets:
  - L142: return tuple(fieldsets)
  - L156: list_display = ("id", "ida", "status", "customer", "totals_total", "totals_cost", "totals_margin_pc", "totals_balance", "priority", "is_active", "date_created")
  - L158: search_fields = ("id", "ida")
  - L163: list_display = ("id", "ida", "invoice", "qty_staged", "item_ida_item", "item_description", "status", "is_active", "date_created")
  - L165: search_fields = ("id", "ida")
  - L178: list_display = ("id", "ida", "workorder", "qty_staged", "item_ida_item", "item_description", "status", "is_active", "date_created")
  - L180: search_fields = ("id", "ida")
  - L237: list_display = ("id", "ida", "status", "customer", "totals_total", "totals_cost", "totals_margin_pc", "totals_balance", "priority", "is_active", "date_created")
  - L239: search_fields = ("id", "ida")
  - L244: list_display = ("id", "ida", "order", "qty_staged", "item_ida_item", "item_description", "status", "is_active", "date_created")
  - L246: search_fields = ("id", "ida")
  - L251: list_display = ("id", "ida", "status", "vendor", "totals_total", "totals_cost", "totals_margin_pc", "totals_balance", "priority", "is_active", "date_created")
  - L253: search_fields = ("id", "ida")
- Recommended list display: ida, name
- Recommended detail order (all fields): base_uom, description, dt_created, dt_modified, health_rating, id, ida, is_active, is_archived, is_deleted, is_locked, kind, name, qr_code, row_version, security_level, sku, specification_id, uom, uuid, version, actions, catalog, comments, cost, flags, gls, metadata, prefs, price, quantity, refs, stats, tax_code
- Scalar fields (alphabetical): base_uom, description, dt_created, dt_modified, health_rating, id, ida, is_active, is_archived, is_deleted, is_locked, kind, name, qr_code, row_version, security_level, sku, specification_id, uom, uuid, version
- JSONB fields (alphabetical): actions, catalog, comments, cost, flags, gls, metadata, prefs, price, quantity, refs, stats, tax_code

### order
- apps/transactions/admin.py
  - L68: """Display computed fields from JSON item and quantity fields for line models."""
  - L102: """Group JSON-heavy fields at the end of the admin form."""
  - L127: for field in self.model._meta.fields:
  - L136: fieldsets: list[tuple[str, dict]] = []
  - L138: fieldsets.append((self.details_fieldset_title, {"fields": detail_fields}))
  - L140: fieldsets.append((self.jsonb_fieldset_title, {"fields": json_fields}))
  - L141: if fieldsets:
  - L142: return tuple(fieldsets)
  - L156: list_display = ("id", "ida", "status", "customer", "totals_total", "totals_cost", "totals_margin_pc", "totals_balance", "priority", "is_active", "date_created")
  - L158: search_fields = ("id", "ida")
  - L163: list_display = ("id", "ida", "invoice", "qty_staged", "item_ida_item", "item_description", "status", "is_active", "date_created")
  - L165: search_fields = ("id", "ida")
  - L178: list_display = ("id", "ida", "workorder", "qty_staged", "item_ida_item", "item_description", "status", "is_active", "date_created")
  - L180: search_fields = ("id", "ida")
  - L237: list_display = ("id", "ida", "status", "customer", "totals_total", "totals_cost", "totals_margin_pc", "totals_balance", "priority", "is_active", "date_created")
  - L239: search_fields = ("id", "ida")
  - L244: list_display = ("id", "ida", "order", "qty_staged", "item_ida_item", "item_description", "status", "is_active", "date_created")
  - L246: search_fields = ("id", "ida")
  - L251: list_display = ("id", "ida", "status", "vendor", "totals_total", "totals_cost", "totals_margin_pc", "totals_balance", "priority", "is_active", "date_created")
  - L253: search_fields = ("id", "ida")
- Recommended list display: ida, status
- Recommended detail order (all fields): address_full, attention, balance, conditions_description, conditions_id, contact_id, customer_id, dt_created, dt_modified, email, health_rating, id, ida, is_active, is_archived, is_commission, is_deleted, is_locked, line_increment, manufacturer_id, parent_id, parent_model, phone, price_level, priority, security_level, status, terms, terms_fk_id, total, uuid, vendor_id, version, actions, comments, cost, finance, flow, metadata, prefs, refs, sell, source, totals
- Scalar fields (alphabetical): address_full, attention, balance, conditions_description, conditions_id, contact_id, customer_id, dt_created, dt_modified, email, health_rating, id, ida, is_active, is_archived, is_commission, is_deleted, is_locked, line_increment, manufacturer_id, parent_id, parent_model, phone, price_level, priority, security_level, status, terms, terms_fk_id, total, uuid, vendor_id, version
- JSONB fields (alphabetical): actions, comments, cost, finance, flow, metadata, prefs, refs, sell, source, totals

### invoice
- apps/transactions/admin.py
  - L68: """Display computed fields from JSON item and quantity fields for line models."""
  - L102: """Group JSON-heavy fields at the end of the admin form."""
  - L127: for field in self.model._meta.fields:
  - L136: fieldsets: list[tuple[str, dict]] = []
  - L138: fieldsets.append((self.details_fieldset_title, {"fields": detail_fields}))
  - L140: fieldsets.append((self.jsonb_fieldset_title, {"fields": json_fields}))
  - L141: if fieldsets:
  - L142: return tuple(fieldsets)
  - L156: list_display = ("id", "ida", "status", "customer", "totals_total", "totals_cost", "totals_margin_pc", "totals_balance", "priority", "is_active", "date_created")
  - L158: search_fields = ("id", "ida")
  - L163: list_display = ("id", "ida", "invoice", "qty_staged", "item_ida_item", "item_description", "status", "is_active", "date_created")
  - L165: search_fields = ("id", "ida")
  - L178: list_display = ("id", "ida", "workorder", "qty_staged", "item_ida_item", "item_description", "status", "is_active", "date_created")
  - L180: search_fields = ("id", "ida")
  - L237: list_display = ("id", "ida", "status", "customer", "totals_total", "totals_cost", "totals_margin_pc", "totals_balance", "priority", "is_active", "date_created")
  - L239: search_fields = ("id", "ida")
  - L244: list_display = ("id", "ida", "order", "qty_staged", "item_ida_item", "item_description", "status", "is_active", "date_created")
  - L246: search_fields = ("id", "ida")
  - L251: list_display = ("id", "ida", "status", "vendor", "totals_total", "totals_cost", "totals_margin_pc", "totals_balance", "priority", "is_active", "date_created")
  - L253: search_fields = ("id", "ida")
- Recommended list display: ida, status
- Recommended detail order (all fields): address_full, attention, balance, conditions_description, conditions_id, contact_id, customer_id, dt_created, dt_modified, email, health_rating, id, ida, is_active, is_archived, is_commission, is_deleted, is_locked, line_increment, manufacturer_id, parent_id, parent_model, phone, price_level, priority, security_level, status, terms, terms_fk_id, total, uuid, vendor_id, version, actions, comments, cost, finance, flow, metadata, prefs, refs, sell, source, totals
- Scalar fields (alphabetical): address_full, attention, balance, conditions_description, conditions_id, contact_id, customer_id, dt_created, dt_modified, email, health_rating, id, ida, is_active, is_archived, is_commission, is_deleted, is_locked, line_increment, manufacturer_id, parent_id, parent_model, phone, price_level, priority, security_level, status, terms, terms_fk_id, total, uuid, vendor_id, version
- JSONB fields (alphabetical): actions, comments, cost, finance, flow, metadata, prefs, refs, sell, source, totals

### document
- apps/docs/admin.py
  - L9: # Scalar fields alphabetically for list display
  - L34: # Object/JSON fields alphabetically
  - L47: list_display = ('id', 'name', 'status', 'model_name', 'mime_type', 'size_bytes', 'dt_created')
  - L49: search_fields = ('name', 'slug', 'description')
  - L50: readonly_fields = ('uuid', 'dt_created', 'dt_modified', 'search_vector')
  - L53: fieldsets = (
  - L54: ('Identification', {'fields': ('id', 'ida', 'uuid', 'name', 'slug')}),
  - L55: ('Status & Classification', {'fields': ('status', 'model_name', 'confidential', 'security_level')}),
  - L56: ('File Info', {'fields': ('mime_type', 'size_bytes', 'checksum', 'path')}),
  - L57: ('Content', {'fields': ('description', 'body', 'comment', 'data', 'copyright')}),
  - L58: ('Counters & Sequence', {'fields': ('count_accessed', 'sequence', 'retention_period')}),
  - L59: ('Lifecycle', {'fields': ('is_active', 'is_deleted', 'is_archived', 'version')}),
  - L60: ('Timestamps', {'fields': ('dt_created', 'dt_modified')}),
  - L61: ('Extended Data', {'fields': ('refs', 'prefs', 'metadata', 'actions', 'comments'), 'classes': ('collapse',)}),
  - L68: # Scalar fields alphabetically for list display
  - L88: # Object/JSON/Text fields alphabetically
  - L100: list_display = ('id', 'question', 'answer', 'parent_model', 'parent_id', 'status', 'sequence', 'dt_created')
  - L102: search_fields = ('question', 'answer', 'parent_model')
  - L103: readonly_fields = ('uuid', 'dt_created', 'dt_modified', 'search_vector')
  - L107: fieldsets = (
- Recommended list display: ida, name
- Recommended detail order (all fields): body, checksum, comment, confidential, count_accessed, description, dt_created, dt_modified, health_rating, id, ida, is_active, is_archived, is_deleted, is_locked, mime_type, model_name, name, retention_period, search_vector, security_level, sequence, size_bytes, slug, status, uuid, version, actions, comments, copyright, data, metadata, path, prefs, refs
- Scalar fields (alphabetical): body, checksum, comment, confidential, count_accessed, description, dt_created, dt_modified, health_rating, id, ida, is_active, is_archived, is_deleted, is_locked, mime_type, model_name, name, retention_period, search_vector, security_level, sequence, size_bytes, slug, status, uuid, version
- JSONB fields (alphabetical): actions, comments, copyright, data, metadata, path, prefs, refs

### contact
- apps/communications/admin.py
  - L12: list_display = ('id', 'address1', 'city', 'country', 'address_type')
  - L14: search_fields = ('address1', 'address2', 'city', 'zip', 'full')
  - L15: readonly_fields = ('full',)
  - L16: fieldsets = (
  - L18: 'fields': ('address1', 'address2', 'address_type', 'city', 'country', 'state', 'zip', 'full')
  - L21: 'fields': ('latitude', 'longitude')
  - L24: 'fields': ('comments', 'instructions', 'refs', 'prefs', 'metadata')
  - L33: list_display = ('id', 'email', 'name', 'contact', 'is_primary', 'is_verified')
  - L35: search_fields = ('email', 'name', 'attention')
  - L36: #readonly_fields = ('uuid', 'status_display')
  - L40: fieldsets = (
  - L42: 'fields': ('email', 'name', 'attention', 'contact')
  - L45: 'fields': ('opt_out', 'is_primary')
  - L48: 'fields': ('comments', 'refs', 'prefs', 'metadata')
  - L56: list_display = ('id', 'number', 'name', 'contact', 'country_code', 'opt_out')  # Changed dt_verified to get_dt_verified
  - L58: search_fields = ('number', 'name', 'attention')
  - L59: #readonly_fields = ('uuid')  # Add get_dt_verified
  - L60: fieldsets = (
  - L62: 'fields': ('number', 'country_code', 'format', 'name', 'attention', 'opt_out', 'contact')
  - L65: 'fields': ('comments', 'refs', 'prefs', 'metadata')
- apps/core/admin.py
  - L47: list_display = scalar_fields
  - L49: search_fields = ('email', 'name_first', 'name_last', 'company')
  - L50: readonly_fields = ('id', 'uuid', 'ida', 'dt_created', 'dt_modified', 'dt_joined', 'version')
  - L64: # Specify the fields to be used in displaying the User model
  - L65: # These are the fields that inherit from BaseUserAdmin but we override for our Contact model
  - L69: 'fields': ('email', 'password1', 'password2'),
  - L73: 'fields': ('name_first', 'name_last', 'name_middle', 'name_prefix', 'name_suffix'),
  - L77: 'fields': (
  - L91: 'fields': ('role', 'is_active', 'is_staff'),
  - L95: fieldsets = (
  - L96: (None, {'fields': ('email', 'password')}),
  - L97: ('Scalar fields', {'fields': (
  - L106: ('JSONB fields', {
  - L107: 'fields': ('actions', 'comment', 'comments', 'groups', 'metadata', 'prefs', 'refs', 'user_permissions'),
  - L111: 'fields': ('id', 'uuid', 'ida', 'dt_created', 'dt_modified', 'dt_joined', 'version'),
  - L116: # Override the get_fieldsets method to use our custom fieldsets
  - L138: list_display = ('id', 'get_action_title', 'project_id', 'project_name', 'kanban_column', 'status', 'priority', 'dt_deadline')
  - L140: search_fields = ('project_id', 'action')
  - L141: readonly_fields = ('uuid', 'dt_created', 'dt_modified')
  - L142: # Keep scalar then object fields alphabetical for detail view coherence.
- apps/orgs/admin.py
  - L13: """Custom form to make JSON aspect fields optional."""
  - L17: fields = '__all__'
  - L22: # Make all JSON aspect fields optional (alphabetical)
  - L30: if field_name in self.fields:
  - L31: self.fields[field_name].required = False
  - L35: if 'org_type' in self.fields:
  - L36: self.fields['org_type'].widget = forms.HiddenInput()
  - L37: elif 'org_type' in self.fields:
  - L39: self.fields['org_type'].required = False
  - L51: list_display = ("id", "company", "primary_org_badge", "org_type", "status", "is_active", "version")
  - L53: search_fields = ("display_name", "domains", "contacts", "email", "phone")
  - L54: readonly_fields = ("id", "uuid", "ida", "dt_created", "dt_modified", "version")
  - L58: # Scalar fields alphabetical, then JSONB fields alphabetical
  - L59: fieldsets = (
  - L60: ("Scalar fields", {"fields": (
  - L68: ("JSONB fields", {
  - L69: "fields": (
  - L78: "fields": ("id", "uuid", "ida", "dt_created", "dt_modified", "version"),
- apps/transactions/admin.py
  - L68: """Display computed fields from JSON item and quantity fields for line models."""
  - L102: """Group JSON-heavy fields at the end of the admin form."""
  - L127: for field in self.model._meta.fields:
  - L136: fieldsets: list[tuple[str, dict]] = []
  - L138: fieldsets.append((self.details_fieldset_title, {"fields": detail_fields}))
  - L140: fieldsets.append((self.jsonb_fieldset_title, {"fields": json_fields}))
  - L141: if fieldsets:
  - L142: return tuple(fieldsets)
  - L156: list_display = ("id", "ida", "status", "customer", "totals_total", "totals_cost", "totals_margin_pc", "totals_balance", "priority", "is_active", "date_created")
  - L158: search_fields = ("id", "ida")
  - L163: list_display = ("id", "ida", "invoice", "qty_staged", "item_ida_item", "item_description", "status", "is_active", "date_created")
  - L165: search_fields = ("id", "ida")
  - L178: list_display = ("id", "ida", "workorder", "qty_staged", "item_ida_item", "item_description", "status", "is_active", "date_created")
  - L180: search_fields = ("id", "ida")
  - L237: list_display = ("id", "ida", "status", "customer", "totals_total", "totals_cost", "totals_margin_pc", "totals_balance", "priority", "is_active", "date_created")
  - L239: search_fields = ("id", "ida")
  - L244: list_display = ("id", "ida", "order", "qty_staged", "item_ida_item", "item_description", "status", "is_active", "date_created")
  - L246: search_fields = ("id", "ida")
  - L251: list_display = ("id", "ida", "status", "vendor", "totals_total", "totals_cost", "totals_margin_pc", "totals_balance", "priority", "is_active", "date_created")
  - L253: search_fields = ("id", "ida")
- Recommended list display: ida, company
- Recommended detail order (all fields): address_full, address_id, attention, comment, company, customer_id, department, domain, domain_id, dt_created, dt_joined, dt_modified, email, email_id, employee_id, groups, health_rating, id, ida, is_active, is_archived, is_deleted, is_locked, is_staff, is_superuser, last_login, manufacturer_id, name_first, name_last, name_middle, name_prefix, name_suffix, other_id, password, phone, phone_id, rep_id, role, security_level, title, user_permissions, uuid, vendor_id, version, actions, comments, metadata, prefs, refs
- Scalar fields (alphabetical): address_full, address_id, attention, comment, company, customer_id, department, domain, domain_id, dt_created, dt_joined, dt_modified, email, email_id, employee_id, groups, health_rating, id, ida, is_active, is_archived, is_deleted, is_locked, is_staff, is_superuser, last_login, manufacturer_id, name_first, name_last, name_middle, name_prefix, name_suffix, other_id, password, phone, phone_id, rep_id, role, security_level, title, user_permissions, uuid, vendor_id, version
- JSONB fields (alphabetical): actions, comments, metadata, prefs, refs

### payment
- apps/transactions/admin.py
  - L68: """Display computed fields from JSON item and quantity fields for line models."""
  - L102: """Group JSON-heavy fields at the end of the admin form."""
  - L127: for field in self.model._meta.fields:
  - L136: fieldsets: list[tuple[str, dict]] = []
  - L138: fieldsets.append((self.details_fieldset_title, {"fields": detail_fields}))
  - L140: fieldsets.append((self.jsonb_fieldset_title, {"fields": json_fields}))
  - L141: if fieldsets:
  - L142: return tuple(fieldsets)
  - L156: list_display = ("id", "ida", "status", "customer", "totals_total", "totals_cost", "totals_margin_pc", "totals_balance", "priority", "is_active", "date_created")
  - L158: search_fields = ("id", "ida")
  - L163: list_display = ("id", "ida", "invoice", "qty_staged", "item_ida_item", "item_description", "status", "is_active", "date_created")
  - L165: search_fields = ("id", "ida")
  - L178: list_display = ("id", "ida", "workorder", "qty_staged", "item_ida_item", "item_description", "status", "is_active", "date_created")
  - L180: search_fields = ("id", "ida")
  - L237: list_display = ("id", "ida", "status", "customer", "totals_total", "totals_cost", "totals_margin_pc", "totals_balance", "priority", "is_active", "date_created")
  - L239: search_fields = ("id", "ida")
  - L244: list_display = ("id", "ida", "order", "qty_staged", "item_ida_item", "item_description", "status", "is_active", "date_created")
  - L246: search_fields = ("id", "ida")
  - L251: list_display = ("id", "ida", "status", "vendor", "totals_total", "totals_cost", "totals_margin_pc", "totals_balance", "priority", "is_active", "date_created")
  - L253: search_fields = ("id", "ida")
- Recommended list display: ida, status
- Recommended detail order (all fields): amount, contact_id, dt_created, dt_modified, dt_payment, dt_processed, dt_reconciliation, fee_amount, gateway, health_rating, id, id_gateway_payment_intent, id_gateway_transaction, ida, invoice_id, is_active, is_archived, is_deleted, is_locked, notes, payment_method_id, payment_term_id, reconciled, reference_number, security_level, status, uuid, version, actions, comments, gateway_response, metadata, prefs, refs
- Scalar fields (alphabetical): amount, contact_id, dt_created, dt_modified, dt_payment, dt_processed, dt_reconciliation, fee_amount, gateway, health_rating, id, id_gateway_payment_intent, id_gateway_transaction, ida, invoice_id, is_active, is_archived, is_deleted, is_locked, notes, payment_method_id, payment_term_id, reconciled, reference_number, security_level, status, uuid, version
- JSONB fields (alphabetical): actions, comments, gateway_response, metadata, prefs, refs

### customer
- apps/core/admin.py
  - L47: list_display = scalar_fields
  - L49: search_fields = ('email', 'name_first', 'name_last', 'company')
  - L50: readonly_fields = ('id', 'uuid', 'ida', 'dt_created', 'dt_modified', 'dt_joined', 'version')
  - L64: # Specify the fields to be used in displaying the User model
  - L65: # These are the fields that inherit from BaseUserAdmin but we override for our Contact model
  - L69: 'fields': ('email', 'password1', 'password2'),
  - L73: 'fields': ('name_first', 'name_last', 'name_middle', 'name_prefix', 'name_suffix'),
  - L77: 'fields': (
  - L91: 'fields': ('role', 'is_active', 'is_staff'),
  - L95: fieldsets = (
  - L96: (None, {'fields': ('email', 'password')}),
  - L97: ('Scalar fields', {'fields': (
  - L106: ('JSONB fields', {
  - L107: 'fields': ('actions', 'comment', 'comments', 'groups', 'metadata', 'prefs', 'refs', 'user_permissions'),
  - L111: 'fields': ('id', 'uuid', 'ida', 'dt_created', 'dt_modified', 'dt_joined', 'version'),
  - L116: # Override the get_fieldsets method to use our custom fieldsets
  - L138: list_display = ('id', 'get_action_title', 'project_id', 'project_name', 'kanban_column', 'status', 'priority', 'dt_deadline')
  - L140: search_fields = ('project_id', 'action')
  - L141: readonly_fields = ('uuid', 'dt_created', 'dt_modified')
  - L142: # Keep scalar then object fields alphabetical for detail view coherence.
- apps/orgs/admin.py
  - L13: """Custom form to make JSON aspect fields optional."""
  - L17: fields = '__all__'
  - L22: # Make all JSON aspect fields optional (alphabetical)
  - L30: if field_name in self.fields:
  - L31: self.fields[field_name].required = False
  - L35: if 'org_type' in self.fields:
  - L36: self.fields['org_type'].widget = forms.HiddenInput()
  - L37: elif 'org_type' in self.fields:
  - L39: self.fields['org_type'].required = False
  - L51: list_display = ("id", "company", "primary_org_badge", "org_type", "status", "is_active", "version")
  - L53: search_fields = ("display_name", "domains", "contacts", "email", "phone")
  - L54: readonly_fields = ("id", "uuid", "ida", "dt_created", "dt_modified", "version")
  - L58: # Scalar fields alphabetical, then JSONB fields alphabetical
  - L59: fieldsets = (
  - L60: ("Scalar fields", {"fields": (
  - L68: ("JSONB fields", {
  - L69: "fields": (
  - L78: "fields": ("id", "uuid", "ida", "dt_created", "dt_modified", "version"),
- apps/transactions/admin.py
  - L68: """Display computed fields from JSON item and quantity fields for line models."""
  - L102: """Group JSON-heavy fields at the end of the admin form."""
  - L127: for field in self.model._meta.fields:
  - L136: fieldsets: list[tuple[str, dict]] = []
  - L138: fieldsets.append((self.details_fieldset_title, {"fields": detail_fields}))
  - L140: fieldsets.append((self.jsonb_fieldset_title, {"fields": json_fields}))
  - L141: if fieldsets:
  - L142: return tuple(fieldsets)
  - L156: list_display = ("id", "ida", "status", "customer", "totals_total", "totals_cost", "totals_margin_pc", "totals_balance", "priority", "is_active", "date_created")
  - L158: search_fields = ("id", "ida")
  - L163: list_display = ("id", "ida", "invoice", "qty_staged", "item_ida_item", "item_description", "status", "is_active", "date_created")
  - L165: search_fields = ("id", "ida")
  - L178: list_display = ("id", "ida", "workorder", "qty_staged", "item_ida_item", "item_description", "status", "is_active", "date_created")
  - L180: search_fields = ("id", "ida")
  - L237: list_display = ("id", "ida", "status", "customer", "totals_total", "totals_cost", "totals_margin_pc", "totals_balance", "priority", "is_active", "date_created")
  - L239: search_fields = ("id", "ida")
  - L244: list_display = ("id", "ida", "order", "qty_staged", "item_ida_item", "item_description", "status", "is_active", "date_created")
  - L246: search_fields = ("id", "ida")
  - L251: list_display = ("id", "ida", "status", "vendor", "totals_total", "totals_cost", "totals_margin_pc", "totals_balance", "priority", "is_active", "date_created")
  - L253: search_fields = ("id", "ida")
- Recommended list display: ida, display_name
- Recommended detail order (all fields): address_full, address_id, attention, contact_id, display_name, domain, domain_id, dt_created, dt_modified, email, email_id, health_rating, id, ida, is_active, is_archived, is_deleted, is_locked, org_type, phone, phone_id, price_level, security_level, status, terms, terms_fk_id, uuid, version, actions, addresses, comments, connections, contacts, data, docs, domains, emails, financial, gl_accounts, metadata, metrics, phones, prefs, refs, relations, relationship_stats, stats
- Scalar fields (alphabetical): address_full, address_id, attention, contact_id, display_name, domain, domain_id, dt_created, dt_modified, email, email_id, health_rating, id, ida, is_active, is_archived, is_deleted, is_locked, org_type, phone, phone_id, price_level, security_level, status, terms, terms_fk_id, uuid, version
- JSONB fields (alphabetical): actions, addresses, comments, connections, contacts, data, docs, domains, emails, financial, gl_accounts, metadata, metrics, phones, prefs, refs, relations, relationship_stats, stats

### vendor
- apps/core/admin.py
  - L47: list_display = scalar_fields
  - L49: search_fields = ('email', 'name_first', 'name_last', 'company')
  - L50: readonly_fields = ('id', 'uuid', 'ida', 'dt_created', 'dt_modified', 'dt_joined', 'version')
  - L64: # Specify the fields to be used in displaying the User model
  - L65: # These are the fields that inherit from BaseUserAdmin but we override for our Contact model
  - L69: 'fields': ('email', 'password1', 'password2'),
  - L73: 'fields': ('name_first', 'name_last', 'name_middle', 'name_prefix', 'name_suffix'),
  - L77: 'fields': (
  - L91: 'fields': ('role', 'is_active', 'is_staff'),
  - L95: fieldsets = (
  - L96: (None, {'fields': ('email', 'password')}),
  - L97: ('Scalar fields', {'fields': (
  - L106: ('JSONB fields', {
  - L107: 'fields': ('actions', 'comment', 'comments', 'groups', 'metadata', 'prefs', 'refs', 'user_permissions'),
  - L111: 'fields': ('id', 'uuid', 'ida', 'dt_created', 'dt_modified', 'dt_joined', 'version'),
  - L116: # Override the get_fieldsets method to use our custom fieldsets
  - L138: list_display = ('id', 'get_action_title', 'project_id', 'project_name', 'kanban_column', 'status', 'priority', 'dt_deadline')
  - L140: search_fields = ('project_id', 'action')
  - L141: readonly_fields = ('uuid', 'dt_created', 'dt_modified')
  - L142: # Keep scalar then object fields alphabetical for detail view coherence.
- apps/orgs/admin.py
  - L13: """Custom form to make JSON aspect fields optional."""
  - L17: fields = '__all__'
  - L22: # Make all JSON aspect fields optional (alphabetical)
  - L30: if field_name in self.fields:
  - L31: self.fields[field_name].required = False
  - L35: if 'org_type' in self.fields:
  - L36: self.fields['org_type'].widget = forms.HiddenInput()
  - L37: elif 'org_type' in self.fields:
  - L39: self.fields['org_type'].required = False
  - L51: list_display = ("id", "company", "primary_org_badge", "org_type", "status", "is_active", "version")
  - L53: search_fields = ("display_name", "domains", "contacts", "email", "phone")
  - L54: readonly_fields = ("id", "uuid", "ida", "dt_created", "dt_modified", "version")
  - L58: # Scalar fields alphabetical, then JSONB fields alphabetical
  - L59: fieldsets = (
  - L60: ("Scalar fields", {"fields": (
  - L68: ("JSONB fields", {
  - L69: "fields": (
  - L78: "fields": ("id", "uuid", "ida", "dt_created", "dt_modified", "version"),
- apps/transactions/admin.py
  - L68: """Display computed fields from JSON item and quantity fields for line models."""
  - L102: """Group JSON-heavy fields at the end of the admin form."""
  - L127: for field in self.model._meta.fields:
  - L136: fieldsets: list[tuple[str, dict]] = []
  - L138: fieldsets.append((self.details_fieldset_title, {"fields": detail_fields}))
  - L140: fieldsets.append((self.jsonb_fieldset_title, {"fields": json_fields}))
  - L141: if fieldsets:
  - L142: return tuple(fieldsets)
  - L156: list_display = ("id", "ida", "status", "customer", "totals_total", "totals_cost", "totals_margin_pc", "totals_balance", "priority", "is_active", "date_created")
  - L158: search_fields = ("id", "ida")
  - L163: list_display = ("id", "ida", "invoice", "qty_staged", "item_ida_item", "item_description", "status", "is_active", "date_created")
  - L165: search_fields = ("id", "ida")
  - L178: list_display = ("id", "ida", "workorder", "qty_staged", "item_ida_item", "item_description", "status", "is_active", "date_created")
  - L180: search_fields = ("id", "ida")
  - L237: list_display = ("id", "ida", "status", "customer", "totals_total", "totals_cost", "totals_margin_pc", "totals_balance", "priority", "is_active", "date_created")
  - L239: search_fields = ("id", "ida")
  - L244: list_display = ("id", "ida", "order", "qty_staged", "item_ida_item", "item_description", "status", "is_active", "date_created")
  - L246: search_fields = ("id", "ida")
  - L251: list_display = ("id", "ida", "status", "vendor", "totals_total", "totals_cost", "totals_margin_pc", "totals_balance", "priority", "is_active", "date_created")
  - L253: search_fields = ("id", "ida")
- Recommended list display: ida, display_name
- Recommended detail order (all fields): address_full, address_id, attention, contact_id, display_name, domain, domain_id, dt_created, dt_modified, email, email_id, health_rating, id, ida, is_active, is_archived, is_deleted, is_locked, org_type, phone, phone_id, price_level, security_level, status, terms, terms_fk_id, uuid, version, actions, addresses, comments, connections, contacts, data, docs, domains, emails, financial, gl_accounts, metadata, metrics, phones, prefs, refs, relations, relationship_stats, stats
- Scalar fields (alphabetical): address_full, address_id, attention, contact_id, display_name, domain, domain_id, dt_created, dt_modified, email, email_id, health_rating, id, ida, is_active, is_archived, is_deleted, is_locked, org_type, phone, phone_id, price_level, security_level, status, terms, terms_fk_id, uuid, version
- JSONB fields (alphabetical): actions, addresses, comments, connections, contacts, data, docs, domains, emails, financial, gl_accounts, metadata, metrics, phones, prefs, refs, relations, relationship_stats, stats

### requisition
- apps/transactions/admin.py
  - L68: """Display computed fields from JSON item and quantity fields for line models."""
  - L102: """Group JSON-heavy fields at the end of the admin form."""
  - L127: for field in self.model._meta.fields:
  - L136: fieldsets: list[tuple[str, dict]] = []
  - L138: fieldsets.append((self.details_fieldset_title, {"fields": detail_fields}))
  - L140: fieldsets.append((self.jsonb_fieldset_title, {"fields": json_fields}))
  - L141: if fieldsets:
  - L142: return tuple(fieldsets)
  - L156: list_display = ("id", "ida", "status", "customer", "totals_total", "totals_cost", "totals_margin_pc", "totals_balance", "priority", "is_active", "date_created")
  - L158: search_fields = ("id", "ida")
  - L163: list_display = ("id", "ida", "invoice", "qty_staged", "item_ida_item", "item_description", "status", "is_active", "date_created")
  - L165: search_fields = ("id", "ida")
  - L178: list_display = ("id", "ida", "workorder", "qty_staged", "item_ida_item", "item_description", "status", "is_active", "date_created")
  - L180: search_fields = ("id", "ida")
  - L237: list_display = ("id", "ida", "status", "customer", "totals_total", "totals_cost", "totals_margin_pc", "totals_balance", "priority", "is_active", "date_created")
  - L239: search_fields = ("id", "ida")
  - L244: list_display = ("id", "ida", "order", "qty_staged", "item_ida_item", "item_description", "status", "is_active", "date_created")
  - L246: search_fields = ("id", "ida")
  - L251: list_display = ("id", "ida", "status", "vendor", "totals_total", "totals_cost", "totals_margin_pc", "totals_balance", "priority", "is_active", "date_created")
  - L253: search_fields = ("id", "ida")
- Recommended list display: ida, name
- Recommended detail order (all fields): dt_created, dt_modified, health_rating, id, ida, is_active, is_archived, is_deleted, is_locked, name, purpose, security_level, status, uuid, version, actions, comments, metadata, prefs, refs
- Scalar fields (alphabetical): dt_created, dt_modified, health_rating, id, ida, is_active, is_archived, is_deleted, is_locked, name, purpose, security_level, status, uuid, version
- JSONB fields (alphabetical): actions, comments, metadata, prefs, refs

### audit
- apps/accounts/admin.py
  - L11: list_display = ("id", "account_number", "name", "type", "category", "division", "used_for", "account_debit", "account_credit")
  - L13: search_fields = ("account_number", "name")
  - L18: list_display = ("code", "name", "precision", "is_active")
  - L20: search_fields = ("code", "name")
  - L25: list_display = ("currency_base", "currency_target", "rate", "dt_start", "dt_end", "is_active")
  - L27: search_fields = ("currency_base", "currency_target")
  - L32: list_display = ("name", "currency_base", "currency_target", "rate", "dt_start", "dt_end", "is_active")
  - L34: search_fields = ("name", "currency_base", "currency_target")
  - L39: list_display = ("name", "days_due", "days_discount", "discount_rate", "day_cut_off_due", "day_cut_off_invoice")
  - L41: search_fields = ("name", "description")
  - L46: list_display = ("id", "source", "model_name", "value_original", "value_available", "is_settled", "is_void", "dt_posted", "is_active")
  - L48: search_fields = ("ida",)
  - L49: readonly_fields = ("uuid", "dt_created", "dt_modified")
  - L54: list_display = ("id", "tax_jurisdiction", "tax_name", "service_provider", "tax_rate_sales", "tax_rate_cost", "is_active")
  - L56: search_fields = ("tax_jurisdiction", "tax_name", "gl_account_payable")
  - L57: readonly_fields = ("uuid", "dt_created", "dt_modified")
  - L62: list_display = ("id", "account", "debit", "credit", "source", "type", "is_active", "dt_created")
  - L64: search_fields = ("account", "ida")
  - L65: readonly_fields = ("uuid", "dt_created", "dt_modified")
  - L70: list_display = ("id", "name", "purpose", "rating", "priority", "is_completed", "is_active", "dt_created")
- Recommended list display: ida, name
- Recommended detail order (all fields): dt_created, dt_modified, health_rating, id, ida, is_active, is_archived, is_completed, is_deleted, is_locked, name, priority, purpose, rating, security_level, uuid, version, actions, changes, comments, conflicts, metadata, prefs, recommendations, refs
- Scalar fields (alphabetical): dt_created, dt_modified, health_rating, id, ida, is_active, is_archived, is_completed, is_deleted, is_locked, name, priority, purpose, rating, security_level, uuid, version
- JSONB fields (alphabetical): actions, changes, comments, conflicts, metadata, prefs, recommendations, refs

### report
- apps/core/admin.py
  - L47: list_display = scalar_fields
  - L49: search_fields = ('email', 'name_first', 'name_last', 'company')
  - L50: readonly_fields = ('id', 'uuid', 'ida', 'dt_created', 'dt_modified', 'dt_joined', 'version')
  - L64: # Specify the fields to be used in displaying the User model
  - L65: # These are the fields that inherit from BaseUserAdmin but we override for our Contact model
  - L69: 'fields': ('email', 'password1', 'password2'),
  - L73: 'fields': ('name_first', 'name_last', 'name_middle', 'name_prefix', 'name_suffix'),
  - L77: 'fields': (
  - L91: 'fields': ('role', 'is_active', 'is_staff'),
  - L95: fieldsets = (
  - L96: (None, {'fields': ('email', 'password')}),
  - L97: ('Scalar fields', {'fields': (
  - L106: ('JSONB fields', {
  - L107: 'fields': ('actions', 'comment', 'comments', 'groups', 'metadata', 'prefs', 'refs', 'user_permissions'),
  - L111: 'fields': ('id', 'uuid', 'ida', 'dt_created', 'dt_modified', 'dt_joined', 'version'),
  - L116: # Override the get_fieldsets method to use our custom fieldsets
  - L138: list_display = ('id', 'get_action_title', 'project_id', 'project_name', 'kanban_column', 'status', 'priority', 'dt_deadline')
  - L140: search_fields = ('project_id', 'action')
  - L141: readonly_fields = ('uuid', 'dt_created', 'dt_modified')
  - L142: # Keep scalar then object fields alphabetical for detail view coherence.
- Recommended list display: ida, name
- Recommended detail order (all fields): category, description, dt_created, dt_modified, health_rating, id, ida, is_active, is_archived, is_deleted, is_locked, model_name, name, output_type, purpose, record_id, role_required, security_level, sort_order, uuid, version, actions, comments, data, metadata, prefs, refs
- Scalar fields (alphabetical): category, description, dt_created, dt_modified, health_rating, id, ida, is_active, is_archived, is_deleted, is_locked, model_name, name, output_type, purpose, record_id, role_required, security_level, sort_order, uuid, version
- JSONB fields (alphabetical): actions, comments, data, metadata, prefs, refs

### connection
- apps/sync/admin.py
  - L13: list_display = ("id", "name", "type", "status")
  - L14: search_fields = ("name", "type")
  - L15: readonly_fields = ()
  - L20: list_display = ("id", "connection_link", "direction", "status", "duration")
  - L21: search_fields = ("id", "status", "direction")
- Recommended list display: ida, name
- Recommended detail order (all fields): action, comment, dt_created, dt_modified, health_rating, id, ida, is_active, is_archived, is_deleted, is_locked, name, purpose, security_level, status, type, uuid, version, actions, changes, comments, config, conflicts, encryption, maps, metadata, prefs, refs, relationships, rules, scripts
- Scalar fields (alphabetical): action, comment, dt_created, dt_modified, health_rating, id, ida, is_active, is_archived, is_deleted, is_locked, name, purpose, security_level, status, type, uuid, version
- JSONB fields (alphabetical): actions, changes, comments, config, conflicts, encryption, maps, metadata, prefs, refs, relationships, rules, scripts

## User Overrides
<!-- Alice-Instruction: Add alternative instructions below. Example: model=customer; list_display=ida,company; detail_order=company,status,metadata,refs -->
- To provide alternative instructions, add a note via /wcapi/ai/note/ with:
  category=pending, role=config_suggestion, name='Schema report override',
  details={model, list_display, detail_order, rationale}
