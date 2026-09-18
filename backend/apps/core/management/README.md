# Core Management Command Registry

This registry tracks permanent core maintenance commands so operational workflows remain discoverable and stable.

## Command Catalog

### contact_communications_maintenance

- File: `apps/core/management/commands/contact_communications_maintenance.py`
- Service: `apps/core/services/contact_communications_maintenance.py`
- Purpose:
  - Loop through contact records and reconcile communication linkage across `Contact`, `Email`, `Phone`, `Domain`, and `Address`
  - Create missing communication records when scalar contact communication values exist
  - Claim matching unowned communication rows for the contact when present
  - Rebuild `Contact.refs.links.<type>` and ensure communication-side `refs.links.contact` includes the contact
- Options:
  - `--contact-id <id>`
  - `--limit <n>`
  - `--dry-run`
  - `--allow-reassign-owned`

## Operational Standard

- Treat listed commands as permanent maintenance interfaces.
- Keep command behavior idempotent whenever practical.
- Prefer adding new core maintenance capabilities as:
  1. Reusable service function in `apps/core/services/`
  2. Thin management command wrapper
  3. Entry in this registry with purpose and usage notes

## Examples

```bash
# Preview all contacts without writing updates
python manage.py contact_communications_maintenance --dry-run

# Process one contact
python manage.py contact_communications_maintenance --contact-id 41

# Process first 500 contacts
python manage.py contact_communications_maintenance --limit 500

# Allow moving rows currently assigned to a different contact
python manage.py contact_communications_maintenance --allow-reassign-owned
```
