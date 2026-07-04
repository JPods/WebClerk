# Email System — Operations Guide
**Status:** Design complete | **Source:** Bill 2026-07-04

---

## Principle

Emails are actions with a delivery mechanism. No separate EmailTemplate, EmailQueue, or EmailOptOut models. The Report model stores templates. The Action model tracks sends.

---

## Architecture

```
Report (purpose='email', config.template = email body)
  → generate email from template + record data
    → send via SMTP (company_profile Setting has SMTP config)
      → Action created: task="Email sent: Invoice #123 to Smith"
        → refs.links.email_id = Gmail/Outlook message ID
        → refs.links.invoice_id = 123
        → refs.links.contact_id = 55
          → click email_id → opens in Gmail/Outlook
          → follow-up? action stays open
          → done? mark complete
```

---

## Standard Emails (stored as Report records)

| Report Name | Trigger | Template |
|---|---|---|
| Invoice Notification | Invoice created/shipped | "Your invoice #{ida} for ${total} is attached" |
| Order Confirmation | Order confirmed | "Your order #{ida} has been received" |
| Proposal Sent | Proposal created | "Please review proposal #{ida}" |
| Statement | Monthly/on-demand | Statement PDF attached |
| Past Due Notice | Aging > 30 days | "Invoice #{ida} is past due by {days} days" |
| Shipping Notification | Order shipped | "Your order #{ida} has shipped via {carrier}" |
| Payment Receipt | Payment received | "We received your payment of ${amount}" |

Each is a Report record with `config.delivery_type = 'email'` and `config.template` containing the email body template with merge fields.

---

## Email = Action

Sending an email creates an Action:

```json
Action = {
  task: {en: "Email: Invoice #123 sent to Smith Co"},
  status: "Done",              // or "Backlog" if follow-up needed
  kanban_column: "Done",
  assigned_to: {id: 69},       // who sent it
  refs: {
    links: {
      email_id: "<msg-id@gmail.com>",     // external email ID — clickable
      invoice_id: 123,
      contact_id: 55
    }
  }
}
```

Click `email_id` → opens the email in Gmail/Outlook (protocol handler).

---

## MySalesAndService = Action Query

WC2 had a separate MySalesAndService view. WC3: it's just Actions filtered by user.

```python
# My tasks (everything assigned to me)
Action.objects.filter(assigned_to__id=user_id, status__in=['Backlog', 'In Progress'])

# My emails needing follow-up
Action.objects.filter(assigned_to__id=user_id, task__en__startswith='Email:', status='Backlog')
```

DataBrowser shows this. Spawn links on Contact show all Actions for that contact.

---

## SMTP Configuration

In company_profile Setting (already built):

```json
config.accounting.email = {
  host: "smtp.gmail.com",
  port: 587,
  user: "orders@jpods.com",
  use_tls: true
}
```

Per-user SMTP possible via Contact.prefs (from EA_Email Composer mining — per-user config, not global).

---

## Opt-Out

No separate table. `Contact.prefs.email_opt_out = true` or `Contact.metadata.email_opt_out = true`. The send service checks before sending. Simple, queryable, on the record that matters.

---

## What's NOT Built Yet

1. Email send service (compose from Report template + data, send via SMTP, create Action)
2. Report records for standard emails (seed like we seeded the 28 reports)
3. Retry/queue mechanism (ScheduledTask for failed sends)
4. Opt-out check in send path

---

## Files

| File | Status | Purpose |
|------|--------|---------|
| `apps/core/models/action.py` | Exists | Action records for email tracking |
| `apps/core/models/report.py` | Exists | Report records store email templates |
| `apps/core/management/commands/seed_company_settings.py` | Exists | SMTP config in company_profile |
| Email send service | Needs building | Compose + send + create Action |
