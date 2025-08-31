from django.core.management.base import BaseCommand
from django.apps import apps
import inspect
import os

VALIDATE_TEMPLATE = (
    "    def api_validate_payload(self, data: dict, is_update: bool):\n"
    "        \"\"\"Model-specific validation (scaffold).\n\n"
    "        Populate errors list; return (ok, errors).\n"
    "        is_update True when existing record updated (id present).\n"
    "        \"\"\"\n"
    "        errors: list[str] = []\n"
    "        # Example checks (remove when implementing):\n"
    "        # if not is_update and not data.get('required_field'):\n"
    "        #     errors.append('required_field: missing')\n"
    "        return (len(errors) == 0, errors)\n"
)

PRE_TEMPLATE = (
    "    def pre_save_hook(self, data: dict):\n"
    "        \"\"\"Pre-save guard / normalization (scaffold).\n\n"
    "        Return a string to abort save with HTTP 400 or None to continue.\n"
    "        Keep lightweight (avoid heavy DB work).\n"
    "        \"\"\"\n"
    "        # Example: if not data.get('name'): return 'name: required'\n"
    "        return None\n"
)

POST_TEMPLATE = (
    "    def post_save_hook(self, data: dict):\n"
    "        \"\"\"Post-save synchronous side-effect (scaffold).\n\n"
    "        Return a string to append to response messages or None.\n"
    "        Heavy work should be deferred to async tasks.\n"
    "        \"\"\"\n"
    "        # Example: return 'saved <resource>'\n"
    "        return None\n"
)

class Command(BaseCommand):
    help = (
        "Scaffold api_validate_payload (and optionally pre/post hooks) for BaseModel descendants missing overrides. "
        "Use --include-hooks to also add pre_save_hook / post_save_hook stubs when they inherit defaults."
    )

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show planned changes without writing files')
        parser.add_argument('--app', type=str, default='', help='Limit to a specific app label')
        parser.add_argument('--include-hooks', action='store_true', help='Also scaffold pre_save_hook and post_save_hook if using BaseModel defaults')

    def handle(self, *args, **options):
        dry = options['dry_run']
        target_app = options.get('app') or ''
        modified: list[str] = []
        include_hooks = options.get('include_hooks')
        for model in apps.get_models():
            m = model
            if target_app and m._meta.app_label != target_app:
                continue
            # ensure subclass of BaseModel
            try:
                from common.models import BaseModel  # local import
            except Exception:
                continue
            if not issubclass(m, BaseModel):
                continue
            # if api_validate_payload overridden (not inherited from BaseModel), skip
            # Determine which stubs needed
            need_validate = False
            need_pre = False
            need_post = False
            try:
                if m.api_validate_payload.__qualname__.startswith('BaseModel.'):
                    need_validate = True
            except Exception:
                pass
            if include_hooks:
                try:
                    if m.pre_save_hook.__qualname__.startswith('BaseModel.'):
                        need_pre = True
                except Exception:
                    pass
                try:
                    if m.post_save_hook.__qualname__.startswith('BaseModel.'):
                        need_post = True
                except Exception:
                    pass
            if not any([need_validate, need_pre, need_post]):
                continue
            file = inspect.getsourcefile(m)
            if not file or not os.path.isfile(file):
                continue
            with open(file, 'r', encoding='utf-8') as fh:
                content = fh.read().splitlines()
            # insertion point: end of class definition area
            insert_at = None
            for idx, line in enumerate(content):
                if line.startswith(f'class {m.__name__}'):
                    for j in range(idx + 1, len(content)):
                        if content[j].startswith('class '):
                            insert_at = j
                            break
                    if insert_at is None:
                        insert_at = len(content)
                    break
            if insert_at is None:
                continue
            scaffold_lines: list[str] = []
            if need_pre:
                scaffold_lines.extend(PRE_TEMPLATE.splitlines())
                scaffold_lines.append("")
            if need_validate:
                scaffold_lines.extend(VALIDATE_TEMPLATE.splitlines())
                scaffold_lines.append("")
            if need_post:
                scaffold_lines.extend(POST_TEMPLATE.splitlines())
                scaffold_lines.append("")
            content[insert_at:insert_at] = scaffold_lines
            joined = '\n'.join(content)
            new_text = joined + ('\n' if not new_text_endswith_newline(joined) else '')
            if dry:
                added = ", ".join([p for p, need in [('pre_save_hook', need_pre), ('api_validate_payload', need_validate), ('post_save_hook', need_post)] if need])
                self.stdout.write(f"Would modify {file} (insert {added})")
            else:
                with open(file, 'w', encoding='utf-8') as fh:
                    fh.write(new_text)
                modified.append(file)
        if modified:
            self.stdout.write(self.style.SUCCESS(f"Added api_validate_payload scaffold to {len(modified)} file(s)."))
        elif not dry:
            self.stdout.write("No scaffolds added (all models already override or none matched).")
        if dry:
            self.stdout.write("Dry run complete.")

def new_text_endswith_newline(text: str) -> bool:
    return text.endswith('\n')
