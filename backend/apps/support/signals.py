from __future__ import annotations
from django.conf import settings
from django.apps import apps
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver

from common.refs.tasks import sync_action_denorm_refs

ACTION_MODEL_LABEL = getattr(settings, "WEBCLERK_ACTION_MODEL", "support.Action")

def _get_action_model():
    try:
        app_label, model_name = ACTION_MODEL_LABEL.split(".")
        return apps.get_model(app_label, model_name)
    except Exception:
        return None

def register_action_signals():
    Action = _get_action_model()
    if not Action:
        return

    @receiver(post_save, sender=Action, weak=False, dispatch_uid="action_refs_post_save")
    def _action_post_save(sender, instance, **kwargs):
        sync_action_denorm_refs(ACTION_MODEL_LABEL, instance.pk)

    # Dynamically bind m2m_changed for each M2M on Action (capture through in closure)
    for m2m in Action._meta.many_to_many:
        through = getattr(m2m.remote_field, "through", None)
        rel_name = m2m.name

        if not through:
            continue

        def _make_m2m_receiver(sender_through, rel_name_capture):
            @receiver(m2m_changed, sender=sender_through, weak=False, dispatch_uid=f"action_refs_m2m_{rel_name_capture}")
            def _action_m2m_changed(sender, instance, action, reverse, model, pk_set, **kwargs):
                ActionModel = _get_action_model()
                if ActionModel and isinstance(instance, ActionModel):
                    sync_action_denorm_refs(ACTION_MODEL_LABEL, instance.pk)
            return _action_m2m_changed

        _make_m2m_receiver(through, rel_name)