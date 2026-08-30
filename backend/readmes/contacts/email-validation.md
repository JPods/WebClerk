# Email Validation — ZeroBounce Integration

## Overview

Every contact's email address is validated through ZeroBounce before any outbound
communication. Invalid, spamtrap, and abuse emails are automatically removed from
the contact's email field and archived in metadata for audit purposes.

## Health Rating Standard

| Rating | ZeroBounce Status | Meaning | Email Field | Action |
|:------:|---|---|---|---|
| **5** | valid | Confirmed deliverable | Kept | Safe to email |
| **4** | catch-all | Server accepts all (can't confirm) | Kept | Email with caution |
| **3** | unknown | Couldn't verify | Kept | Try once, re-validate in 90 days |
| **2** | do_not_mail | Role address, disposable | **Removed** | Don't email, keep record |
| **1** | spamtrap / abuse | Dangerous to send to | **Removed** | Flag, never email |
| **0** | invalid | Bad address / doesn't exist | **Removed** | Needs new email |

## How It Works

### What happens when email is removed (ratings 0, 1, 2)

The email is NOT deleted — it's moved from `contact.email` to `contact.metadata.email_history[]`:

```json
{
  "email_history": [
    {
      "email": "old.address@defunct-company.com",
      "status": "invalid",
      "sub_status": "does_not_accept_mail",
      "date": "2026-07-24",
      "action": "removed",
      "provider": "zerobounce"
    }
  ]
}
```

This ensures:
- **No accidental sends** — bad email is not in the email field
- **Full audit trail** — you can see what was there and why it was removed
- **Re-import safety** — dedup won't put a bad email back
- **Alice can explain** — "This contact's email bounced on July 24"

### ZeroBounce data stored

Full validation result stored in `contact.metadata.zb`:

```json
{
  "zb": {
    "status": "valid",
    "sub_status": "",
    "validated": "2026-07-24",
    "domain": "jpods.com",
    "smtp_provider": "g-suite",
    "free_email": false,
    "did_you_mean": null
  }
}
```

## Running Validation

### Check credits
```bash
cd /Users/williamjames/Documents/CommerceExpert/webClerk3
source venv/bin/activate
python scripts/validate_emails.py --check-credits
```

### Validate all unvalidated contacts
```bash
python scripts/validate_emails.py
```

### Validate a limited batch
```bash
python scripts/validate_emails.py --limit 100
```

### Dry run (see what would happen, no changes)
```bash
python scripts/validate_emails.py --dry-run --limit 50
```

### Re-validate contacts older than 90 days
```bash
python scripts/validate_emails.py --revalidate-days 90
```

### Check progress while running
```sql
SELECT health_rating, COUNT(*)
FROM contacts
WHERE is_active=true AND is_deleted=false
GROUP BY health_rating
ORDER BY health_rating;
```

## Cost

- Each validation = 1 credit
- ZeroBounce pricing: ~$0.008/email at volume
- Re-validate every 6 months (default) — emails go stale

## Integration with Alice

Alice should:
1. **On new contact creation** — validate email before saving (single API call)
2. **On campaign send** — check health_rating >= 4 before including
3. **When user asks about a contact** — mention if email was removed and why
4. **Weekly report** — "X contacts need email updates (rating 0)"
5. **Suggest "did you mean"** — ZeroBounce sometimes returns a correction

## API Key

Stored in `.env` as `ZEROBOUNCE_API_KEY`. Never in code, never in git.
