#!/usr/bin/env python
"""Audit Customer table payload size to diagnose slow loading."""
import os, sys, django, json, time

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "webclerk3_api.settings")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from apps.orgs.models import Customer
from apps.orgs.serializers import CustomerSerializer

qs = Customer.objects.filter(is_active=True, is_deleted=False)
count = qs.count()
print(f"Customer count: {count}")

if count == 0:
    print("No customers found.")
    sys.exit(0)

# Time the serialization
start = time.time()
serializer = CustomerSerializer(qs, many=True)
data = serializer.data
elapsed = time.time() - start
print(f"Serialization time: {elapsed:.2f}s")

payload = json.dumps(data)
total_size = len(payload)
print(f"Total payload size: {total_size} bytes ({total_size/1024:.1f} KB, {total_size/1024/1024:.2f} MB)")
print(f"Avg per record: {total_size/count:.0f} bytes ({total_size/count/1024:.1f} KB)")

# Show field sizes for first record
first = dict(data[0])
print()
print("Field sizes for first record (sorted largest first):")
for k, v in sorted(first.items(), key=lambda x: len(json.dumps(x[1])), reverse=True):
    size = len(json.dumps(v))
    if size > 50:
        print(f"  {k}: {size} bytes ({size/1024:.1f} KB)")
    else:
        print(f"  {k}: {size} bytes")

# Aggregate: find which JSON fields are bloated across all records
print()
print("Aggregate field sizes across ALL records:")
field_totals = {}
for rec in data:
    for k, v in dict(rec).items():
        field_totals[k] = field_totals.get(k, 0) + len(json.dumps(v))

for k, total in sorted(field_totals.items(), key=lambda x: x[1], reverse=True):
    avg = total / count
    pct = total / total_size * 100
    print(f"  {k}: total={total/1024:.1f} KB, avg={avg:.0f} bytes/rec, {pct:.1f}%")
