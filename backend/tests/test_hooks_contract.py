"""The code-hook contract: one class per model, one method pair per verb.

Hooks are ``before_<verb>(self, ctx)`` / ``after_<verb>(self, ctx)`` on a registered
``ModelBehaviour`` (Bill, 2026-09-24). A hook named for a verb that does not exist would
never run, so it is a defect, not a spare.
"""
import inspect

import pytest

from apps.core.services import behaviours
from apps.core.services.verbs import VERBS


@pytest.mark.hooks
def test_every_hook_names_a_real_verb_and_takes_one_context():
    violations = []
    for model_key, behaviour in behaviours._REGISTRY.items():
        for name, fn in inspect.getmembers(type(behaviour), inspect.isfunction):
            moment, _, verb = name.partition('_')
            if moment not in ('before', 'after') or not verb:
                continue
            if verb not in VERBS:
                violations.append(f'{model_key}: {name} names no verb in {sorted(VERBS)}')
            params = tuple(inspect.signature(fn).parameters)
            if params != ('self', 'ctx'):
                violations.append(f'{model_key}: {name}{params} — expected (self, ctx)')
    assert not violations, 'Hook contract violations:\n' + '\n'.join(violations)


@pytest.mark.django_db
@pytest.mark.hooks
def test_no_model_carries_the_retired_save_hooks():
    """pre_save_hook / post_save_hook on models were a second code-hook mechanism."""
    from django.apps import apps
    carrying = [m.__name__ for m in apps.get_models()
                if hasattr(m, 'pre_save_hook') or hasattr(m, 'post_save_hook')]
    assert not carrying, f'models still carrying retired hooks: {carrying}'
