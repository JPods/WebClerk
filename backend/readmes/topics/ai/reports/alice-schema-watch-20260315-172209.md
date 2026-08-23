# Alice Schema Watch Report

- Timestamp (UTC): 2026-03-15 17:22:09
- Commit: e82c6eaff02e0302a84bd90056daefef177e865f
- Schema files touched: 2
- Models touched: item, order, invoice, document, contact, payment, customer, vendor, requisition, audit, report, connection
- Drift issues: total=949, high=148, medium=309, low=492

## Schema Files
- apps/core/migrations/0013_alter_setting_purpose.py
- common/models.py

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
  - L48: # Scalar fields: address_full, address_id, attention, comment, company, department, domain, domain_id, dt_created, dt_joined, dt_modified, email, email_id, groups, health_rating, ida, is_active, is_archived, is_deleted, is_locked, is_staff, is_superuser, last_login, name_first, name_last, name_middle, name_prefix, name_suffix, other_id, password, phone, phone_id, role, security_level, title, user_permissions, uuid, version
  - L49: list_display = ("ida", "company", "title", "email", "phone", "address_full", "is_active", "dt_created")
  - L51: search_fields = ('email', 'name_first', 'name_last', 'company')
  - L52: readonly_fields = ('id', 'uuid', 'dt_created', 'dt_modified', 'dt_joined', 'version')
  - L66: # Specify the fields to be used in displaying the User model
  - L67: # These are the fields that inherit from BaseUserAdmin but we override for our Contact model
  - L71: 'fields': ('email', 'password1', 'password2'),
  - L75: 'fields': ('name_first', 'name_last', 'name_middle', 'name_prefix', 'name_suffix'),
  - L79: 'fields': (
  - L93: 'fields': ('role', 'is_active', 'is_staff'),
  - L97: fieldsets = (
  - L98: (None, {'fields': ('email', 'password')}),
  - L99: ('Scalar fields', {'fields': (
  - L108: ('JSONB fields', {
  - L109: 'fields': ('actions', 'comment', 'comments', 'groups', 'metadata', 'prefs', 'refs', 'user_permissions'),
  - L113: 'fields': ('id', 'uuid', 'ida', 'dt_created', 'dt_modified', 'dt_joined', 'version'),
  - L118: # Override the get_fieldsets method to use our custom fieldsets
  - L140: # Scalar fields: burndown, contact_id, difficulty, dt_completed, dt_created, dt_deadline, dt_end_original, dt_expected, dt_modified, dt_start, dt_start_original, dt_updated, duration, health_rating, ida, is_active, is_archived, is_deleted, is_locked, kanban_column, linkage, percent_complete, priority, project_id, project_ida, project_name, security_level, sequence, status, uuid, version
  - L141: list_display = ("ida", "project_name", "priority", "status", "burndown", "kanban_column", "assigned_to_names", "description_en", "contact_id", "difficulty", "dt_completed", "is_active", "dt_created")
  - L143: search_fields = ('project_id', 'action')
- apps/products/admin.py
  - L17: # Scalar fields: base_uom, description, dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, kind, name, qr_code, row_version, security_level, sku, specification_id, uom, uuid, version
  - L18: list_display = ("ida", "name", "sku", "description", "kind", "base_uom", "is_active", "dt_created")
  - L20: search_fields = ("ida", "name", "sku", "description")
  - L21: readonly_fields = ("uuid", "dt_created", "dt_modified")
  - L26: # Scalar fields: dt_created, dt_modified, external_sku, external_uuid, health_rating, is_active, is_archived, is_deleted, is_locked, is_preferred, security_level, source, source_id, source_model_name, source_name, status, uuid, version
  - L27: list_display = ("status", "external_sku", "external_uuid", "health_rating", "is_locked", "is_preferred", "is_active", "dt_created")
  - L29: search_fields = ("ida", "description")
  - L34: # Scalar fields: alternate_group, change_reason, child_description, child_ida, cost_snapshot, dt_created, dt_effective_from, dt_effective_to, dt_last_recalc, dt_modified, health_rating, is_active, is_alternate, is_archived, is_deleted, is_locked, is_optional, parent_description, parent_ida, quantity, revision, scrap_factor, security_level, sequence, uuid, version, yield_pct
  - L35: list_display = ("quantity", "child_ida", "child_description", "parent_ida", "parent_description", "cost_snapshot", "dt_effective_from", "is_active", "dt_created")
  - L37: search_fields = ("ida", "description")
  - L42: # Scalar fields: code, dt_created, dt_modified, health_rating, is_active, is_archived, is_deleted, is_locked, name, priority, security_level, site_code, uuid, version
  - L43: list_display = ("name", "code", "health_rating", "is_locked", "priority", "security_level", "is_active", "dt_created")
  - L45: search_fields = ("ida", "description")
  - L50: # Scalar fields: dt_created, dt_modified, health_rating, is_active, is_archived, is_deleted, is_locked, lot, security_level, serial_batch, source_doc_id, source_doc_type, status, uuid, version
  - L51: list_display = ("status", "health_rating", "is_locked", "lot", "security_level", "serial_batch", "is_active", "dt_created")
  - L53: search_fields = ("ida", "description")
  - L58: # Scalar fields: dt_created, dt_modified, health_rating, is_active, is_archived, is_deleted, is_locked, security_level, site_code, status, uuid, version
  - L59: list_display = ("status", "health_rating", "is_locked", "security_level", "site_code", "is_active", "dt_created")
  - L61: search_fields = ("ida", "description")
  - L66: # Scalar fields: dt_created, dt_modified, health_rating, is_active, is_archived, is_deleted, is_locked, movement_type, quantity, reason, security_level, site_code, source_doc_id, source_doc_type, status, uuid, version
- apps/transactions/admin.py
  - L69: """Display computed fields from JSON item and quantity fields for line models."""
  - L103: """Group JSON-heavy fields at the end of the admin form."""
  - L128: for field in self.model._meta.fields:
  - L137: fieldsets: list[tuple[str, dict]] = []
  - L139: fieldsets.append((self.details_fieldset_title, {"fields": detail_fields}))
  - L141: fieldsets.append((self.jsonb_fieldset_title, {"fields": json_fields}))
  - L142: if fieldsets:
  - L143: return tuple(fieldsets)
  - L157: # Scalar fields: address_full, attention, balance, conditions_description, conditions_id, dt_created, dt_modified, email, health_rating, ida, is_active, is_archived, is_commission, is_deleted, is_locked, line_increment, parent_id, parent_model, phone, price_level, priority, security_level, status, terms, total, uuid, version
  - L158: list_display = ("ida", "status", "email", "phone", "address_full", "attention", "is_active", "dt_created")
  - L160: search_fields = ("id", "ida")
  - L165: # Scalar fields: dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, line_number, price_level, security_level, status, uuid, version
  - L166: list_display = ("ida", "status", "health_rating", "is_locked", "line_number", "price_level", "is_active", "dt_created")
  - L168: search_fields = ("id", "ida")
  - L181: # Scalar fields: dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, line_number, price_level, security_level, status, uuid, version
  - L182: list_display = ("ida", "status", "health_rating", "is_locked", "line_number", "price_level", "is_active", "dt_created")
  - L184: search_fields = ("id", "ida")
  - L241: # Scalar fields: address_full, attention, balance, conditions_description, conditions_id, dt_created, dt_modified, email, health_rating, ida, is_active, is_archived, is_commission, is_deleted, is_locked, line_increment, parent_id, parent_model, phone, price_level, priority, security_level, status, terms, total, uuid, version
  - L242: list_display = ("ida", "status", "email", "phone", "address_full", "attention", "is_active", "dt_created")
  - L244: search_fields = ("id", "ida")
- Recommended list display: ida, name
- Recommended detail order (all fields): base_uom, description, dt_created, dt_modified, health_rating, id, ida, is_active, is_archived, is_deleted, is_locked, kind, name, qr_code, row_version, security_level, sku, specification_id, uom, uuid, version, actions, catalog, comments, cost, flags, gls, metadata, prefs, price, quantity, refs, stats, tax_code
- Scalar fields (alphabetical): base_uom, description, dt_created, dt_modified, health_rating, id, ida, is_active, is_archived, is_deleted, is_locked, kind, name, qr_code, row_version, security_level, sku, specification_id, uom, uuid, version
- JSONB fields (alphabetical): actions, catalog, comments, cost, flags, gls, metadata, prefs, price, quantity, refs, stats, tax_code

### order
- apps/transactions/admin.py
  - L69: """Display computed fields from JSON item and quantity fields for line models."""
  - L103: """Group JSON-heavy fields at the end of the admin form."""
  - L128: for field in self.model._meta.fields:
  - L137: fieldsets: list[tuple[str, dict]] = []
  - L139: fieldsets.append((self.details_fieldset_title, {"fields": detail_fields}))
  - L141: fieldsets.append((self.jsonb_fieldset_title, {"fields": json_fields}))
  - L142: if fieldsets:
  - L143: return tuple(fieldsets)
  - L157: # Scalar fields: address_full, attention, balance, conditions_description, conditions_id, dt_created, dt_modified, email, health_rating, ida, is_active, is_archived, is_commission, is_deleted, is_locked, line_increment, parent_id, parent_model, phone, price_level, priority, security_level, status, terms, total, uuid, version
  - L158: list_display = ("ida", "status", "email", "phone", "address_full", "attention", "is_active", "dt_created")
  - L160: search_fields = ("id", "ida")
  - L165: # Scalar fields: dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, line_number, price_level, security_level, status, uuid, version
  - L166: list_display = ("ida", "status", "health_rating", "is_locked", "line_number", "price_level", "is_active", "dt_created")
  - L168: search_fields = ("id", "ida")
  - L181: # Scalar fields: dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, line_number, price_level, security_level, status, uuid, version
  - L182: list_display = ("ida", "status", "health_rating", "is_locked", "line_number", "price_level", "is_active", "dt_created")
  - L184: search_fields = ("id", "ida")
  - L241: # Scalar fields: address_full, attention, balance, conditions_description, conditions_id, dt_created, dt_modified, email, health_rating, ida, is_active, is_archived, is_commission, is_deleted, is_locked, line_increment, parent_id, parent_model, phone, price_level, priority, security_level, status, terms, total, uuid, version
  - L242: list_display = ("ida", "status", "email", "phone", "address_full", "attention", "is_active", "dt_created")
  - L244: search_fields = ("id", "ida")
- Recommended list display: ida, status
- Recommended detail order (all fields): address_full, attention, balance, conditions_description, conditions_id, contact_id, customer_id, dt_created, dt_modified, email, health_rating, id, ida, is_active, is_archived, is_commission, is_deleted, is_locked, line_increment, manufacturer_id, parent_id, parent_model, phone, price_level, priority, security_level, status, terms, terms_fk_id, total, uuid, vendor_id, version, actions, comments, cost, finance, flow, metadata, prefs, refs, sell, source, totals
- Scalar fields (alphabetical): address_full, attention, balance, conditions_description, conditions_id, contact_id, customer_id, dt_created, dt_modified, email, health_rating, id, ida, is_active, is_archived, is_commission, is_deleted, is_locked, line_increment, manufacturer_id, parent_id, parent_model, phone, price_level, priority, security_level, status, terms, terms_fk_id, total, uuid, vendor_id, version
- JSONB fields (alphabetical): actions, comments, cost, finance, flow, metadata, prefs, refs, sell, source, totals

### invoice
- apps/transactions/admin.py
  - L69: """Display computed fields from JSON item and quantity fields for line models."""
  - L103: """Group JSON-heavy fields at the end of the admin form."""
  - L128: for field in self.model._meta.fields:
  - L137: fieldsets: list[tuple[str, dict]] = []
  - L139: fieldsets.append((self.details_fieldset_title, {"fields": detail_fields}))
  - L141: fieldsets.append((self.jsonb_fieldset_title, {"fields": json_fields}))
  - L142: if fieldsets:
  - L143: return tuple(fieldsets)
  - L157: # Scalar fields: address_full, attention, balance, conditions_description, conditions_id, dt_created, dt_modified, email, health_rating, ida, is_active, is_archived, is_commission, is_deleted, is_locked, line_increment, parent_id, parent_model, phone, price_level, priority, security_level, status, terms, total, uuid, version
  - L158: list_display = ("ida", "status", "email", "phone", "address_full", "attention", "is_active", "dt_created")
  - L160: search_fields = ("id", "ida")
  - L165: # Scalar fields: dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, line_number, price_level, security_level, status, uuid, version
  - L166: list_display = ("ida", "status", "health_rating", "is_locked", "line_number", "price_level", "is_active", "dt_created")
  - L168: search_fields = ("id", "ida")
  - L181: # Scalar fields: dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, line_number, price_level, security_level, status, uuid, version
  - L182: list_display = ("ida", "status", "health_rating", "is_locked", "line_number", "price_level", "is_active", "dt_created")
  - L184: search_fields = ("id", "ida")
  - L241: # Scalar fields: address_full, attention, balance, conditions_description, conditions_id, dt_created, dt_modified, email, health_rating, ida, is_active, is_archived, is_commission, is_deleted, is_locked, line_increment, parent_id, parent_model, phone, price_level, priority, security_level, status, terms, total, uuid, version
  - L242: list_display = ("ida", "status", "email", "phone", "address_full", "attention", "is_active", "dt_created")
  - L244: search_fields = ("id", "ida")
- Recommended list display: ida, status
- Recommended detail order (all fields): address_full, attention, balance, conditions_description, conditions_id, contact_id, customer_id, dt_created, dt_modified, email, health_rating, id, ida, is_active, is_archived, is_commission, is_deleted, is_locked, line_increment, manufacturer_id, parent_id, parent_model, phone, price_level, priority, security_level, status, terms, terms_fk_id, total, uuid, vendor_id, version, actions, comments, cost, finance, flow, metadata, prefs, refs, sell, source, totals
- Scalar fields (alphabetical): address_full, attention, balance, conditions_description, conditions_id, contact_id, customer_id, dt_created, dt_modified, email, health_rating, id, ida, is_active, is_archived, is_commission, is_deleted, is_locked, line_increment, manufacturer_id, parent_id, parent_model, phone, price_level, priority, security_level, status, terms, terms_fk_id, total, uuid, vendor_id, version
- JSONB fields (alphabetical): actions, comments, cost, finance, flow, metadata, prefs, refs, sell, source, totals

### document
- apps/docs/admin.py
  - L9: # Scalar fields alphabetically for list display
  - L34: # Object/JSON fields alphabetically
  - L47: # Scalar fields: body, checksum, comment, confidential, count_accessed, description, dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, mime_type, model_name, name, retention_period, search_vector, security_level, sequence, size_bytes, slug, status, uuid, version
  - L48: list_display = ("ida", "name", "description", "status", "body", "checksum", "is_active", "dt_created")
  - L50: search_fields = ('name', 'slug', 'description')
  - L51: readonly_fields = ('uuid', 'dt_created', 'dt_modified', 'search_vector')
  - L54: fieldsets = (
  - L55: ('Identification', {'fields': ('id', 'ida', 'uuid', 'name', 'slug')}),
  - L56: ('Status & Classification', {'fields': ('status', 'model_name', 'confidential', 'security_level')}),
  - L57: ('File Info', {'fields': ('mime_type', 'size_bytes', 'checksum', 'path')}),
  - L58: ('Content', {'fields': ('description', 'body', 'comment', 'data', 'copyright')}),
  - L59: ('Counters & Sequence', {'fields': ('count_accessed', 'sequence', 'retention_period')}),
  - L60: ('Lifecycle', {'fields': ('is_active', 'is_deleted', 'is_archived', 'version')}),
  - L61: ('Timestamps', {'fields': ('dt_created', 'dt_modified')}),
  - L62: ('Extended Data', {'fields': ('refs', 'prefs', 'metadata', 'actions', 'comments'), 'classes': ('collapse',)}),
  - L69: # Scalar fields alphabetically for list display
  - L89: # Object/JSON/Text fields alphabetically
  - L101: # Scalar fields: answer, answer_id, count_accessed, dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, parent_id, parent_model, question, question_id, search_vector, security_level, sequence, status, uuid, version
  - L102: list_display = ("ida", "status", "answer", "answer_id", "count_accessed", "health_rating", "is_active", "dt_created")
  - L104: search_fields = ('question', 'answer', 'parent_model')
- Recommended list display: ida, name
- Recommended detail order (all fields): body, checksum, comment, confidential, count_accessed, description, dt_created, dt_modified, health_rating, id, ida, is_active, is_archived, is_deleted, is_locked, mime_type, model_name, name, retention_period, search_vector, security_level, sequence, size_bytes, slug, status, uuid, version, actions, comments, copyright, data, metadata, path, prefs, refs
- Scalar fields (alphabetical): body, checksum, comment, confidential, count_accessed, description, dt_created, dt_modified, health_rating, id, ida, is_active, is_archived, is_deleted, is_locked, mime_type, model_name, name, retention_period, search_vector, security_level, sequence, size_bytes, slug, status, uuid, version
- JSONB fields (alphabetical): actions, comments, copyright, data, metadata, path, prefs, refs

### contact
- apps/communications/admin.py
  - L12: # Scalar fields: address1, address2, address_type, city, country, dt_created, dt_modified, full, health_rating, ida, instructions, is_active, is_archived, is_deleted, is_locked, latitude, longitude, security_level, state, uuid, version, zip
  - L13: list_display = ("ida", "address1", "address2", "address_type", "city", "country", "is_active", "dt_created")
  - L15: search_fields = ('address1', 'address2', 'city', 'zip', 'full')
  - L16: readonly_fields = ('full',)
  - L17: fieldsets = (
  - L19: 'fields': ('address1', 'address2', 'address_type', 'city', 'country', 'state', 'zip', 'full')
  - L22: 'fields': ('latitude', 'longitude')
  - L25: 'fields': ('comments', 'instructions', 'refs', 'prefs', 'metadata')
  - L34: # Scalar fields: attention, dt_created, dt_modified, email, health_rating, ida, is_active, is_archived, is_deleted, is_locked, is_primary, is_verified, name, opt_out, security_level, type, uuid, version
  - L35: list_display = ("ida", "name", "type", "email", "is_primary", "is_verified", "is_active", "dt_created")
  - L37: search_fields = ('email', 'name', 'attention')
  - L38: #readonly_fields = ('uuid', 'status_display')
  - L42: fieldsets = (
  - L44: 'fields': ('email', 'name', 'attention', 'contact')
  - L47: 'fields': ('opt_out', 'is_primary')
  - L50: 'fields': ('comments', 'refs', 'prefs', 'metadata')
  - L58: # Scalar fields: attention, country_code, dt_created, dt_modified, format, health_rating, ida, is_active, is_archived, is_deleted, is_locked, name, number, opt_out, security_level, uuid, version
  - L59: list_display = ("ida", "name", "number", "attention", "country_code", "format", "is_active", "dt_created")
  - L61: search_fields = ('number', 'name', 'attention')
  - L62: #readonly_fields = ('uuid')  # Add get_dt_verified
- apps/core/admin.py
  - L48: # Scalar fields: address_full, address_id, attention, comment, company, department, domain, domain_id, dt_created, dt_joined, dt_modified, email, email_id, groups, health_rating, ida, is_active, is_archived, is_deleted, is_locked, is_staff, is_superuser, last_login, name_first, name_last, name_middle, name_prefix, name_suffix, other_id, password, phone, phone_id, role, security_level, title, user_permissions, uuid, version
  - L49: list_display = ("ida", "company", "title", "email", "phone", "address_full", "is_active", "dt_created")
  - L51: search_fields = ('email', 'name_first', 'name_last', 'company')
  - L52: readonly_fields = ('id', 'uuid', 'dt_created', 'dt_modified', 'dt_joined', 'version')
  - L66: # Specify the fields to be used in displaying the User model
  - L67: # These are the fields that inherit from BaseUserAdmin but we override for our Contact model
  - L71: 'fields': ('email', 'password1', 'password2'),
  - L75: 'fields': ('name_first', 'name_last', 'name_middle', 'name_prefix', 'name_suffix'),
  - L79: 'fields': (
  - L93: 'fields': ('role', 'is_active', 'is_staff'),
  - L97: fieldsets = (
  - L98: (None, {'fields': ('email', 'password')}),
  - L99: ('Scalar fields', {'fields': (
  - L108: ('JSONB fields', {
  - L109: 'fields': ('actions', 'comment', 'comments', 'groups', 'metadata', 'prefs', 'refs', 'user_permissions'),
  - L113: 'fields': ('id', 'uuid', 'ida', 'dt_created', 'dt_modified', 'dt_joined', 'version'),
  - L118: # Override the get_fieldsets method to use our custom fieldsets
  - L140: # Scalar fields: burndown, contact_id, difficulty, dt_completed, dt_created, dt_deadline, dt_end_original, dt_expected, dt_modified, dt_start, dt_start_original, dt_updated, duration, health_rating, ida, is_active, is_archived, is_deleted, is_locked, kanban_column, linkage, percent_complete, priority, project_id, project_ida, project_name, security_level, sequence, status, uuid, version
  - L141: list_display = ("ida", "project_name", "priority", "status", "burndown", "kanban_column", "assigned_to_names", "description_en", "contact_id", "difficulty", "dt_completed", "is_active", "dt_created")
  - L143: search_fields = ('project_id', 'action')
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
  - L51: # Scalar fields: address_full, address_id, attention, display_name, domain, domain_id, dt_created, dt_modified, email, email_id, health_rating, ida, is_active, is_archived, is_deleted, is_locked, org_type, phone, phone_id, price_level, security_level, status, terms, uuid, version
  - L52: list_display = ("ida", "display_name", "status", "email", "phone", "address_full", "is_active", "dt_created")
  - L54: search_fields = ("display_name", "domains", "contacts", "email", "phone")
  - L55: readonly_fields = ("id", "uuid", "dt_created", "dt_modified", "version")
  - L59: # Scalar fields alphabetical, then JSONB fields alphabetical
  - L60: fieldsets = (
  - L61: ("Scalar fields", {"fields": (
  - L69: ("JSONB fields", {
  - L70: "fields": (
  - L79: "fields": ("id", "uuid", "ida", "dt_created", "dt_modified", "version"),
- Recommended list display: ida, company
- Recommended detail order (all fields): address_full, address_id, attention, comment, company, customer_id, department, domain, domain_id, dt_created, dt_joined, dt_modified, email, email_id, employee_id, groups, health_rating, id, ida, is_active, is_archived, is_deleted, is_locked, is_staff, is_superuser, last_login, manufacturer_id, name_first, name_last, name_middle, name_prefix, name_suffix, other_id, password, phone, phone_id, rep_id, role, security_level, title, user_permissions, uuid, vendor_id, version, actions, comments, metadata, prefs, refs
- Scalar fields (alphabetical): address_full, address_id, attention, comment, company, customer_id, department, domain, domain_id, dt_created, dt_joined, dt_modified, email, email_id, employee_id, groups, health_rating, id, ida, is_active, is_archived, is_deleted, is_locked, is_staff, is_superuser, last_login, manufacturer_id, name_first, name_last, name_middle, name_prefix, name_suffix, other_id, password, phone, phone_id, rep_id, role, security_level, title, user_permissions, uuid, vendor_id, version
- JSONB fields (alphabetical): actions, comments, metadata, prefs, refs

### payment
- apps/transactions/admin.py
  - L69: """Display computed fields from JSON item and quantity fields for line models."""
  - L103: """Group JSON-heavy fields at the end of the admin form."""
  - L128: for field in self.model._meta.fields:
  - L137: fieldsets: list[tuple[str, dict]] = []
  - L139: fieldsets.append((self.details_fieldset_title, {"fields": detail_fields}))
  - L141: fieldsets.append((self.jsonb_fieldset_title, {"fields": json_fields}))
  - L142: if fieldsets:
  - L143: return tuple(fieldsets)
  - L157: # Scalar fields: address_full, attention, balance, conditions_description, conditions_id, dt_created, dt_modified, email, health_rating, ida, is_active, is_archived, is_commission, is_deleted, is_locked, line_increment, parent_id, parent_model, phone, price_level, priority, security_level, status, terms, total, uuid, version
  - L158: list_display = ("ida", "status", "email", "phone", "address_full", "attention", "is_active", "dt_created")
  - L160: search_fields = ("id", "ida")
  - L165: # Scalar fields: dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, line_number, price_level, security_level, status, uuid, version
  - L166: list_display = ("ida", "status", "health_rating", "is_locked", "line_number", "price_level", "is_active", "dt_created")
  - L168: search_fields = ("id", "ida")
  - L181: # Scalar fields: dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, line_number, price_level, security_level, status, uuid, version
  - L182: list_display = ("ida", "status", "health_rating", "is_locked", "line_number", "price_level", "is_active", "dt_created")
  - L184: search_fields = ("id", "ida")
  - L241: # Scalar fields: address_full, attention, balance, conditions_description, conditions_id, dt_created, dt_modified, email, health_rating, ida, is_active, is_archived, is_commission, is_deleted, is_locked, line_increment, parent_id, parent_model, phone, price_level, priority, security_level, status, terms, total, uuid, version
  - L242: list_display = ("ida", "status", "email", "phone", "address_full", "attention", "is_active", "dt_created")
  - L244: search_fields = ("id", "ida")
- Recommended list display: ida, status
- Recommended detail order (all fields): amount, contact_id, dt_created, dt_modified, dt_payment, dt_processed, dt_reconciliation, fee_amount, gateway, health_rating, id, id_gateway_payment_intent, id_gateway_transaction, ida, invoice_id, is_active, is_archived, is_deleted, is_locked, notes, payment_method_id, payment_term_id, reconciled, reference_number, security_level, status, uuid, version, actions, comments, gateway_response, metadata, prefs, refs
- Scalar fields (alphabetical): amount, contact_id, dt_created, dt_modified, dt_payment, dt_processed, dt_reconciliation, fee_amount, gateway, health_rating, id, id_gateway_payment_intent, id_gateway_transaction, ida, invoice_id, is_active, is_archived, is_deleted, is_locked, notes, payment_method_id, payment_term_id, reconciled, reference_number, security_level, status, uuid, version
- JSONB fields (alphabetical): actions, comments, gateway_response, metadata, prefs, refs

### customer
- apps/core/admin.py
  - L48: # Scalar fields: address_full, address_id, attention, comment, company, department, domain, domain_id, dt_created, dt_joined, dt_modified, email, email_id, groups, health_rating, ida, is_active, is_archived, is_deleted, is_locked, is_staff, is_superuser, last_login, name_first, name_last, name_middle, name_prefix, name_suffix, other_id, password, phone, phone_id, role, security_level, title, user_permissions, uuid, version
  - L49: list_display = ("ida", "company", "title", "email", "phone", "address_full", "is_active", "dt_created")
  - L51: search_fields = ('email', 'name_first', 'name_last', 'company')
  - L52: readonly_fields = ('id', 'uuid', 'dt_created', 'dt_modified', 'dt_joined', 'version')
  - L66: # Specify the fields to be used in displaying the User model
  - L67: # These are the fields that inherit from BaseUserAdmin but we override for our Contact model
  - L71: 'fields': ('email', 'password1', 'password2'),
  - L75: 'fields': ('name_first', 'name_last', 'name_middle', 'name_prefix', 'name_suffix'),
  - L79: 'fields': (
  - L93: 'fields': ('role', 'is_active', 'is_staff'),
  - L97: fieldsets = (
  - L98: (None, {'fields': ('email', 'password')}),
  - L99: ('Scalar fields', {'fields': (
  - L108: ('JSONB fields', {
  - L109: 'fields': ('actions', 'comment', 'comments', 'groups', 'metadata', 'prefs', 'refs', 'user_permissions'),
  - L113: 'fields': ('id', 'uuid', 'ida', 'dt_created', 'dt_modified', 'dt_joined', 'version'),
  - L118: # Override the get_fieldsets method to use our custom fieldsets
  - L140: # Scalar fields: burndown, contact_id, difficulty, dt_completed, dt_created, dt_deadline, dt_end_original, dt_expected, dt_modified, dt_start, dt_start_original, dt_updated, duration, health_rating, ida, is_active, is_archived, is_deleted, is_locked, kanban_column, linkage, percent_complete, priority, project_id, project_ida, project_name, security_level, sequence, status, uuid, version
  - L141: list_display = ("ida", "project_name", "priority", "status", "burndown", "kanban_column", "assigned_to_names", "description_en", "contact_id", "difficulty", "dt_completed", "is_active", "dt_created")
  - L143: search_fields = ('project_id', 'action')
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
  - L51: # Scalar fields: address_full, address_id, attention, display_name, domain, domain_id, dt_created, dt_modified, email, email_id, health_rating, ida, is_active, is_archived, is_deleted, is_locked, org_type, phone, phone_id, price_level, security_level, status, terms, uuid, version
  - L52: list_display = ("ida", "display_name", "status", "email", "phone", "address_full", "is_active", "dt_created")
  - L54: search_fields = ("display_name", "domains", "contacts", "email", "phone")
  - L55: readonly_fields = ("id", "uuid", "dt_created", "dt_modified", "version")
  - L59: # Scalar fields alphabetical, then JSONB fields alphabetical
  - L60: fieldsets = (
  - L61: ("Scalar fields", {"fields": (
  - L69: ("JSONB fields", {
  - L70: "fields": (
  - L79: "fields": ("id", "uuid", "ida", "dt_created", "dt_modified", "version"),
- Recommended list display: ida, display_name
- Recommended detail order (all fields): address_full, address_id, attention, contact_id, display_name, domain, domain_id, dt_created, dt_modified, email, email_id, health_rating, id, ida, is_active, is_archived, is_deleted, is_locked, org_type, phone, phone_id, price_level, security_level, status, terms, terms_fk_id, uuid, version, actions, addresses, comments, connections, contacts, data, docs, domains, emails, financial, gl_accounts, metadata, metrics, phones, prefs, refs, relations, relationship_stats, stats
- Scalar fields (alphabetical): address_full, address_id, attention, contact_id, display_name, domain, domain_id, dt_created, dt_modified, email, email_id, health_rating, id, ida, is_active, is_archived, is_deleted, is_locked, org_type, phone, phone_id, price_level, security_level, status, terms, terms_fk_id, uuid, version
- JSONB fields (alphabetical): actions, addresses, comments, connections, contacts, data, docs, domains, emails, financial, gl_accounts, metadata, metrics, phones, prefs, refs, relations, relationship_stats, stats

### vendor
- apps/core/admin.py
  - L48: # Scalar fields: address_full, address_id, attention, comment, company, department, domain, domain_id, dt_created, dt_joined, dt_modified, email, email_id, groups, health_rating, ida, is_active, is_archived, is_deleted, is_locked, is_staff, is_superuser, last_login, name_first, name_last, name_middle, name_prefix, name_suffix, other_id, password, phone, phone_id, role, security_level, title, user_permissions, uuid, version
  - L49: list_display = ("ida", "company", "title", "email", "phone", "address_full", "is_active", "dt_created")
  - L51: search_fields = ('email', 'name_first', 'name_last', 'company')
  - L52: readonly_fields = ('id', 'uuid', 'dt_created', 'dt_modified', 'dt_joined', 'version')
  - L66: # Specify the fields to be used in displaying the User model
  - L67: # These are the fields that inherit from BaseUserAdmin but we override for our Contact model
  - L71: 'fields': ('email', 'password1', 'password2'),
  - L75: 'fields': ('name_first', 'name_last', 'name_middle', 'name_prefix', 'name_suffix'),
  - L79: 'fields': (
  - L93: 'fields': ('role', 'is_active', 'is_staff'),
  - L97: fieldsets = (
  - L98: (None, {'fields': ('email', 'password')}),
  - L99: ('Scalar fields', {'fields': (
  - L108: ('JSONB fields', {
  - L109: 'fields': ('actions', 'comment', 'comments', 'groups', 'metadata', 'prefs', 'refs', 'user_permissions'),
  - L113: 'fields': ('id', 'uuid', 'ida', 'dt_created', 'dt_modified', 'dt_joined', 'version'),
  - L118: # Override the get_fieldsets method to use our custom fieldsets
  - L140: # Scalar fields: burndown, contact_id, difficulty, dt_completed, dt_created, dt_deadline, dt_end_original, dt_expected, dt_modified, dt_start, dt_start_original, dt_updated, duration, health_rating, ida, is_active, is_archived, is_deleted, is_locked, kanban_column, linkage, percent_complete, priority, project_id, project_ida, project_name, security_level, sequence, status, uuid, version
  - L141: list_display = ("ida", "project_name", "priority", "status", "burndown", "kanban_column", "assigned_to_names", "description_en", "contact_id", "difficulty", "dt_completed", "is_active", "dt_created")
  - L143: search_fields = ('project_id', 'action')
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
  - L51: # Scalar fields: address_full, address_id, attention, display_name, domain, domain_id, dt_created, dt_modified, email, email_id, health_rating, ida, is_active, is_archived, is_deleted, is_locked, org_type, phone, phone_id, price_level, security_level, status, terms, uuid, version
  - L52: list_display = ("ida", "display_name", "status", "email", "phone", "address_full", "is_active", "dt_created")
  - L54: search_fields = ("display_name", "domains", "contacts", "email", "phone")
  - L55: readonly_fields = ("id", "uuid", "dt_created", "dt_modified", "version")
  - L59: # Scalar fields alphabetical, then JSONB fields alphabetical
  - L60: fieldsets = (
  - L61: ("Scalar fields", {"fields": (
  - L69: ("JSONB fields", {
  - L70: "fields": (
  - L79: "fields": ("id", "uuid", "ida", "dt_created", "dt_modified", "version"),
- Recommended list display: ida, display_name
- Recommended detail order (all fields): address_full, address_id, attention, contact_id, display_name, domain, domain_id, dt_created, dt_modified, email, email_id, health_rating, id, ida, is_active, is_archived, is_deleted, is_locked, org_type, phone, phone_id, price_level, security_level, status, terms, terms_fk_id, uuid, version, actions, addresses, comments, connections, contacts, data, docs, domains, emails, financial, gl_accounts, metadata, metrics, phones, prefs, refs, relations, relationship_stats, stats
- Scalar fields (alphabetical): address_full, address_id, attention, contact_id, display_name, domain, domain_id, dt_created, dt_modified, email, email_id, health_rating, id, ida, is_active, is_archived, is_deleted, is_locked, org_type, phone, phone_id, price_level, security_level, status, terms, terms_fk_id, uuid, version
- JSONB fields (alphabetical): actions, addresses, comments, connections, contacts, data, docs, domains, emails, financial, gl_accounts, metadata, metrics, phones, prefs, refs, relations, relationship_stats, stats

### requisition
- apps/transactions/admin.py
  - L69: """Display computed fields from JSON item and quantity fields for line models."""
  - L103: """Group JSON-heavy fields at the end of the admin form."""
  - L128: for field in self.model._meta.fields:
  - L137: fieldsets: list[tuple[str, dict]] = []
  - L139: fieldsets.append((self.details_fieldset_title, {"fields": detail_fields}))
  - L141: fieldsets.append((self.jsonb_fieldset_title, {"fields": json_fields}))
  - L142: if fieldsets:
  - L143: return tuple(fieldsets)
  - L157: # Scalar fields: address_full, attention, balance, conditions_description, conditions_id, dt_created, dt_modified, email, health_rating, ida, is_active, is_archived, is_commission, is_deleted, is_locked, line_increment, parent_id, parent_model, phone, price_level, priority, security_level, status, terms, total, uuid, version
  - L158: list_display = ("ida", "status", "email", "phone", "address_full", "attention", "is_active", "dt_created")
  - L160: search_fields = ("id", "ida")
  - L165: # Scalar fields: dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, line_number, price_level, security_level, status, uuid, version
  - L166: list_display = ("ida", "status", "health_rating", "is_locked", "line_number", "price_level", "is_active", "dt_created")
  - L168: search_fields = ("id", "ida")
  - L181: # Scalar fields: dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, line_number, price_level, security_level, status, uuid, version
  - L182: list_display = ("ida", "status", "health_rating", "is_locked", "line_number", "price_level", "is_active", "dt_created")
  - L184: search_fields = ("id", "ida")
  - L241: # Scalar fields: address_full, attention, balance, conditions_description, conditions_id, dt_created, dt_modified, email, health_rating, ida, is_active, is_archived, is_commission, is_deleted, is_locked, line_increment, parent_id, parent_model, phone, price_level, priority, security_level, status, terms, total, uuid, version
  - L242: list_display = ("ida", "status", "email", "phone", "address_full", "attention", "is_active", "dt_created")
  - L244: search_fields = ("id", "ida")
- Recommended list display: ida, name
- Recommended detail order (all fields): dt_created, dt_modified, health_rating, id, ida, is_active, is_archived, is_deleted, is_locked, name, purpose, security_level, status, uuid, version, actions, comments, metadata, prefs, refs
- Scalar fields (alphabetical): dt_created, dt_modified, health_rating, id, ida, is_active, is_archived, is_deleted, is_locked, name, purpose, security_level, status, uuid, version
- JSONB fields (alphabetical): actions, comments, metadata, prefs, refs

### audit
- apps/accounts/admin.py
  - L12: # Scalar fields: account_credit, account_debit, account_number, category, comment, division, dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, name, security_level, type, type_id, used_for, uuid, version
  - L13: list_display = ("ida", "name", "type", "account_credit", "account_debit", "account_number", "is_active", "dt_created")
  - L15: search_fields = ("account_number", "name")
  - L24: # Scalar fields: code, dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, name, precision, security_level, symbol, uuid, version
  - L25: list_display = ("ida", "name", "code", "health_rating", "is_locked", "precision", "is_active", "dt_created")
  - L27: search_fields = ("code", "name")
  - L32: # Scalar fields: currency_base, currency_target, dt_created, dt_end, dt_modified, dt_start, health_rating, ida, is_active, is_archived, is_deleted, is_locked, name, precision_convert, precision_display, rate, security_level, uuid, version
  - L33: list_display = ("ida", "name", "currency_base", "currency_target", "dt_end", "dt_start", "is_active", "dt_created")
  - L35: search_fields = ("currency_base", "currency_target")
  - L40: # Scalar fields: currency_base, currency_target, dt_created, dt_end, dt_modified, dt_start, health_rating, ida, is_active, is_archived, is_deleted, is_locked, name, precision_convert, precision_display, rate, security_level, uuid, version
  - L41: list_display = ("ida", "name", "currency_base", "currency_target", "dt_end", "dt_start", "is_active", "dt_created")
  - L43: search_fields = ("name", "currency_base", "currency_target")
  - L48: # Scalar fields: approved_by, day_cut_off_due, day_cut_off_invoice, days_discount, days_due, days_in_period, description, discount_rate, dt_begin, dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, name, period_count, security_level, uuid, version
  - L49: list_display = ("ida", "name", "description", "approved_by", "day_cut_off_due", "day_cut_off_invoice", "is_active", "dt_created")
  - L51: search_fields = ("name", "description")
  - L56: # Scalar fields: discount_potential, dt_created, dt_discount_due, dt_due, dt_modified, dt_posted, dt_recorded, dt_settled, health_rating, ida, is_active, is_archived, is_cleared, is_deleted, is_locked, is_settled, is_void, model_name, parent_id, security_level, source, uuid, value_available, value_original, version
  - L57: list_display = ("ida", "discount_potential", "dt_discount_due", "dt_due", "dt_posted", "dt_recorded", "is_active", "dt_created")
  - L59: search_fields = ("ida",)
  - L60: readonly_fields = ("uuid", "dt_created", "dt_modified")
  - L65: # Scalar fields: dt_created, dt_modified, gl_account_payable, health_rating, ida, is_active, is_archived, is_deleted, is_locked, security_level, service_provider, tax_jurisdiction, tax_name, tax_rate_cost, tax_rate_on_shipping, tax_rate_sales, uuid, version
- Recommended list display: ida, name
- Recommended detail order (all fields): dt_created, dt_modified, health_rating, id, ida, is_active, is_archived, is_completed, is_deleted, is_locked, name, priority, purpose, rating, security_level, uuid, version, actions, changes, comments, conflicts, metadata, prefs, recommendations, refs
- Scalar fields (alphabetical): dt_created, dt_modified, health_rating, id, ida, is_active, is_archived, is_completed, is_deleted, is_locked, name, priority, purpose, rating, security_level, uuid, version
- JSONB fields (alphabetical): actions, changes, comments, conflicts, metadata, prefs, recommendations, refs

### report
- apps/core/admin.py
  - L48: # Scalar fields: address_full, address_id, attention, comment, company, department, domain, domain_id, dt_created, dt_joined, dt_modified, email, email_id, groups, health_rating, ida, is_active, is_archived, is_deleted, is_locked, is_staff, is_superuser, last_login, name_first, name_last, name_middle, name_prefix, name_suffix, other_id, password, phone, phone_id, role, security_level, title, user_permissions, uuid, version
  - L49: list_display = ("ida", "company", "title", "email", "phone", "address_full", "is_active", "dt_created")
  - L51: search_fields = ('email', 'name_first', 'name_last', 'company')
  - L52: readonly_fields = ('id', 'uuid', 'dt_created', 'dt_modified', 'dt_joined', 'version')
  - L66: # Specify the fields to be used in displaying the User model
  - L67: # These are the fields that inherit from BaseUserAdmin but we override for our Contact model
  - L71: 'fields': ('email', 'password1', 'password2'),
  - L75: 'fields': ('name_first', 'name_last', 'name_middle', 'name_prefix', 'name_suffix'),
  - L79: 'fields': (
  - L93: 'fields': ('role', 'is_active', 'is_staff'),
  - L97: fieldsets = (
  - L98: (None, {'fields': ('email', 'password')}),
  - L99: ('Scalar fields', {'fields': (
  - L108: ('JSONB fields', {
  - L109: 'fields': ('actions', 'comment', 'comments', 'groups', 'metadata', 'prefs', 'refs', 'user_permissions'),
  - L113: 'fields': ('id', 'uuid', 'ida', 'dt_created', 'dt_modified', 'dt_joined', 'version'),
  - L118: # Override the get_fieldsets method to use our custom fieldsets
  - L140: # Scalar fields: burndown, contact_id, difficulty, dt_completed, dt_created, dt_deadline, dt_end_original, dt_expected, dt_modified, dt_start, dt_start_original, dt_updated, duration, health_rating, ida, is_active, is_archived, is_deleted, is_locked, kanban_column, linkage, percent_complete, priority, project_id, project_ida, project_name, security_level, sequence, status, uuid, version
  - L141: list_display = ("ida", "project_name", "priority", "status", "burndown", "kanban_column", "assigned_to_names", "description_en", "contact_id", "difficulty", "dt_completed", "is_active", "dt_created")
  - L143: search_fields = ('project_id', 'action')
- Recommended list display: ida, name
- Recommended detail order (all fields): category, description, dt_created, dt_modified, health_rating, id, ida, is_active, is_archived, is_deleted, is_locked, model_name, name, output_type, purpose, record_id, role_required, security_level, sort_order, uuid, version, actions, comments, data, metadata, prefs, refs
- Scalar fields (alphabetical): category, description, dt_created, dt_modified, health_rating, id, ida, is_active, is_archived, is_deleted, is_locked, model_name, name, output_type, purpose, record_id, role_required, security_level, sort_order, uuid, version
- JSONB fields (alphabetical): actions, comments, data, metadata, prefs, refs

### connection
- apps/sync/admin.py
  - L14: # Scalar fields: action, comment, dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, name, purpose, security_level, status, type, uuid, version
  - L15: list_display = ("ida", "name", "status", "type", "action", "comment", "is_active", "dt_created")
  - L16: search_fields = ("name", "type")
  - L17: readonly_fields = ()
  - L22: # Scalar fields: alert, direction, dt_created, dt_modified, duration, health_rating, ida, is_active, is_archived, is_deleted, is_locked, security_level, size, status, uuid, version
  - L23: list_display = ("ida", "status", "alert", "direction", "duration", "health_rating", "is_active", "dt_created")
  - L24: search_fields = ("id", "status", "direction")
- Recommended list display: ida, name
- Recommended detail order (all fields): action, comment, dt_created, dt_modified, health_rating, id, ida, is_active, is_archived, is_deleted, is_locked, name, purpose, security_level, status, type, uuid, version, actions, changes, comments, config, conflicts, encryption, maps, metadata, prefs, refs, relationships, rules, scripts
- Scalar fields (alphabetical): action, comment, dt_created, dt_modified, health_rating, id, ida, is_active, is_archived, is_deleted, is_locked, name, purpose, security_level, status, type, uuid, version
- JSONB fields (alphabetical): actions, changes, comments, config, conflicts, encryption, maps, metadata, prefs, refs, relationships, rules, scripts

## To_Alice Consumption
- No To_Alice overrides were applied.

## User Overrides
<!-- To_Alice: -->
- Example To_Alice payload: model=customer; list_display=ida,display_name; detail_order=display_name,status,addresses,contacts
- To provide alternative instructions, add a note via /wcapi/ai/note/ with:
  category=pending, role=config_suggestion, name='Schema report override',
  details={model, list_display, detail_order, rationale}
