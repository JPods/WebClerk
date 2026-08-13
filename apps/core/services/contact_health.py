"""Contact data health metrics for dashboard cards."""
from apps.core.models import Contact


def get_contact_health(params: dict = None) -> dict:
    total = Contact.objects.count()
    null_email = Contact.objects.filter(email__isnull=True).count()
    null_phone = Contact.objects.filter(phone__isnull=True).count()
    null_both = Contact.objects.filter(email__isnull=True, phone__isnull=True).count()
    has_email_fk = Contact.objects.filter(email_id__isnull=False).count()
    has_phone_fk = Contact.objects.filter(phone_id__isnull=False).count()

    def pct(n):
        return round(n / total * 100, 1) if total else 0

    return {
        "metrics": [
            {"label": "Count", "value": f"{total:,}"},
            {"label": "Has Email", "value": f"{total - null_email:,}"},
            {"label": "Has Phone", "value": f"{total - null_phone:,}"},
            {"label": "No Email", "value": f"{null_email:,}"},
            {"label": "No Phone", "value": f"{null_phone:,}"},
            {"label": "No Either", "value": f"{null_both:,}"},
        ],
    }
