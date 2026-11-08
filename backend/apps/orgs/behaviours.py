"""The orgs' code hooks (core/services/behaviours.py): one branch for every org model."""
from apps.core.services.behaviours import HookContext, ModelBehaviour, register
from apps.orgs.services.contact_linking import (
    CONTACT_ROLES, contact_values, contacts_of, rename_contacts)

ORG_MODELS = ('customer', 'vendor', 'employee', 'manufacturer', 'rep', 'other_org')


class OrgBehaviour(ModelBehaviour):
    #: Bill, 2026-10-16: staff whose customer search on a contact finds nothing make the org
    #: from that contact. `new` carries the contact's id and what they typed; the org is
    #: saved populated (an individual: the contact's attention is the company) and the
    #: contact is linked to it. Duplicates are the users' to clean up.
    SIGNALS = {'_from_contact': int, '_company': str}

    def before_save(self, ctx: HookContext) -> None:
        source = None
        if (ctx.obj.config or {}).get('is_new'):
            source = _source_contact(ctx)
            if source is not None:
                _populate_from_contact(ctx.obj, source, ctx.data.get('_company'))
                _take_source_name(ctx, source.source_name)
        if source is None:
            _follow_primary_contact(ctx)
        # A new org is saved before anyone names it, and an org must have a company
        # (org_company_not_empty): the naked record carries a name to be replaced.
        if (ctx.obj.config or {}).get('is_new') and not (ctx.obj.company or '').strip():
            ctx.obj.company = f'New {type(ctx.obj)._meta.verbose_name}'

    def after_save(self, ctx: HookContext) -> None:
        if ctx.is_update and 'company' in ctx.changed:    # at birth the contact's own save takes the name
            _rename_contacts(ctx)
        source = getattr(ctx.obj, '_from_contact', None)
        if source is None:
            return
        role = ctx.model_key if ctx.model_key in CONTACT_ROLES else None
        if role and getattr(source, f'{role}_id') != ctx.obj.pk:
            setattr(source, f'{role}_id', ctx.obj.pk)
            source.save()                         # Contact.save takes the company name
        # Populated, not naked: nothing for Alice's sweep of untouched new records.
        config = dict(ctx.obj.config or {})
        if config.pop('is_new', None) is not None:
            type(ctx.obj).objects.filter(pk=ctx.obj.pk).update(config=config)
            ctx.obj.config = config
        ctx.messages.append(f'{ctx.model_key} made from contact #{source.pk}')


def _follow_primary_contact(ctx: HookContext) -> None:
    """An org shows its primary contact's name and email (Bill, 2026-10-31): a de-normalized
    value is changed on the record it comes from, never typed here. Choosing another primary
    contact — one of this org's own — takes that contact's values."""
    from apps.core.services.door import Refused
    org = ctx.obj
    if 'contact_id' in ctx.changed and org.contact_id:
        if not contacts_of(org).filter(pk=org.contact_id).exists():
            raise Refused(400, 'not_this_orgs_contact',
                          f'Contact #{org.contact_id} is not one of this {ctx.model_key}\'s contacts: '
                          f'add it in the Contacts panel first.', {'contact_id': org.contact_id})
        for k, v in contact_values(org.contact_id).items():
            setattr(org, k, v)
        from apps.core.models import Contact
        _take_source_name(ctx, Contact.objects.filter(pk=org.contact_id)
                          .values_list('source_name', flat=True).first())
        return
    typed = sorted(k for k in ('attention', 'email') if k in ctx.changed)
    if typed and org.contact_id:
        raise Refused(400, 'copied_value',
                      f'{", ".join(typed)} {"is" if len(typed) == 1 else "are"} copied from contact '
                      f'#{org.contact_id}: change {"it" if len(typed) == 1 else "them"} on the contact, '
                      f'or choose another primary contact.', {'fields': typed, 'contact_id': org.contact_id})


def _take_source_name(ctx: HookContext, source_name) -> None:
    """An org made from, or given, a contact takes the contact's source_name when its own is
    blank (Bill, 2026-11-08: "it should transfer the source_name from the contact if one is
    assigned") — the blanks-only rule defaults follow: a source_name in the same payload wins."""
    if source_name and 'source_name' not in ctx.data and not (ctx.obj.source_name or '').strip():
        ctx.obj.source_name = source_name


def _rename_contacts(ctx: HookContext) -> None:
    """The org's name changed: its contacts follow (contact_linking.rename_contacts). Only a
    save that changed `company` pays for it."""
    result = rename_contacts(ctx.actor, ctx.obj)
    if result['renamed']:
        n = len(result['renamed'])
        ctx.messages.append(f'{n} contact{"" if n == 1 else "s"} renamed to {ctx.obj.company}')
    for held in result['held']:
        ctx.messages.append(f'contact #{held["id"]} is being edited by {held["held_by"]}: '
                            f'not renamed — save it again when they leave it')


def _source_contact(ctx: HookContext):
    """The contact named by _from_contact, if this actor can see it — else refused."""
    contact_id = ctx.data.get('_from_contact')
    if contact_id in (None, ''):
        return None
    from apps.core.services.door import Refused
    from apps.core.services.record_serialize import visible_queryset
    _cls, qs = visible_queryset('contact', actor=ctx.actor)
    contact = qs.filter(pk=contact_id).first()
    if contact is None:
        raise Refused(404, 'from_contact_not_found',
                      f'Contact #{contact_id} is not one you can make an org from.',
                      {'_from_contact': contact_id})
    return contact


def _populate_from_contact(org, contact, typed) -> None:
    """The org points at the contact's own communication records (they belong to the
    contact; one source, no copies) and takes the contact as its primary contact."""
    name = (contact.attention or contact.get_full_name() or '').strip()
    org.company = (typed or '').strip() or name or org.company
    org.attention = name or org.attention
    org.contact_id = contact.pk
    org.email = contact.email or org.email
    for pointer in ('email_id', 'phone_id', 'address_id', 'domain_id'):
        setattr(org, pointer, getattr(contact, pointer) or getattr(org, pointer))
    org._from_contact = contact


def register_orgs() -> None:
    for key in ORG_MODELS:
        register(key, OrgBehaviour())
