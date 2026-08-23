import pytest
from django.core.exceptions import ValidationError

from apps.products.models.service import Service, default_billing
from apps.products.models.item import Item

# Assuming an Item model exists accessible via Service.item FK chain. If not, tests should be adapted.

@pytest.mark.django_db
class TestServiceBilling:
    def test_add_rate_and_current_rate(self):
        item = Item.objects.create(name="Svc Item", kind=Item.KIND_SERVICE)
        svc = Service(item=item, description="Install", purpose="test")
        svc.add_rate(rate=100, unit="hour", min_minutes=30, dt_effective=1000)
        svc.save()
        cur = svc.current_rate("hour")
        assert cur is not None
        assert cur.get("rate") == 100
        assert cur.get("min_minutes") == 30


    def test_compute_charge_min_minutes_and_rounding(self):
        item = Item.objects.create(name="Consult Item", kind=Item.KIND_SERVICE)
        svc = Service(item=item, description="Consult")
        svc.billing = default_billing()
        svc.billing["tiers"].append({"unit": "hour", "rate": 150, "cost": 0, "min_minutes": 60, "dt_effective": 1})
        svc.billing["rounding"]["strategy"] = "HALF_UP"
        svc.clean()
        # 15 minutes requested but min billable 60 -> 1 hour * 150
        assert svc.compute_charge(minutes=15, unit="hour") == 150.0
        with pytest.raises(ValueError):
            svc.compute_charge(minutes=-1)

    def test_compute_charge_travel_and_caps(self):
        item = Item.objects.create(name="Field Item", kind=Item.KIND_SERVICE)
        svc = Service(item=item, description="Field Work")
        svc.billing = default_billing()
        svc.billing.update({"min_charge": 300, "max_charge": 400})
        svc.billing["tiers"].append({"unit": "hour", "rate": 120, "cost": 0, "min_minutes": 0, "dt_effective": 1})
        svc.billing["travel"].update({"per_mile": 2.5, "included_miles": 10})
        svc.clean()
        # 2 hours (120*2=240) + travel ( (25-10)*2.5 = 37.5 ) = 277.5 -> min_charge forces 300
        assert svc.compute_charge(minutes=120, miles=25) == 300.0
        # Large hours to exceed max: 5h=600 + travel 0 -> capped at 400
        assert svc.compute_charge(minutes=300, miles=0) == 400.0

    def test_invalid_currency_raises(self):
        item = Item.objects.create(name="Bad Cur Item", kind=Item.KIND_SERVICE)
        svc = Service(item=item, description="Invalid Cur")
        svc.billing = default_billing()
        svc.billing["currency"] = "US"  # invalid length
        with pytest.raises(ValidationError):
            svc.clean()

    def test_duplicate_tier_effective_raises(self):
        item = Item.objects.create(name="Dup Tier Item", kind=Item.KIND_SERVICE)
        svc = Service(item=item, description="Dup Tier")
        svc.billing = default_billing()
        svc.billing["tiers"].append({"unit": "hour", "rate": 100, "cost": 0, "min_minutes": 0, "dt_effective": 10})
        svc.billing["tiers"].append({"unit": "hour", "rate": 120, "cost": 0, "min_minutes": 0, "dt_effective": 10})
        with pytest.raises(ValidationError):
            svc.clean()

    def test_process_step_uniqueness(self):
        item = Item.objects.create(name="Proc Item", kind=Item.KIND_SERVICE)
        svc = Service(item=item, description="Proc")
        svc.process = {"steps": [
            {"name": "Pick", "minutes": 10},
            {"name": "pick", "minutes": 5},  # duplicate case-insensitive
            {"name": "Pack", "minutes": 15},
        ], "version":1}
        svc.clean()
        names = [s['name'].lower() for s in svc.process['steps']]
        assert names.count('pick') == 1

    def test_concurrency_row_version(self):
        item = Item.objects.create(name="Concurrency Item", kind=Item.KIND_SERVICE)
        svc = Service(item=item, description="Conc")
        svc.save()
        # Simulate reload
        fresh = Service.objects.get(pk=svc.pk)
        svc.description = "Conc Updated"  # stale instance version 0
        fresh.description = "Conc Fresh"
        fresh.save()  # increments version to 1 internally after save cycle
        assert fresh.row_version == 1
        # Attempt to save stale instance should raise ValidationError
        with pytest.raises(ValidationError):
            svc.save()
