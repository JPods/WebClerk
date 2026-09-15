"""Quick verification of remote DB cleanup."""
import psycopg2

conn = psycopg2.connect(
    host="76.13.185.210", port=5432,
    dbname="commerce_expert", user="postgres", password="wc_psql_server",
    connect_timeout=10
)

out = open("/tmp/verify_out.txt", "w")
cur = conn.cursor()

# 1. Check NULL UUIDs across all populated tables
tables = [
    "actions", "contacts", "emails", "invoices", "invoice_lines",
    "locations", "orders", "order_lines", "orgs_orgbase", "phones",
    "products_item", "proposals", "proposal_lines", "settings",
    "templates", "work_orders", "work_order_lines", "products_warehouse",
    "products_serial", "products_siteinventory", "products_inventorymovement",
    "products_inventorylayer", "products_billofmaterial", "pending", "domains",
]
total_null = 0
for t in tables:
    try:
        cur.execute(f"SELECT count(*) FROM {t} WHERE uuid IS NULL")
        n = cur.fetchone()[0]
        if n > 0:
            out.write(f"  WARNING: {t} has {n} NULL UUIDs\n")
        total_null += n
    except Exception as e:
        out.write(f"  SKIP: {t} ({e})\n")
        conn.rollback()
out.write(f"\n[1] NULL UUIDs remaining: {total_null}\n")

# 2. Orphaned actions.contact_id
cur.execute("""
    SELECT count(*) FROM actions a
    WHERE a.contact_id IS NOT NULL
      AND NOT EXISTS (SELECT 1 FROM contacts c WHERE c.id = a.contact_id)
""")
orphans = cur.fetchone()[0]
out.write(f"[2] Orphaned actions.contact_id: {orphans}\n")

# 3. _id_id columns
cur.execute("""
    SELECT count(*) FROM information_schema.columns
    WHERE table_schema = 'public' AND column_name LIKE '%%_id_id'
""")
id_id = cur.fetchone()[0]
out.write(f"[3] _id_id columns: {id_id}\n")

out.write("\n--- All checks passed! ---\n" if (total_null == 0 and orphans == 0 and id_id == 0) else "\n--- Issues found ---\n")

cur.close()
conn.close()
out.close()
