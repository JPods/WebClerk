#!/bin/bash
# build_demo_db.sh — Create a demo database from the current dataset.
#
# Usage:
#     bash scripts/build_demo_db.sh
#
# What it does:
#   1. Copies commerce_expert → commerce_demo
#   2. Removes all contacts except qq-prefixed (and their dependent records)
#   3. Clears logs, sessions, and operational noise
#   4. Creates a demo admin user (demo@webclerk.com / demo1234)
#   5. Dumps to media/downloads/webclerk-demo.sql.gz
#
# The resulting file can be downloaded from webclerk.com/downloads/webclerk-demo.sql.gz

set -e

SOURCE_DB="commerce_expert"
DEMO_DB="commerce_demo"
DUMP_DIR="media/downloads"
DUMP_FILE="$DUMP_DIR/webclerk-demo.sql.gz"
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

cd "$SCRIPT_DIR"

echo "=== Building WebClerk Demo Database ==="
echo ""

# Step 1: Copy the current database (via dump/restore to avoid connection locks)
echo "1. Copying $SOURCE_DB → $DEMO_DB"
dropdb --if-exists "$DEMO_DB"
createdb "$DEMO_DB"
pg_dump "$SOURCE_DB" | psql -q "$DEMO_DB" > /dev/null 2>&1
echo "   Done."

# Step 2: Clean — keep qq contacts + all system/config data, remove everything else
echo "2. Cleaning data..."
psql "$DEMO_DB" <<'SQL'
BEGIN;

-- Collect all contact IDs referenced by qq data (not just qq-prefixed contacts)
CREATE TEMP TABLE qq_contact_ids AS
  SELECT id FROM contacts WHERE ida LIKE 'qq%'
  UNION SELECT contact_id FROM orgs_orgbase WHERE ida LIKE 'qq%' AND contact_id IS NOT NULL
  UNION SELECT contact_id FROM orders WHERE ida LIKE 'qq%' AND contact_id IS NOT NULL
  UNION SELECT contact_id FROM invoices WHERE ida LIKE 'qq%' AND contact_id IS NOT NULL;

-- Save qq data to temp tables
CREATE TEMP TABLE qq_contacts AS SELECT * FROM contacts WHERE id IN (SELECT id FROM qq_contact_ids);
CREATE TEMP TABLE qq_orgs AS SELECT * FROM orgs_orgbase WHERE ida LIKE 'qq%';
CREATE TEMP TABLE qq_items AS SELECT * FROM products_item WHERE ida LIKE 'qq%';
CREATE TEMP TABLE qq_orders AS SELECT * FROM orders WHERE ida LIKE 'qq%';
CREATE TEMP TABLE qq_order_lines AS SELECT ol.* FROM order_lines ol JOIN orders o ON ol.order_id = o.id WHERE o.ida LIKE 'qq%';
CREATE TEMP TABLE qq_invoices AS SELECT * FROM invoices WHERE ida LIKE 'qq%';
CREATE TEMP TABLE qq_invoice_lines AS SELECT il.* FROM invoice_lines il JOIN invoices i ON il.invoice_id = i.id WHERE i.ida LIKE 'qq%';

-- Truncate all user-data tables (CASCADE handles FKs)
TRUNCATE contacts CASCADE;
TRUNCATE orgs_orgbase CASCADE;
TRUNCATE products_item CASCADE;
TRUNCATE orders CASCADE;
TRUNCATE invoices CASCADE;
TRUNCATE pending CASCADE;
TRUNCATE ledger CASCADE;
TRUNCATE actions CASCADE;

-- Restore qq data
INSERT INTO contacts SELECT * FROM qq_contacts;
INSERT INTO orgs_orgbase SELECT * FROM qq_orgs;
INSERT INTO products_item SELECT * FROM qq_items;
INSERT INTO orders SELECT * FROM qq_orders;
INSERT INTO order_lines SELECT * FROM qq_order_lines;
INSERT INTO invoices SELECT * FROM qq_invoices;
INSERT INTO invoice_lines SELECT * FROM qq_invoice_lines;

-- Clear operational noise (no CASCADE needed, these are leaf tables)
TRUNCATE django_session;
TRUNCATE api_logs CASCADE;
TRUNCATE audit_logs CASCADE;
TRUNCATE coding_session CASCADE;
TRUNCATE notifications CASCADE;
TRUNCATE error_pattern CASCADE;

COMMIT;

-- Summary
SELECT 'contacts: ' || COUNT(*) FROM contacts
UNION ALL SELECT 'orgs: ' || COUNT(*) FROM orgs_orgbase
UNION ALL SELECT 'items: ' || COUNT(*) FROM products_item
UNION ALL SELECT 'orders: ' || COUNT(*) FROM orders
UNION ALL SELECT 'invoices: ' || COUNT(*) FROM invoices;
SQL
echo "   Done."

# Step 3: Create demo admin user
echo "3. Creating demo admin user..."
source "$SCRIPT_DIR/venv/bin/activate"
LOCAL_DATABASE_NAME="$DEMO_DB" DB_MODE="local" python3 manage.py shell -c "
from apps.core.models.contact import Contact
if not Contact.objects.filter(email='demo@webclerk.com').exists():
    u = Contact.objects.create_superuser(
        email='demo@webclerk.com',
        password='demo1234',
        ida='qqdemo-admin',
        name_first='Demo',
        name_last='Admin',
    )
    print(f'  Created demo admin: {u.email}')
else:
    print('  Demo admin already exists')
"
echo "   Done."

# Step 4: Dump the database
echo "4. Dumping database to $DUMP_FILE..."
mkdir -p "$DUMP_DIR"
pg_dump "$DEMO_DB" | gzip > "$DUMP_FILE"
SIZE=$(ls -lh "$DUMP_FILE" | awk '{print $5}')
echo "   Done. Size: $SIZE"

echo ""
echo "=== Demo database ready ==="
echo "  File: $DUMP_FILE"
echo "  Login: demo@webclerk.com / demo1234"
echo ""
echo "To load on another machine:"
echo "  createdb webclerk_demo"
echo "  gunzip -c webclerk-demo.sql.gz | psql webclerk_demo"
echo "  LOCAL_DATABASE_NAME=webclerk_demo python manage.py runserver"
