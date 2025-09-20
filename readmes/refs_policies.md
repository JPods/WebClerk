# Refs Inclusion Policies (Materialized Graph Index)

Baseline: if a line has an active Action, link the assignee (contact, customer, vendor, etc.) to that line via refs.links with kind="assignee". Links are bidirectional (line <-> party).

Write path:

- common.refs.assignees.ensure_line_assignee_links(line, kind="assignee")
- Call from Action save or via Celery task sync_assignees_for_line.
Cleanup:

- common.refs.tasks.nightly_prune_refs applies recency and caps.
- When actions close, links age out via pruning rules.
Notes:

- Link shape: { model, id, kind, dir, ts } stored at model.refs.links.
- Admin rules can override defaults in PolicyEngine (DB-backed overrides TBD).
- Link shape: { model, id, kind, dir, ts } stored at model.refs.links.
- Admin rules can override defaults in PolicyEngine (DB-backed overrides TBD).

## Action models denormalization

Actions denormalize links to speed navigation for the Responsible Person:

- Action -> Target(s): kind auto-inferred:
  - Transactions (orders/invoices/lines): kind="transaction"
  - Products (catalog/product/variant): kind="product"
  - Fallback: kind="acts_on"
- Action -> Documents/Files/Attachments: kind="doc"
- Action -> Communications (messages/emails/notes): kind="comm"
- Action -> Sync/Integration artifacts: kind="sync"
Customization:

- Override inference per model via settings.REFS_ACTION_KIND_OVERRIDES, e.g.:
  { "transactions.invoice": "transaction", "products.product": "product" }
Helpers and tasks:

- common.refs.actions_index.ensure_action_all_links(action)
- common.refs.tasks.sync_action_denorm_refs(action_model, action_id)
- Signals: apps.support.signals.register_action_signals wires post_save and m2m_changed
Helpers and tasks:
- common.refs.actions_index.ensure_action_all_links(action)
- common.refs.tasks.sync_action_denorm_refs(action_model, action_id)
- Signals: apps.support.signals.register_action_signals wires post_save and m2m_changed

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_CONTENT_NEGOTIATION_CLASS": "common.http.negotiation.JSONOnlyNegotiation",
    "EXCEPTION_HANDLER": "common.http.exceptions.api_exception_handler",
}
