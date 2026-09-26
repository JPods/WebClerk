"""The orgs' code hooks (core/services/behaviours.py): one branch for every org model."""
from apps.core.services.behaviours import HookContext, ModelBehaviour, register

ORG_MODELS = ('customer', 'vendor', 'employee', 'manufacturer', 'rep', 'other_org')


class OrgBehaviour(ModelBehaviour):
    def before_save(self, ctx: HookContext) -> None:
        # A new org is saved before anyone names it, and an org must have a company
        # (org_company_not_empty): the naked record carries a name to be replaced.
        if (ctx.obj.config or {}).get('is_new') and not (ctx.obj.company or '').strip():
            ctx.obj.company = f'New {type(ctx.obj)._meta.verbose_name}'


def register_orgs() -> None:
    for key in ORG_MODELS:
        register(key, OrgBehaviour())
