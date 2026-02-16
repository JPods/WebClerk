-- FK Orphan Check + UUID Population Script
-- Run: DB_MODE=remote python manage.py dbshell < tools/remote_fk_check.sql

\echo '=== ORPHANED FK REFERENCES ==='

SELECT 'contacts.customer_id -> orgs' as fk_check, count(*) as orphans
FROM contacts c
WHERE c.customer_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM orgs_orgbase o WHERE o.id = c.customer_id);

SELECT 'contacts.vendor_id -> orgs' as fk_check, count(*) as orphans
FROM contacts c
WHERE c.vendor_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM orgs_orgbase o WHERE o.id = c.vendor_id);

SELECT 'contacts.manufacturer_id -> orgs' as fk_check, count(*) as orphans
FROM contacts c
WHERE c.manufacturer_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM orgs_orgbase o WHERE o.id = c.manufacturer_id);

SELECT 'emails.contact_id -> contacts' as fk_check, count(*) as orphans
FROM emails e
WHERE e.contact_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM contacts c WHERE c.id = e.contact_id);

SELECT 'phones.contact_id -> contacts' as fk_check, count(*) as orphans
FROM phones p
WHERE p.contact_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM contacts c WHERE c.id = p.contact_id);

SELECT 'domains.contact_id -> contacts' as fk_check, count(*) as orphans
FROM domains d
WHERE d.contact_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM contacts c WHERE c.id = d.contact_id);

SELECT 'actions.contact_id -> contacts' as fk_check, count(*) as orphans
FROM actions a
WHERE a.contact_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM contacts c WHERE c.id = a.contact_id);

SELECT 'actions.project_id -> projects' as fk_check, count(*) as orphans
FROM actions a
WHERE a.project_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM projects p WHERE p.id = a.project_id);

SELECT 'orders.customer_id -> orgs' as fk_check, count(*) as orphans
FROM orders o
WHERE o.customer_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM orgs_orgbase ob WHERE ob.id = o.customer_id);

SELECT 'orders.contact_id -> contacts' as fk_check, count(*) as orphans
FROM orders o
WHERE o.contact_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM contacts c WHERE c.id = o.contact_id);

SELECT 'order_lines.order_id -> orders' as fk_check, count(*) as orphans
FROM order_lines ol
WHERE ol.order_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM orders o WHERE o.id = ol.order_id);

SELECT 'order_lines.item_id_fk -> items' as fk_check, count(*) as orphans
FROM order_lines ol
WHERE ol.item_id_fk IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM products_item i WHERE i.id = ol.item_id_fk);

SELECT 'invoices.customer_id -> orgs' as fk_check, count(*) as orphans
FROM invoices i
WHERE i.customer_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM orgs_orgbase o WHERE o.id = i.customer_id);

SELECT 'invoices.contact_id -> contacts' as fk_check, count(*) as orphans
FROM invoices i
WHERE i.contact_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM contacts c WHERE c.id = i.contact_id);

SELECT 'proposals.customer_id -> orgs' as fk_check, count(*) as orphans
FROM proposals p
WHERE p.customer_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM orgs_orgbase o WHERE o.id = p.customer_id);

SELECT 'work_orders.customer_id -> orgs' as fk_check, count(*) as orphans
FROM work_orders w
WHERE w.customer_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM orgs_orgbase o WHERE o.id = w.customer_id);

\echo '=== PK SEQUENCE HEALTH ==='
SELECT 'actions' as tbl, max(id) as max_id, count(*) as rows, max(id) - count(*) as gap FROM actions
UNION ALL SELECT 'contacts', max(id), count(*), max(id) - count(*) FROM contacts
UNION ALL SELECT 'orgs_orgbase', max(id), count(*), max(id) - count(*) FROM orgs_orgbase
UNION ALL SELECT 'products_item', max(id), count(*), max(id) - count(*) FROM products_item
UNION ALL SELECT 'emails', max(id), count(*), max(id) - count(*) FROM emails
UNION ALL SELECT 'phones', max(id), count(*), max(id) - count(*) FROM phones
UNION ALL SELECT 'settings', max(id), count(*), max(id) - count(*) FROM settings
UNION ALL SELECT 'orders', max(id), count(*), max(id) - count(*) FROM orders
UNION ALL SELECT 'invoices', max(id), count(*), max(id) - count(*) FROM invoices
UNION ALL SELECT 'proposals', max(id), count(*), max(id) - count(*) FROM proposals
UNION ALL SELECT 'projects', max(id), count(*), max(id) - count(*) FROM projects
UNION ALL SELECT 'pending', max(id), count(*), max(id) - count(*) FROM pending
UNION ALL SELECT 'requisitions', max(id), count(*), max(id) - count(*) FROM requisitions
UNION ALL SELECT 'work_orders', max(id), count(*), max(id) - count(*) FROM work_orders
ORDER BY gap DESC;

