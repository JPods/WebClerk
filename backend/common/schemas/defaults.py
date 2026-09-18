"""Model-specific envelope defaults.

Returns the correct default dict for any model's config/metadata/prefs/refs
by loading the Pydantic schema and calling model_dump().

Model-specific schemas live next to their Django models as *_pydantic.py files.
_APP_SCHEMA_MAP routes each model_key to its module path.

Base defaults (universal, no model awareness) live in common/models.py:
    default_metadata(), default_refs(), default_prefs(), default_comments()

Usage:
    from common.schemas.defaults import get_envelope_default

    get_envelope_default('contact', 'metadata')  # -> ContactMetadata defaults
    get_envelope_default('serial', 'config')      # -> SerialConfig defaults
    get_envelope_default('touch', 'refs')          # -> RefsBase defaults (no schema file)
"""
from __future__ import annotations

import importlib
import logging

logger = logging.getLogger(__name__)


def _model_key_to_class(key: str) -> str:
    """Convert snake_case model key to PascalCase class prefix."""
    return ''.join(word.capitalize() for word in key.split('_'))


_ENVELOPE_SUFFIXES = {
    'config': 'Config',
    'metadata': 'Metadata',
    'prefs': 'Prefs',
    'refs': 'Refs',
}

# Schemas co-located with their Django models (app/models/*_pydantic.py).
# Key = model_key (snake_case), value = dotted module path.
_APP_SCHEMA_MAP = {
    # accounts
    'audit':                         'apps.accounts.models.audit_pydantic',
    'budget':                        'apps.accounts.models.budget_pydantic',
    'currency':                      'apps.accounts.models.currency_pydantic',
    'erosion':                       'apps.accounts.models.erosion_pydantic',
    'gl_account':                    'apps.accounts.models.gl_account_pydantic',
    'gl_journal':                    'apps.accounts.models.gl_journal_pydantic',
    'journal_batch':                 'apps.accounts.models.journal_batch_pydantic',
    'ledger':                        'apps.accounts.models.ledger_pydantic',
    'tax_jurisdiction':              'apps.accounts.models.tax_jurisdiction_pydantic',
    'term':                          'apps.accounts.models.term_pydantic',
    # ai_assistant
    'ai_message':                    'apps.ai_assistant.models.ai_message_pydantic',
    'alice_coaching_log':            'apps.ai_assistant.models.alice_pydantic',
    'alice_insight':                 'apps.ai_assistant.models.alice_insight_pydantic',
    'alice_observation':             'apps.ai_assistant.models.alice_pydantic',
    'alice_preset':                  'apps.ai_assistant.models.alice_pydantic',
    'episode':                       'apps.ai_assistant.models.episode_pydantic',
    # communications
    'address':                       'apps.communications.models.address_pydantic',
    'domain':                        'apps.communications.models.domain_pydantic',
    'email':                         'apps.communications.models.email_pydantic',
    'phone':                         'apps.communications.models.phone_pydantic',
    'touch':                         'apps.communications.models.touch_pydantic',
    # core
    'action':                        'apps.core.models.action_pydantic',
    'api_log':                       'apps.core.models.log_pydantic',
    'contact':                       'apps.core.models.contact_pydantic',
    'model_link_config':             'apps.core.models.rbac_pydantic',
    'model_role_config':             'apps.core.models.rbac_pydantic',
    'notification':                  'apps.core.models.notification_pydantic',
    'pending':                       'apps.core.models.pending_pydantic',
    'refs_mismatch_log':             'apps.core.models.refs_mismatch_log_pydantic',
    'report':                        'apps.core.models.report_pydantic',
    'role_config':                   'apps.core.models.rbac_pydantic',
    'setting':                       'apps.core.models.setting_pydantic',
    'user_daily_log':                'apps.core.models.log_pydantic',
    'user_profile':                  'apps.core.models.rbac_pydantic',
    'workspace':                     'apps.core.models.workspace_pydantic',
    # docs
    'document':                      'apps.docs.models.document_pydantic',
    'linkage':                       'apps.docs.models.linkage_entry_pydantic',
    'question_answer':               'apps.docs.models.question_answer_pydantic',
    'tag':                           'apps.docs.models.tag_pydantic',
    # orgs
    'customer':                      'apps.orgs.models.customer_pydantic',
    'employee':                      'apps.orgs.models.employee_pydantic',
    'manufacturer':                  'apps.orgs.models.manufacturer_pydantic',
    'other_org':                     'apps.orgs.models.other_pydantic',
    'rep':                           'apps.orgs.models.rep_pydantic',
    'vendor':                        'apps.orgs.models.vendor_pydantic',
    # products
    'bill_of_material':              'apps.products.models.bill_of_material_pydantic',
    'catalog':                       'apps.products.models.catalog_pydantic',
    'inventory_adjustment_run':      'apps.products.models.processor_runs_pydantic',
    'inventory_layer':               'apps.products.models.inventory_layer_pydantic',
    'inventory_metrics_snapshot':     'apps.products.models.metrics_pydantic',
    'inventory_reservation':         'apps.products.models.inventory_reservation_pydantic',
    'item':                          'apps.products.models.item_pydantic',
    'item_usage':                    'apps.products.models.usage_pydantic',
    'item_xref':                     'apps.products.models.item_xref_pydantic',
    'serial':                        'apps.products.models.serial_pydantic',
    'serial_log':                    'apps.products.models.serial_pydantic',
    'variant':                       'apps.products.models.variant_pydantic',
    'warehouse':                     'apps.products.models.warehouse_pydantic',
    # sync
    'bundle':                        'apps.sync.models.bundle_pydantic',
    'connection':                    'apps.sync.models.connection_pydantic',
    # transactions
    'invoice':                       'apps.transactions.models.invoice_pydantic',
    'invoice_line':                   'apps.transactions.models.invoice_line_pydantic',
    'order':                         'apps.transactions.models.order_pydantic',
    'order_line':                    'apps.transactions.models.order_line_pydantic',
    'cash':                       'apps.transactions.models.cash_pydantic',
    'project':                       'apps.transactions.models.project_pydantic',
    'proposal':                      'apps.transactions.models.proposal_pydantic',
    'proposal_line':                 'apps.transactions.models.proposal_line_pydantic',
    'purchase':                      'apps.transactions.models.purchase_pydantic',
    'purchase_line':                 'apps.transactions.models.purchase_line_pydantic',
    'receipt':                       'apps.transactions.models.receipt_pydantic',
    'receipt_line':                  'apps.transactions.models.receipt_line_pydantic',
    'requisition':                   'apps.transactions.models.requisition_pydantic',
    'requisition_line':              'apps.transactions.models.requisition_line_pydantic',
    'statement_line':                'apps.transactions.models.statement_line_pydantic',
    'workorder':                     'apps.transactions.models.workorder_pydantic',
    'workorder_line':                'apps.transactions.models.workorder_line_pydantic',
}


