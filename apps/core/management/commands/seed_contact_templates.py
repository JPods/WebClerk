"""
Seed example email and letter report templates for the Contact model.

Creates Report records with markdown bodies using {{contact.field}} tokens.
These appear in the Reports dialog (Cmd+P) when viewing a contact record.

Usage:
    python manage.py seed_contact_templates
"""
import re
from django.core.management.base import BaseCommand
from apps.core.models.report import Report


TEMPLATES = [
    {
        "name": "Welcome Email",
        "ida": "RPT-CONTACT-WELCOME",
        "output_type": "email",
        "category": "letter",
        "sort_order": 10,
        "description": "Onboarding email sent to new contacts after account creation",
        "config": {
            "subject": "Welcome to {{customer.display_name}}",
            "body": """# Welcome, {{contact.name_first}}!

Thank you for joining **{{customer.display_name}}**. We're glad to have you.

Here are your account details:

| | |
|---|---|
| **Name** | {{contact.name_first}} {{contact.name_last}} |
| **Email** | {{contact.email}} |
| **Account** | {{customer.ida}} |
| **Your Rep** | {{rep.display_name}} |

## What's Next?

- Browse our catalog and place your first order
- Set up your communication preferences
- Contact your rep at {{rep.email}} with any questions

We look forward to working with you.

Best regards,
**{{customer.display_name}}**
""",
        },
    },
    {
        "name": "Verify Contact Info",
        "ida": "RPT-CONTACT-VERIFY",
        "output_type": "email",
        "category": "letter",
        "sort_order": 20,
        "description": "Data quality check — confirm or correct contact details",
        "config": {
            "subject": "Please verify your contact information",
            "body": """Hi {{contact.name_first}},

We're updating our records and want to make sure your information is current.

**Please confirm or correct the following:**

| Field | Current Value |
|-------|---------------|
| Name | {{contact.name_prefix}} {{contact.name_first}} {{contact.name_last}} {{contact.name_suffix}} |
| Title | {{contact.title}} |
| Department | {{contact.department}} |
| Company | {{contact.company}} |
| Email | {{contact.email}} |
| Phone | {{contact.phone}} |
| Address | {{contact.address_full}} |

If everything looks correct, no action is needed.

If anything needs updating, simply reply to this email with your corrections.

Thank you,
**{{customer.display_name}}**
""",
        },
    },
    {
        "name": "Thank You Letter",
        "ida": "RPT-CONTACT-THANKYOU",
        "output_type": "print",
        "category": "letter",
        "sort_order": 30,
        "description": "Formal thank-you letter for printing or PDF",
        "config": {
            "subject": "Thank You",
            "body": """{{customer.display_name}}
{{customer.address_full}}

---

{{contact.name_prefix}} {{contact.name_first}} {{contact.name_last}}
{{contact.company}}
{{contact.address_full}}

Dear {{contact.name_first}},

Thank you for your continued partnership with **{{customer.display_name}}**. Your business is important to us, and we value the relationship we've built together.

We are committed to providing you with excellent products and responsive service. If there is anything we can do to improve your experience, please don't hesitate to reach out.

Your dedicated representative is **{{rep.display_name}}**, who can be reached at {{rep.email}} or {{rep.phone}}.

Sincerely,

_________________________
{{rep.display_name}}
{{customer.display_name}}
""",
        },
    },
    {
        "name": "We Miss You",
        "ida": "RPT-CONTACT-INACTIVE",
        "output_type": "email",
        "category": "letter",
        "sort_order": 40,
        "description": "Re-engagement email for contacts with no recent activity",
        "config": {
            "subject": "We miss you, {{contact.name_first}}!",
            "body": """Hi {{contact.name_first}},

It's been a while since we last heard from you, and we wanted to check in.

At **{{customer.display_name}}**, we're always working to improve our products and service. Here's what's new since your last visit:

- Updated product catalog with new arrivals
- Improved order tracking and delivery notifications
- New self-service tools for account management

We'd love to reconnect. Your account (**{{customer.ida}}**) is still active, and your rep **{{rep.display_name}}** is ready to help with anything you need.

**Reply to this email** or call {{rep.phone}} to get started.

Looking forward to hearing from you,
**{{customer.display_name}}**
""",
        },
    },
    {
        "name": "New Rep Introduction",
        "ida": "RPT-CONTACT-INTRO",
        "output_type": "email",
        "category": "letter",
        "sort_order": 50,
        "description": "Introduce a new sales rep to an existing contact",
        "config": {
            "subject": "Your new rep: {{rep.display_name}}",
            "body": """Dear {{contact.name_first}},

I'm writing to introduce myself as your new representative at **{{customer.display_name}}**.

**My contact information:**

| | |
|---|---|
| **Name** | {{rep.display_name}} |
| **Email** | {{rep.email}} |
| **Phone** | {{rep.phone}} |

I've reviewed your account history and I'm familiar with your needs. I'm here to ensure a smooth transition and to continue providing the level of service you expect.

Please don't hesitate to reach out with any questions, orders, or concerns. I look forward to working with you.

Best regards,
**{{rep.display_name}}**
{{customer.display_name}}
""",
        },
    },
    {
        "name": "Mailing Label",
        "ida": "RPT-CONTACT-LABEL",
        "output_type": "label",
        "category": "label",
        "sort_order": 60,
        "description": "Simple address label for envelopes or packages",
        "config": {
            "subject": "Mailing Label",
            "body": """{{contact.name_prefix}} {{contact.name_first}} {{contact.name_last}}
{{contact.company}}
{{contact.address_full}}
""",
        },
    },
]


class Command(BaseCommand):
    help = "Seed example email and letter report templates for the Contact model"

    def handle(self, *args, **options):
        created = 0
        existing = 0

        for tpl in TEMPLATES:
            # Extract tokens from body for discoverability
            tokens = sorted(set(re.findall(r'\{\{(\w+(?:\.\w+)*)\}\}', tpl["config"]["body"])))
            config = {**tpl["config"], "tokens_used": tokens}

            obj, was_created = Report.objects.get_or_create(
                ida=tpl["ida"],
                defaults={
                    "name": tpl["name"],
                    "description": tpl["description"],
                    "model_name": "contact",
                    "output_type": tpl["output_type"],
                    "category": tpl["category"],
                    "sort_order": tpl["sort_order"],
                    "config": config,
                },
            )
            if was_created:
                created += 1
                self.stdout.write(f"  Created: {tpl['name']} ({tpl['ida']}) [{tpl['output_type']}]")
            else:
                existing += 1
                self.stdout.write(f"  Exists:  {tpl['name']} ({tpl['ida']})")

        self.stdout.write(self.style.SUCCESS(
            f"\nContact reports: {created} created, {existing} already existed. "
            f"Total: {len(TEMPLATES)}."
            f"\n\nView in: Reports dialog (Cmd+P) on any contact record"
            f"\nResolve: POST /wcapi/resolve-template/"
            f"\nFields:  GET /wcapi/template-fields/?model=contact"
        ))