\echo '=== EMPTY REQUIRED FIELDS ==='
SELECT 'orgs_orgbase: empty name' as issue, count(*) as cnt FROM orgs_orgbase WHERE name IS NULL OR name = '';
SELECT 'contacts: empty name' as issue, count(*) as cnt FROM contacts WHERE (first_name IS NULL OR first_name = '') AND (last_name IS NULL OR last_name = '');
SELECT 'products_item: empty name' as issue, count(*) as cnt FROM products_item WHERE name IS NULL OR name = '';
SELECT 'projects: empty name' as issue, count(*) as cnt FROM projects WHERE name IS NULL OR name = '';
SELECT 'settings: empty key' as issue, count(*) as cnt FROM settings WHERE key IS NULL OR key = '';

\echo '=== NULL UUID COUNTS ==='
SELECT 'actions' as tbl, count(*) as null_uuids FROM actions WHERE uuid IS NULL
UNION ALL SELECT 'contacts', count(*) FROM contacts WHERE uuid IS NULL
UNION ALL SELECT 'orgs_orgbase', count(*) FROM orgs_orgbase WHERE uuid IS NULL
UNION ALL SELECT 'products_item', count(*) FROM products_item WHERE uuid IS NULL
UNION ALL SELECT 'products_warehouse', count(*) FROM products_warehouse WHERE uuid IS NULL
UNION ALL SELECT 'emails', count(*) FROM emails WHERE uuid IS NULL
UNION ALL SELECT 'phones', count(*) FROM phones WHERE uuid IS NULL
UNION ALL SELECT 'settings', count(*) FROM settings WHERE uuid IS NULL
UNION ALL SELECT 'projects', count(*) FROM projects WHERE uuid IS NULL
UNION ALL SELECT 'proposals', count(*) FROM proposals WHERE uuid IS NULL
UNION ALL SELECT 'invoices', count(*) FROM invoices WHERE uuid IS NULL
UNION ALL SELECT 'orders', count(*) FROM orders WHERE uuid IS NULL
UNION ALL SELECT 'pending', count(*) FROM pending WHERE uuid IS NULL
UNION ALL SELECT 'requisitions', count(*) FROM requisitions WHERE uuid IS NULL
UNION ALL SELECT 'connections', count(*) FROM connections WHERE uuid IS NULL
UNION ALL SELECT 'domains', count(*) FROM domains WHERE uuid IS NULL
UNION ALL SELECT 'documents', count(*) FROM documents WHERE uuid IS NULL
UNION ALL SELECT 'templates', count(*) FROM templates WHERE uuid IS NULL
UNION ALL SELECT 'tags', count(*) FROM tags WHERE uuid IS NULL
UNION ALL SELECT 'locations', count(*) FROM locations WHERE uuid IS NULL
UNION ALL SELECT 'work_orders', count(*) FROM work_orders WHERE uuid IS NULL
UNION ALL SELECT 'qas', count(*) FROM qas WHERE uuid IS NULL
UNION ALL SELECT 'products_catalog', count(*) FROM products_catalog WHERE uuid IS NULL
UNION ALL SELECT 'refs_mismatch_log', count(*) FROM refs_mismatch_log WHERE uuid IS NULL
UNION ALL SELECT 'acct_currencies', count(*) FROM acct_currencies WHERE uuid IS NULL
UNION ALL SELECT 'acct_exchanges', count(*) FROM acct_exchanges WHERE uuid IS NULL
UNION ALL SELECT 'acct_exchange_rates', count(*) FROM acct_exchange_rates WHERE uuid IS NULL
ORDER BY null_uuids DESC;

\echo '=== AUDIT COMPLETE ==='
