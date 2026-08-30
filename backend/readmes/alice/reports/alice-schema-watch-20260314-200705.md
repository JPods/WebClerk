# Alice Schema Watch Report

- Timestamp (UTC): 2026-03-14 20:07:05
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

## User Overrides
<!-- Alice-Instruction: Add alternative instructions below. Example: model=customer; list_display=ida,company; detail_order=company,status,metadata,refs -->
- To provide alternative instructions, add a note via /wcapi/ai/note/ with:
  category=pending, role=config_suggestion, name='Schema report override',
  details={model, list_display, detail_order, rationale}
