"""The orgs' code hooks (core/services/behaviours.py): one branch for every org model."""
from apps.core.services.behaviours import HookContext, ModelBehaviour, register

ORG_MODELS = ('customer', 'vendor', 'employee', 'manufacturer', 'rep', 'other_org')

#: The org a contact can belong to, by model: the contact's ForeignKey of the same name.
CONTACT_ROLES = ('customer', 'vendor', 'manufacturer', 'rep')


class OrgBehaviour(ModelBehaviour):
    #: Bill, 2026-10-16: staff whose customer search on a contact finds nothing make the org
    #: from that contact. `new` carries the contact's id and what they typed; the org is
    #: saved populated (an individual: the contact's attention is the company) and the
    #: contact is linked to it. Duplicates are the users' to clean up.
    SIGNALS = {'_from_contact': int, '_company': str}

    def before_save(self, ctx: HookContext) -> None:
        if (ctx.obj.config or {}).get('is_new'):
            source = _source_contact(ctx)
            if source is not None:
                _populate_from_contact(ctx.obj, source, ctx.data.get('_company'))
        # A new org is saved before anyone names it, and an org must have a company
        # (org_company_not_empty): the naked record carries a name to be replaced.
        if (ctx.obj.config or {}).get('is_new') and not (ctx.obj.company or '').strip():
            ctx.obj.company = f'New {type(ctx.obj)._meta.verbose_name}'

    def after_save(self, ctx: HookContext) -> None:
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
