"""Bring stored JSON aspects and the Settings that name them into their schemas.

Each step moves data written in an older shape to the one its schema declares,
and renames Setting paths that pointed at the older shape. Dry run by default.

    python manage.py conform_aspects                  # report every step
    python manage.py conform_aspects --step shipping  # one step
    python manage.py conform_aspects --apply

Steps
  shipping  TransactionShipping on order/invoice/proposal/purchase/workorder:
            ship_to {address1, city_state_zip, …} → ShipToSnapshot,
            dt_shipped / dt_delivered '' → None, validated through the schema;
            wc:model Settings: flat leaf paths → the nested ones.
"""
from __future__ import annotations

import json
import re

from django.core.management.base import BaseCommand
from django.db import transaction

SHIPPING_MODELS = ('order', 'invoice', 'proposal', 'purchase', 'workorder')

# Flat shipping leaves the layouts used → the leaves the data actually has.
SHIPPING_PATH_RENAMES = {
    'shipping.freight': 'shipping.costs.freight',
    'shipping.fuel_surcharge': 'shipping.costs.fuel_surcharge',
    'shipping.insurance': 'shipping.costs.insurance',
    'shipping.handling': 'shipping.costs.handling',
    'shipping.estimated': 'shipping.costs.estimated',
    'shipping.actual': 'shipping.costs.actual',
    'shipping.customer_charge': 'shipping.costs.customer',
    'shipping.gross_weight': 'shipping.weight.gross',
    'shipping.weight_unit': 'shipping.weight.unit',
}


def _ship_to_snapshot(old: dict) -> dict:
    if not old or 'full_address' in old:
        return old or {}
    lines = [old.get('address1', ''), old.get('address2', ''), old.get('city_state_zip', '')]
    return {
        'company': old.get('company', ''),
        'attention': old.get('attention', ''),
        'full_address': '\n'.join(x for x in lines if x),
        'phone': old.get('phone', ''),
    }


def _epoch_or_none(v):
    return None if v in ('', None) else v


def rename_paths_in_settings(renames: dict, stdout, apply: bool) -> int:
    """Rename exact quoted path strings anywhere in Setting configs."""
    from apps.core.models.setting import Setting
    pattern = re.compile('"(' + '|'.join(re.escape(k) for k in renames) + ')"')
    changed = 0
    for s in Setting.objects.all().only('id', 'ida', 'config'):
        text = json.dumps(s.config or {})
        new_text, n = pattern.subn(lambda m: f'"{renames[m.group(1)]}"', text)
        if n:
            changed += 1
            stdout.write(f'  setting {s.id} {s.ida}: {n} path(s) renamed')
            if apply:
                s.config = json.loads(new_text)
                s.save(update_fields=['config'])
    return changed


class Command(BaseCommand):
    help = 'Conform stored aspects and Setting paths to their schemas (dry run unless --apply)'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')
        parser.add_argument('--step', choices=['shipping'], default=None)

    def handle(self, *args, **opts):
        apply = opts['apply']
        steps = [opts['step']] if opts['step'] else ['shipping']
        with transaction.atomic():
            for step in steps:
                getattr(self, f'step_{step}')(apply)
        self.stdout.write(self.style.SUCCESS('Applied.' if apply else 'Dry run — nothing saved.'))

    def step_shipping(self, apply: bool):
        from apps.core.constants.model_registry import MODEL_REGISTRY
        from common.schemas.transaction_envelopes import TransactionShipping

        self.stdout.write('shipping:')
        for key in SHIPPING_MODELS:
            model = MODEL_REGISTRY[key].import_model()
            reshaped = 0
            for rec in model.objects.all().only('id', 'shipping'):
                old = rec.shipping or {}
                new = dict(old)
                new['ship_to'] = _ship_to_snapshot(old.get('ship_to') or {})
                new['dt_shipped'] = _epoch_or_none(old.get('dt_shipped'))
                new['dt_delivered'] = _epoch_or_none(old.get('dt_delivered'))
                new = TransactionShipping.model_validate(new).model_dump()
                if new != old:
                    reshaped += 1
                    if apply:
                        model.objects.filter(pk=rec.pk).update(shipping=new)
            self.stdout.write(f'  {key}: {reshaped} records reshaped')
        n = rename_paths_in_settings(SHIPPING_PATH_RENAMES, self.stdout, apply)
        self.stdout.write(f'  settings: {n} records with flat shipping paths')
