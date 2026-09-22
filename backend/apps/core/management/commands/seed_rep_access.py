"""A rep gets a salesperson's fields, on their own customers and documents.

Bill, 2026-09-20: *"Reps need to behave like staff"*, then
*"Reps match sales but only for customers and order to which their rep_id is assigned."*

That is the access model working as designed: **fields by enumeration, rows by scope**.
The field lists are copied from sales — same view, same edit, no separate list to drift —
and the row rule is the rep org assigned on the contact (``contacts.rep_id``).

Before this, 'rep' sat in PORTAL_ROLES, so view_edit_convert stripped opaque leaves from
its view and trimmed edit to match: 168 edit leaves against sales' 469 on an order, and
zero on an invoice.

    manage.py seed_rep_access            # show what would change
    manage.py seed_rep_access --apply
"""
from django.core.management.base import BaseCommand

from apps.core.services import access

#: The rows a rep may touch: the ones carrying their rep org. The assignment is a field
#: on the record (Bill, 2026-09-20: "We need a rep_id (not FK) and attention_rep in
#: customer, proposal, order"), not something inferred by joining through contacts — so
#: the scope is one indexed column on the row itself.
REP_SCOPE = {
    'order':    {'rep_id__in': '$user.org_ids.rep'},
    'quote':    {'rep_id__in': '$user.org_ids.rep'},
    'customer': {'rep_id__in': '$user.org_ids.rep'},
    # An invoice has no rep_id of its own; it inherits the order's. A rep sees theirs
    # through the order until that is decided — invoice is deliberately not scoped here.
}

#: Models a rep reads as sales does and never writes. A rep cannot put a line on a
#: proposal without seeing what the item is and what it sells for (Bill, 2026-09-20: "they
#: can access items in proposals and orders. If they cannot do that without accessing the
#: item model, then we give them access to items as well") — and "They cannot write to
#: items". Held here rather than inherited from sales, so a later grant to sales cannot
#: quietly hand a rep the catalogue. An item belongs to no rep, so there is no row scope.
REP_READ_ONLY = ('item',)


class Command(BaseCommand):
    help = "Give rep the sales field lists, scoped to their assigned customers and documents."

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):
        from apps.core.models.setting import Setting

        apply_changes = options['apply']
        changed = 0

        targets = [(key, scope) for key, scope in REP_SCOPE.items()]
        targets += [(key, None) for key in REP_READ_ONLY]
        for key, scope in targets:
            setting = (Setting.objects.filter(purpose='wc:model', parent_model=key).first())
            if setting is None:
                self.stdout.write(self.style.WARNING(f"{key}: no wc:model Setting"))
                continue

            config = dict(setting.config or {})
            acc = dict(config.get('access') or {})
            roles = dict(acc.get('roles') or {})
            sales = roles.get('sales')
            if not sales:
                self.stdout.write(self.style.WARNING(f"{key}: no sales block to match"))
                continue

            rep = dict(roles.get('rep') or {})
            before_view = len(access.expand_sets(rep.get('view') or [], acc.get('sets') or {}))
            before_edit = len(access.expand_sets(rep.get('edit') or [], acc.get('sets') or {}))

            # The same lists, by reference where sales uses a set — no second list to drift.
            read_only = key in REP_READ_ONLY
            rep['view'] = list(sales.get('view') or [])
            rep['edit'] = [] if read_only else list(sales.get('edit') or [])
            rep['create'] = False if read_only else sales.get('create', True)
            rep['delete'] = False                    # a rep does not delete the company's records
            if scope is None:
                rep['scope'] = dict(sales.get('scope') or {})
                rep['edit_scope'] = dict(sales.get('edit_scope') or sales.get('scope') or {})
            else:
                rep['scope'] = dict(scope)           # rows: only what is assigned to them
                rep['edit_scope'] = dict(scope)
            roles['rep'] = rep

            after_view = len(access.expand_sets(rep['view'], acc.get('sets') or {}))
            after_edit = len(access.expand_sets(rep['edit'], acc.get('sets') or {}))
            changed += 1
            self.stdout.write(
                f"  {key}/rep: view {before_view} -> {after_view}, "
                f"edit {before_edit} -> {after_edit}, "
                f"scope {list(scope)[0] if scope else 'as sales'}")

            if apply_changes:
                acc['roles'] = roles
                config['access'] = acc
                problems = access.validate_access(key, acc)
                if problems:
                    self.stdout.write(self.style.ERROR(
                        f"  {key}: refused — {problems[:3]}"))
                    changed -= 1
                    continue
                setting.config = config
                setting._setting_update_authorized = True
                setting.save(update_fields=['config', 'dt_modified', 'version'])
                access.clear_cache(key)

        verb = 'Updated' if apply_changes else 'Would update'
        self.stdout.write(self.style.SUCCESS(f"{verb} {changed} rep block(s)."))
        if not apply_changes and changed:
            self.stdout.write("Dry run — pass --apply to write.")