def _schema_key(model_key: str) -> str:
    """Registry keys that are views over another model's table (databrowser, gantt, wc
    over Setting) take that model's schema: the table decides, not the name."""
    if model_key in _APP_SCHEMA_MAP:
        return model_key
    from apps.core.constants.model_registry import MODEL_REGISTRY
    meta = MODEL_REGISTRY.get(model_key)
    if meta:
        for key, other in MODEL_REGISTRY.items():
            if other.model == meta.model and key in _APP_SCHEMA_MAP:
                return key
    return model_key


def schema_class(model_key: str, envelope: str) -> type:
    """The Pydantic class for one envelope of one model. Code is the only source.

    A model in _APP_SCHEMA_MAP must define {PascalKey}{Suffix} in its module — a missing
    module or class raises, because a schema that silently fails to load means every
    save of that model goes unvalidated. A model not in the map uses the envelope base
    class: that is its declared schema, not a fallback.
    """
    if envelope not in _ENVELOPE_SUFFIXES:
        raise ValueError(f"envelope must be one of {list(_ENVELOPE_SUFFIXES)}")
    model_key = _schema_key(model_key)
    if model_key not in _APP_SCHEMA_MAP:
        from common.schemas.envelopes import ConfigBase, MetadataBase, RecordPrefsBase, RefsBase
        return {'config': ConfigBase, 'metadata': MetadataBase,
                'prefs': RecordPrefsBase, 'refs': RefsBase}[envelope]
    module = importlib.import_module(_APP_SCHEMA_MAP[model_key])
    class_name = _model_key_to_class(model_key) + _ENVELOPE_SUFFIXES[envelope]
    try:
        return getattr(module, class_name)
    except AttributeError:
        raise AttributeError(f'{_APP_SCHEMA_MAP[model_key]} has no {class_name}') from None


def schema_classes(model_key: str) -> dict[str, type]:
    """{envelope: Pydantic class} for each envelope field the model has.

    A model that is not a registered Django model is taken to carry all four.
    """
    from apps.core.constants.model_registry import MODEL_REGISTRY
    envelopes = list(_ENVELOPE_SUFFIXES)
    if model_key in MODEL_REGISTRY:
        names = {f.name for f in MODEL_REGISTRY[model_key].import_model()._meta.get_fields()}
        envelopes = [e for e in envelopes if e in names]
    return {envelope: schema_class(model_key, envelope) for envelope in envelopes}


def get_envelope_default(model_key: str, envelope: str) -> dict:
    """Return the default dict for a model's config/metadata/prefs/refs."""
    return schema_class(model_key, envelope)().model_dump()
