# Email Validation — ZeroBounce Integration
**Review date:** 2026-08-31
**Status:** Scaffolded — service stub + Pydantic schema in place; API calls not yet wired

## Overview

Email validation through ZeroBounce. The service skeleton exists at
`apps/sync/services/email_verification.py` (provider-agnostic, currently returns
stub responses). The Pydantic schema `ZeroBounceValidation` is wired into
`ContactMetadata.zb`. The batch script and health rating assignment are not yet built.

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

**Not yet built.** The batch validation script (`validate_emails.py`) does not exist.
When built, it should be a management command (not a standalone script) at
`apps/core/management/commands/validate_emails.py`.

### What exists now

- **Service stub:** `apps/sync/services/email_verification.py` — resolves a Connection
  record (type `email_verification`), logs attempts as Bundle records, always returns
  `{"status": "stubbed", "deliverability": "unknown"}`.
- **Pydantic schema:** `common/schemas/contact.py` — `ZeroBounceValidation` with fields:
  domain, status, validated, free_email, sub_status, did_you_mean, smtp_provider.
  Stored at `ContactMetadata.zb`.
- **Normalizer:** `apps/sync/services/standards.py` — `normalize_email_result()` with
  status map (valid/invalid/risky/unknown).
- **Config:** `.env.template` has `ZEROBOUNCE_API_KEY=` (commented out).

### To activate

1. Set `ZEROBOUNCE_API_KEY` in `.env`
2. Create a Connection record: type=`email_verification`, config.provider=`zerobounce`
3. Replace stub logic in `email_verification.py` with actual ZeroBounce API call
4. Build the management command for batch validation

## Cost

- Each validation = 1 credit
- ZeroBounce pricing: ~$0.008/email at volume
- Re-validate every 6 months (default) — emails go stale

## Integration with Alice (planned)

None of these are implemented yet. When the API is wired:

1. **On new contact creation** — validate email before saving (single API call)
2. **On campaign send** — check health_rating >= 4 before including
3. **When user asks about a contact** — mention if email was removed and why
4. **Weekly report** — "X contacts need email updates (rating 0)"
5. **Suggest "did you mean"** — ZeroBounce sometimes returns a correction

## API Key

Stored in `.env` as `ZEROBOUNCE_API_KEY`. Never in code, never in git.
