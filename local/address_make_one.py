# You can run this in Django shell or create a management command
# To open Django shell: python manage.py shell

from apps.communications.models.address import Location
from django.utils import timezone

# Create address record for Jane Doe
jane_address = Location.objects.create(
    address1="123 Main Street",
    address2="Apt 4B",
    address_type="residential",
    city="San Francisco",
    state="CA",
    zip="94102",
    country="USA",
    instructions="Ring doorbell twice. Gate code is 1234.",
    latitude=37.7749,
    longitude=-122.4194,
    full="123 Main Street, Apt 4B, San Francisco, CA 94102, USA",
    comment="Primary residence address",
    dt_verified=0,
    refs={
        "keywords": "main,street,apartment,residential,san,francisco",
        "tags": ["primary", "verified", "residential"],
        "links": {"contact_name": "Jane Doe"}
    },
    metadata={
        "security": "verified",
        "priority": "high",
        "profiles": ["primary_address"],
        "health": {
            "rating": {"value": 5, "dt": 0, "contact_id": 0}
        }
    },
    pres={
        "preferred_delivery": True,
        "billing_address": True
    }
)

print(f"Created address: {jane_address}")
print(f"Location UUID: {jane_address.uuid}")