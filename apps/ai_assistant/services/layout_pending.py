"""
Layout Pending — decoupled layout save via pending record.

User changes create a pending record (audit trail).
apply_pending_layout reads the pending and applies it to the Setting.

Flow:
  1. React calls manage action "save_layout_pending" with {model, layout_data}
  2. This creates an AliceObservation (pending, auditable)
  3. Then immediately applies it to the Setting record
  4. Returns the updated Setting data

No celery needed — the apply is synchronous but the pending record
provides the audit trail and survives if the Setting is locked.
"""
import json
import time
import logging

logger = logging.getLogger(__name__)


def save_layout_pending(params: dict) -> dict:
    """Create a pending layout record and apply it immediately.

    params:
        model: str — the parent_model (e.g. 'contact', 'action')
        layout_data: dict — the full WorkbenchFieldsSetting {list, detail, views}
        contact_id: int — who made the change (optional)
    """
    from apps.core.models import Setting

    model = params.get('model')
    layout_data = params.get('layout_data')
    contact_id = params.get('contact_id', 0)

    if not model:
        raise ValueError("model is required")
    if not layout_data or not isinstance(layout_data, dict):
        raise ValueError("layout_data dict is required")

    now_ms = int(time.time() * 1000)

    # --- Step 1: Create audit record ---
    try:
        from apps.ai_assistant.models_alice import AliceObservation
        AliceObservation.objects.create(
            source='layout_save',
            category='layout_pending',
            name=f'Layout change: {model}',
            data={
                'model': model,
                'layout_data': layout_data,
                'contact_id': contact_id,
                'dt_requested': now_ms,
                'status': 'applied',
            },
        )
    except Exception as e:
        logger.warning(f"[layout_pending] Could not create audit record: {e}")
        # Don't block the save — audit is nice-to-have

    # --- Step 2: Apply to Setting ---
    # Try wc:model first (consolidated), fall back to legacy wc:workbench_fields
    setting = Setting.objects.filter(
        parent_model=model,
        purpose='wc:model',
    ).first()

    if setting:
        # Update the columns section within wc:model
        cfg = setting.config or {}
        old_list = [f.get('field') if isinstance(f, dict) else f
                    for f in (cfg.get('columns', {}).get('list', []) if isinstance(cfg.get('columns'), dict) else [])[:4]]

        cfg['columns'] = layout_data
        setting.config = cfg
        setting.save(update_fields=['config', 'dt_modified'])

        new_list = [f.get('field') if isinstance(f, dict) else f
                    for f in layout_data.get('list', [])[:4]]

        logger.warning(
            f"[layout_pending] APPLIED to wc:model #{setting.id} for {model}: "
            f"list {old_list} → {new_list}"
        )

        return {
            'setting_id': setting.id,
            'model': model,
            'status': 'applied',
            'list_count': len(layout_data.get('list', [])),
            'views_count': len(layout_data.get('views', [])),
        }

    # Legacy fallback
    setting = Setting.objects.filter(
        parent_model=model,
        purpose='wc:workbench_fields',
    ).first()

    if not setting:
        # Create new wc:model record with columns section
        setting = Setting.objects.create(
            name=f'{model} Model Definition',
            ida=f'wc-model-{model}',
            parent_model=model,
            purpose='wc:model',
            scope='system',
            config={'columns': layout_data},
        )
        logger.info(f"[layout_pending] Created new wc:model Setting #{setting.id} for {model}")
        return {
            'setting_id': setting.id,
            'model': model,
            'status': 'created',
            'list_count': len(layout_data.get('list', [])),
            'views_count': len(layout_data.get('views', [])),
        }

    # Update legacy record
    old_list = [f.get('field') if isinstance(f, dict) else f
                for f in (setting.config or {}).get('list', [])[:4]]

    setting.config = layout_data
    setting.save(update_fields=['config', 'dt_modified'])

    new_list = [f.get('field') if isinstance(f, dict) else f
                for f in layout_data.get('list', [])[:4]]

    logger.warning(
        f"[layout_pending] APPLIED Setting #{setting.id} for {model}: "
        f"list {old_list} → {new_list}"
    )

    return {
        'setting_id': setting.id,
        'model': model,
        'status': 'applied',
        'list_count': len(layout_data.get('list', [])),
        'views_count': len(layout_data.get('views', [])),
    }
