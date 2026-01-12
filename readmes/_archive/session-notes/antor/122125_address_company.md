# Address / Company rename notes

author: antor ahmed
time: 2025-12-21 8:33 UTC+6

📌 **Summary**

This note documents the recent changes introduced to prefer the term **`company`** instead of `display_name` on the org model, and the related `Location -> Address` model rename + compatibility shim. These changes were made in a backward-compatible way (no DB schema change yet) and include small admin/serializer/docs updates and compatibility shims where appropriate.

---

## 🔧 Changes made (high level)

- Org model: prefer `company` (new alias property on `OrgBase`) while keeping the DB-backed column `display_name` for now.
- Exposed `company` in API `to_universal_dict` while **keeping** `display_name` (deprecated) for compatibility.
- Admin: show `company` in list views (search still uses `display_name` DB column).
- Serializer: `CustomerSerializer` now exposes `company` instead of `display_name`.
- Common mapping & docs updated to reference `company` where appropriate.
- `Location` model split: the real implementation moved to `apps.communications.models.address.Address`; `apps.communications.models.location` now contains a compatibility shim that re-exports `Address` as `Location` and emits a DeprecationWarning.
- Tests/docs adjusted to use `Address` and new `company` naming.

---

## 🗂 Files changed (non-exhaustive, important entries)

- apps/orgs/models/base.py
  - Added `company` property (alias for `display_name`) and updated `to_universal_dict()` and `keywords_source`.
- apps/orgs/admin.py
  - List display updated to show `company`.
- apps/orgs/serializers/customer_serializer.py
  - Schema updated to include `company` in `fields`.
- common/models.py
  - Universal mapping updated to show `company` for `orgbase`.
- readmes/*
  - `readmes/antor/121525_denormalized_links.md`, `readmes/model-fields.json` and other docs updated to reference `company`.
- apps/communications/models/address.py
  - New file containing the `Address` implementation (keeps db_table = `locations`).
- apps/communications/models/location.py
  - Compatibility shim: `Location = Address` with DeprecationWarning.
- various tests and readmes updated (e.g., communications tests to import `Address`).


## 📍 Address (Location) rename details

- **Rationale:** move from the ambiguous `Location` name to **`Address`** for clarity; avoid immediate DB migrations by keeping the existing `locations` table and providing a compatibility shim.

- **Files changed (detailed):**
  - `apps/communications/models/address.py` — **new** implementation file (keeps `db_table = 'locations'`).
  - `apps/communications/models/location.py` — **compatibility shim** that re-exports `Address` as `Location` and emits a `DeprecationWarning` on import.
  - `apps/communications/tests/test_location_formatting.py` — imports switched to `Address` and tests remain functionally the same.
  - `apps/communications/tasks.py` — uses `apps.get_model('communications', 'Address')` for verification flows.
  - `apps/core/constants/model_registry.py` — registry entry updated to `apps.communications.models.address.Address` (key remains `location`).
  - `webclerk3_api/settings.py` — `WCAPI_BLESSED_MODELS['location']` now points to `communications.Address` for API routing and client mappings.
  - Docs & readmes: `readmes/reset.md`, `readmes/location-verification.md`, `readmes/model-registry.{csv,json,md}`, `readmes/rules.md`, and others updated to reference `Address` where appropriate.

- **Backwards compatibility:** code importing `apps.communications.models.location.Location` will continue to work because of the shim, but will get a `DeprecationWarning`. Plan to remove shim after deprecation period.

- **Testing & verification:**
  - Run `pytest apps/communications` to validate formatting and helper tests.
  - Run `python manage.py check` to ensure registry and settings are valid.
  - Smoke-test API endpoints for `locations` (`/wcapi/locations/`) to ensure no routing break.

- **Next steps / follow-up work:**
  - Consider updating public docs and client SDKs to refer to `Address` instead of `Location`.
  - Optionally rename registry endpoint/endpoint labels in next minor release if you want the external API to use `/wcapi/addresses/` (requires versioning & migration planning).

---

## 🛠 Implementation notes (code)

- `OrgBase.company` implementation (added as alias):

```py
@property
def company(self) -> str:
    return getattr(self, 'display_name', '')

@company.setter
def company(self, value: str) -> None:
    setattr(self, 'display_name', value)
```

- `to_universal_dict()` now contains both keys for a transitional period:

```py
base.update({
  "org_type": self.org_type,
  "company": self.company,
  "display_name": self.display_name,  # deprecated
  "status": self.status,
  "is_active": self.is_active,
})
```

- `apps/communications/models/location.py` is now a thin shim that warns on import and re-exports `Address` as `Location`:

```py
from apps.communications.models.address import Address
warnings.warn("...deprecated...", DeprecationWarning)
Location = Address
```

---

## ✅ Migration plan & recommended steps

> Important: no DB column was renamed yet — `display_name` remains the DB-backed field. The approach taken is intentionally safe so we can change behavior in code without immediate schema churn.

1. Short-term (current): keep `display_name` as DB column, use `company` in code via alias property (done).
2. Prep for DB rename (optional/next release):
   - Add a migration that renames the model field from `display_name` to `company` using Django's `RenameField` if you want the field name to change in the model and DB simultaneously.
   - Alternatively, change the model to declare `company = models.CharField(..., db_column='display_name')`, then add a migration to make that explicit. Useful when you want code to reference `company` while DB stays unchanged.
3. Post-rename: update index/constraint names (if you want `org_company_not_empty`), tests, fixtures, and any DB-dependent code.
4. Remove `display_name` alias after a deprecation period and remove compatibility warnings.

Migration commands (examples):

```bash
python manage.py makemigrations apps.orgs
python manage.py migrate
pytest apps.orgs.tests
python manage.py check
```

---

## 🔁 Tests & verification checklist

- [ ] Run `pytest apps/orgs` and `pytest apps/communications` to ensure no regressions.
- [ ] Run full test suite if CI resources permit.
- [ ] Verify admin UI shows `company` and searching still works.
- [ ] Verify API responses include `company` and accept writes mapped into `display_name` (if using serializer changes).
- [ ] If renaming DB column: run migration on staging, verify data integrity and indexes.

---

## ⚠️ Notes & follow-ups

- Update any external API clients or frontend components that currently read/write `display_name` — they should switch to `company` during the migration window.
- Consider adding a short deprecation header to API responses for one release if you want to accelerate client upgrades.
- After a safe period, remove the `display_name` compatibility code.

---

If you want, I can:
- Draft the migration file to rename the column (with `RenameField` or `db_column` approach).
- Run the `apps/orgs` and `apps/communications` tests and report failures.
- Scan for remaining doc/test references to `display_name` and propose batch fixes.

💡 Next step: confirm whether you'd like me to generate the migration to rename the column now or keep the code-only alias for another release.