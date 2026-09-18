"""wcapi_probe.py — run authorization probes against a real database, safely.

    cd backend && venv/bin/python manage.py shell < tools/wcapi_probe.py
    # or, to write your own cases:
    #   from tools.wcapi_probe import Probe, as_user
    #   p = Probe()
    #   p.case("customer cannot escalate",
    #          lambda: as_user(MORGAN).post("/wcapi/save/", {...}, format="json").status_code,
    #          blocked_when=lambda code: code == 403)
    #   p.report()

Why this exists
---------------
Authorization bugs only show up against real data: real roles, real org links, real
policy rows. Fixtures agree with whatever the code currently does, which is how the
2026-09-15 bypasses survived a passing test suite and a hand-written probe run.

So these probes hit the live database — and every single one runs inside
`transaction.atomic()` that is always rolled back by raising `_Rollback`. A probe that
successfully escalates a privilege leaves nothing behind. Read the result, not the row.

Two rules learned the hard way (2026-09-15):

1. `APIClient(SERVER_NAME="localhost")`, or every request 400s on DisallowedHost and
   you will read a wall of "blocked" that proves nothing.
2. Assert on a CHANGE, not on a state. A probe that checked `is_superuser is True`
   against a contact who was ALREADY a superuser reported a bypass that did not exist.
   Capture the value before, and require the probe to have moved it.

Use `hashers.check_password(raw, encoded)` for password checks, never
`user.check_password()`, which can rehash and save.
"""
from __future__ import annotations

from django.db import transaction
from rest_framework.test import APIClient

from apps.core.models import Contact


class _Rollback(Exception):
    """Carries the probe's result back out of the atomic block."""


def as_user(user_or_id, **client_kwargs):
    """An APIClient authenticated as a contact (or anonymous when passed None)."""
    client = APIClient(SERVER_NAME="localhost", **client_kwargs)
    if user_or_id is not None:
        user = user_or_id if isinstance(user_or_id, Contact) else Contact.objects.get(pk=user_or_id)
        client.force_authenticate(user=user)
    return client


def value_of(model, pk, field):
    """Current value of one field — for before/after comparison."""
    return getattr(model.objects.get(pk=pk), field, None)


class Probe:
    """A suite of attack cases. Each case is attempted, then rolled back."""

    def __init__(self):
        self.results: list[tuple[bool, str, object]] = []

    def case(self, name, attempt, blocked_when):
        """Run `attempt` inside a rolled-back transaction.

        `blocked_when(result)` returns True when the attack FAILED to get through —
        i.e. the system behaved correctly. Anything else is reported as VULNERABLE,
        including an unexpected exception, because a probe that errored proves nothing.
        """
        try:
            with transaction.atomic():
                raise _Rollback(attempt())
        except _Rollback as rolled_back:
            result = rolled_back.args[0]
        except Exception as exc:  # noqa: BLE001 - an erroring probe is not a passing probe
            result = f"EXC {type(exc).__name__}: {exc}"[:160]
        try:
            ok = bool(blocked_when(result))
        except Exception as exc:  # noqa: BLE001
            ok, result = False, f"ASSERTION FAILED {type(exc).__name__}: {exc} | {result}"[:200]
        self.results.append((ok, name, result))
        return ok

    def report(self, verbose=True):
        """Print each case and return True when every attack was blocked."""
        for ok, name, result in self.results:
            if verbose or not ok:
                print(f"{'blocked' if ok else 'VULNERABLE':<11} {name} -> {str(result)[:160]}")
        vulnerable = [name for ok, name, _ in self.results if not ok]
        print(f"\n{len(self.results) - len(vulnerable)}/{len(self.results)} blocked")
        if vulnerable:
            print("VULNERABLE: " + ", ".join(vulnerable))
        return not vulnerable


# ── Default suite: the 2026-09-15 bypasses, kept as regressions ───────────────
def default_suite(customer_id=10975, vendor_id=10976):
    """Attacks that were reproduced against this codebase and then closed.

    Pass ids for a non-privileged customer and vendor contact in the current database.
    """
    from apps.products.models import Item
    from apps.sync.models import Connection

    p = Probe()
    C = customer_id

    def save(payload, uid=C):
        return as_user(uid).post("/wcapi/save/", payload, format="json").status_code

    was_superuser = value_of(Contact, C, "is_superuser")
    p.case("dot-path: __dict__.is_superuser on self",
           lambda: (save({"model_name": "contact", "id": C, "__dict__.is_superuser": True}),
                    value_of(Contact, C, "is_superuser")),
           lambda r: r[1] == was_superuser)

    # Compare a boolean, never the hash itself — probe output gets pasted into logs
    # and handoffs, and a credential that leaves the database in a status line has
    # still left the database.
    other_pw = value_of(Contact, vendor_id, "password")
    p.case("dot-path: __dict__.password on another contact",
           lambda: (save({"model_name": "contact", "id": vendor_id,
                          "__dict__.password": "pbkdf2_sha256$attacker"}),
                    value_of(Contact, vendor_id, "password") == other_pw),
           lambda r: r[1] is True)

    p.case("selector path: is_superuser[x=y]",
           lambda: (save({"model_name": "contact", "id": C, "is_superuser[x=y]": True}),
                    value_of(Contact, C, "is_superuser")),
           lambda r: r[1] == was_superuser)

    was_roles = (value_of(Contact, C, "refs") or {}).get("roles")
    p.case("refs.roles admin on self",
           lambda: (save({"model_name": "contact", "id": C, "refs.roles": ["admin"]}),
                    (value_of(Contact, C, "refs") or {}).get("roles")),
           lambda r: r[1] == was_roles)

    p.case("mint a Natalie connection token",
           lambda: (save({"model_name": "connection", "name": "natalie", "status": "active",
                          "config": {"token": "probe-minted"}}),
                    Connection.objects.filter(config__token="probe-minted").exists()),
           lambda r: r[1] is False)

    def forge_order():
        item = Item.objects.filter(is_active=True).first()
        return save({"model_name": "order", "status": "released",
                     "lines": [{"item": {"item_id": item.pk}, "quantity": {"active": 5},
                                "price": {"unit": 0.01}, "_dirty": True}]})
    p.case("transaction lines via /wcapi/save/", forge_order, lambda code: code != 200)

    p.case("REGRESSION: own name_first still editable",
           lambda: save({"model_name": "contact", "id": C,
                         "name_first": {"mode": "update", "value": "ProbeName"}}),
           lambda code: code == 200)
    return p


if __name__ == "__main__" or True:  # `manage.py shell <` executes with __name__ == "builtins"
    default_suite().report()
