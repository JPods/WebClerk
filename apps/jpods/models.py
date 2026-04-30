"""
JPods data models.

Pricing is stored in the standard WC3 Item model (kind="service").
Alice looks up the Item by SKU on every price_query call.

SKU convention: JPODS-{NETWORK_ID}-{ORIGIN}-{DESTINATION}
  e.g. JPODS-DEFAULT-S001-S003

Price levels map to Item.price keys:
  Customer.price_level="demo"     → Item.price["wholesale"]
  Customer.price_level="retail"   → Item.price["retail"]
  Customer.price_level="employee" → Item.price["sample"]
"""
