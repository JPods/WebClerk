#!/usr/bin/env bash
set +e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WC3_DIR="${ROOT_DIR}/../webClerk3"
PY_BIN="${WC3_DIR}/bin/python"

if [ ! -x "${PY_BIN}" ]; then
  if command -v python3 >/dev/null 2>&1; then
    PY_BIN="python3"
  elif command -v python >/dev/null 2>&1; then
    PY_BIN="python"
  else
    echo "[react-startup] Prime snapshot: python not found"
    exit 0
  fi
fi

if [ ! -d "${WC3_DIR}" ]; then
  echo "[react-startup] Prime snapshot: webClerk3 folder not found (${WC3_DIR})"
  exit 0
fi

(
  cd "${WC3_DIR}" || exit 0
  "${PY_BIN}" - <<'PY'
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')

try:
    import django
    django.setup()
    from apps.core.models import Setting
    from apps.orgs.models import OrgBase
except Exception as exc:
    print(f"[react-startup] Prime snapshot unavailable: {exc}")
    raise SystemExit(0)

setting = (
    Setting.objects
    .filter(purpose='db_defaults', name='primary_organization', is_active=True)
    .order_by('-id')
    .first()
)

if not setting:
    print('[react-startup] Prime setting: MISSING')
    raise SystemExit(0)

data = setting.data or {}
model_name = data.get('model_name') or data.get('org_type') or 'customer'
prime_id = data.get('id') or data.get('org_id')
print(f"[react-startup] Prime setting id={setting.id} model_name={model_name} id={prime_id} company={data.get('company')}")

if not prime_id:
    print('[react-startup] Prime org: MISSING id in setting.data')
    raise SystemExit(0)

try:
    prime_id = int(prime_id)
except Exception:
    print(f"[react-startup] Prime org: INVALID id value={prime_id}")
    raise SystemExit(0)

org = OrgBase.objects.filter(pk=prime_id).first()
if not org:
    print(f"[react-startup] Prime org: NOT FOUND id={prime_id}")
    raise SystemExit(0)

print(
    f"[react-startup] Prime org id={org.id} org_type={org.org_type} "
    f"company={org.company} phone={org.phone} email={org.email} "
    f"attention={getattr(org, 'attention', None)} address_full={getattr(org, 'address_full', None)}"
)
PY
)

exit 0
