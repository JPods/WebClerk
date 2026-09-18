-- Remote Database Data Cleanup Audit
-- Run: DB_MODE=remote python manage.py dbshell < tools/remote_audit.sql

\echo '=== 1. DUPLICATE UUIDs ==='
SELECT 'actions' as tbl, uuid, count(*) as cnt FROM actions GROUP BY uuid HAVING count(*) > 1
UNION ALL SELECT 'contacts', uuid, count(*) FROM contacts GROUP BY uuid HAVING count(*) > 1
UNION ALL SELECT 'orgs_orgbase', uuid, count(*) FROM orgs_orgbase GROUP BY uuid HAVING count(*) > 1
UNION ALL SELECT 'products_item', uuid, count(*) FROM products_item GROUP BY uuid HAVING count(*) > 1
UNION ALL SELECT 'products_warehouse', uuid, count(*) FROM products_warehouse GROUP BY uuid HAVING count(*) > 1
UNION ALL SELECT 'emails', uuid, count(*) FROM emails GROUP BY uuid HAVING count(*) > 1
UNION ALL SELECT 'phones', uuid, count(*) FROM phones GROUP BY uuid HAVING count(*) > 1
UNION ALL SELECT 'settings', uuid, count(*) FROM settings GROUP BY uuid HAVING count(*) > 1
UNION ALL SELECT 'projects', uuid, count(*) FROM projects GROUP BY uuid HAVING count(*) > 1
UNION ALL SELECT 'proposals', uuid, count(*) FROM proposals GROUP BY uuid HAVING count(*) > 1
UNION ALL SELECT 'invoices', uuid, count(*) FROM invoices GROUP BY uuid HAVING count(*) > 1
UNION ALL SELECT 'orders', uuid, count(*) FROM orders GROUP BY uuid HAVING count(*) > 1
UNION ALL SELECT 'pending', uuid, count(*) FROM pending GROUP BY uuid HAVING count(*) > 1
UNION ALL SELECT 'requisitions', uuid, count(*) FROM requisitions GROUP BY uuid HAVING count(*) > 1
UNION ALL SELECT 'connections', uuid, count(*) FROM connections GROUP BY uuid HAVING count(*) > 1
UNION ALL SELECT 'domains', uuid, count(*) FROM domains GROUP BY uuid HAVING count(*) > 1
UNION ALL SELECT 'documents', uuid, count(*) FROM documents GROUP BY uuid HAVING count(*) > 1
UNION ALL SELECT 'templates', uuid, count(*) FROM templates GROUP BY uuid HAVING count(*) > 1
UNION ALL SELECT 'tags', uuid, count(*) FROM tags GROUP BY uuid HAVING count(*) > 1
UNION ALL SELECT 'locations', uuid, count(*) FROM locations GROUP BY uuid HAVING count(*) > 1
UNION ALL SELECT 'work_orders', uuid, count(*) FROM work_orders GROUP BY uuid HAVING count(*) > 1
UNION ALL SELECT 'qas', uuid, count(*) FROM qas GROUP BY uuid HAVING count(*) > 1
UNION ALL SELECT 'products_catalog', uuid, count(*) FROM products_catalog GROUP BY uuid HAVING count(*) > 1
UNION ALL SELECT 'refs_mismatch_log', uuid, count(*) FROM refs_mismatch_log GROUP BY uuid HAVING count(*) > 1
UNION ALL SELECT 'acct_currencies', uuid, count(*) FROM acct_currencies GROUP BY uuid HAVING count(*) > 1
UNION ALL SELECT 'acct_exchanges', uuid, count(*) FROM acct_exchanges GROUP BY uuid HAVING count(*) > 1
UNION ALL SELECT 'acct_exchange_rates', uuid, count(*) FROM acct_exchange_rates GROUP BY uuid HAVING count(*) > 1;

\echo '=== 2. NULL UUIDs ==='
SELECT 'actions' as tbl, count(*) as null_uuids FROM actions WHERE uuid IS NULL HAVING count(*) > 0
UNION ALL SELECT 'contacts', count(*) FROM contacts WHERE uuid IS NULL HAVING count(*) > 0
UNION ALL SELECT 'orgs_orgbase', count(*) FROM orgs_orgbase WHERE uuid IS NULL HAVING count(*) > 0
UNION ALL SELECT 'products_item', count(*) FROM products_item WHERE uuid IS NULL HAVING count(*) > 0
UNION ALL SELECT 'products_warehouse', count(*) FROM products_warehouse WHERE uuid IS NULL HAVING count(*) > 0
UNION ALL SELECT 'emails', count(*) FROM emails WHERE uuid IS NULL HAVING count(*) > 0
UNION ALL SELECT 'phones', count(*) FROM phones WHERE uuid IS NULL HAVING count(*) > 0
UNION ALL SELECT 'settings', count(*) FROM settings WHERE uuid IS NULL HAVING count(*) > 0
UNION ALL SELECT 'projects', count(*) FROM projects WHERE uuid IS NULL HAVING count(*) > 0
UNION ALL SELECT 'proposals', count(*) FROM proposals WHERE uuid IS NULL HAVING count(*) > 0
UNION ALL SELECT 'invoices', count(*) FROM invoices WHERE uuid IS NULL HAVING count(*) > 0
UNION ALL SELECT 'orders', count(*) FROM orders WHERE uuid IS NULL HAVING count(*) > 0
UNION ALL SELECT 'pending', count(*) FROM pending WHERE uuid IS NULL HAVING count(*) > 0
UNION ALL SELECT 'requisitions', count(*) FROM requisitions WHERE uuid IS NULL HAVING count(*) > 0
UNION ALL SELECT 'connections', count(*) FROM connections WHERE uuid IS NULL HAVING count(*) > 0
UNION ALL SELECT 'domains', count(*) FROM domains WHERE uuid IS NULL HAVING count(*) > 0
UNION ALL SELECT 'documents', count(*) FROM documents WHERE uuid IS NULL HAVING count(*) > 0
UNION ALL SELECT 'templates', count(*) FROM templates WHERE uuid IS NULL HAVING count(*) > 0
UNION ALL SELECT 'tags', count(*) FROM tags WHERE uuid IS NULL HAVING count(*) > 0
UNION ALL SELECT 'locations', count(*) FROM locations WHERE uuid IS NULL HAVING count(*) > 0
UNION ALL SELECT 'work_orders', count(*) FROM work_orders WHERE uuid IS NULL HAVING count(*) > 0
UNION ALL SELECT 'qas', count(*) FROM qas WHERE uuid IS NULL HAVING count(*) > 0
UNION ALL SELECT 'products_catalog', count(*) FROM products_catalog WHERE uuid IS NULL HAVING count(*) > 0
UNION ALL SELECT 'refs_mismatch_log', count(*) FROM refs_mismatch_log WHERE uuid IS NULL HAVING count(*) > 0;

\echo '=== 3. ORPHANED FK REFERENCES (populated tables) ==='

-- contacts → orgs_orgbase (org_id)
SELECT 'contacts.org_id → orgs_orgbase' as fk_check, count(*) as orphans
FROM contacts c
WHERE c.org_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM orgs_orgbase o WHERE o.id = c.org_id);

-- emails → contacts (contact_id)
SELECT 'emails.contact_id → contacts' as fk_check, count(*) as orphans
FROM emails e
WHERE e.contact_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM contacts c WHERE c.id = e.contact_id);

-- phones → contacts (contact_id)
SELECT 'phones.contact_id → contacts' as fk_check, count(*) as orphans
FROM phones p
WHERE p.contact_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM contacts c WHERE c.id = p.contact_id);

-- emails → orgs_orgbase (org_id)
SELECT 'emails.org_id → orgs_orgbase' as fk_check, count(*) as orphans
FROM emails e
WHERE e.org_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM orgs_orgbase o WHERE o.id = e.org_id);

-- phones → orgs_orgbase (org_id)
SELECT 'phones.org_id → orgs_orgbase' as fk_check, count(*) as orphans
FROM phones p
WHERE p.org_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM orgs_orgbase o WHERE o.id = p.org_id);

-- actions → projects (project_id)
SELECT 'actions.project_id → projects' as fk_check, count(*) as orphans
FROM actions a
WHERE a.project_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM projects p WHERE p.id = a.project_id);

-- orders → orgs_orgbase (org_id)
SELECT 'orders.org_id → orgs_orgbase' as fk_check, count(*) as orphans
FROM orders o
WHERE o.org_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM orgs_orgbase ob WHERE ob.id = o.org_id);

-- order_lines → orders (order_id)
SELECT 'order_lines.order_id → orders' as fk_check, count(*) as orphans
FROM order_lines ol
WHERE ol.order_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM orders o WHERE o.id = ol.order_id);

-- order_lines → products_item (item_id)
SELECT 'order_lines.item_id → products_item' as fk_check, count(*) as orphans
FROM order_lines ol
WHERE ol.item_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM products_item i WHERE i.id = ol.item_id);

-- invoices → orgs_orgbase (org_id)
SELECT 'invoices.org_id → orgs_orgbase' as fk_check, count(*) as orphans
FROM invoices i
WHERE i.org_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM orgs_orgbase o WHERE o.id = i.org_id);

-- proposals → orgs_orgbase (org_id)
SELECT 'proposals.org_id → orgs_orgbase' as fk_check, count(*) as orphans
FROM proposals p
WHERE p.org_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM orgs_orgbase o WHERE o.id = p.org_id);

-- work_orders → orgs_orgbase (org_id)
SELECT 'work_orders.org_id → orgs_orgbase' as fk_check, count(*) as orphans
FROM work_orders w
WHERE w.org_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM orgs_orgbase o WHERE o.id = w.org_id);

-- requisitions → orgs_orgbase (org_id)
SELECT 'requisitions.org_id → orgs_orgbase' as fk_check, count(*) as orphans
FROM requisitions r
WHERE r.org_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM orgs_orgbase o WHERE o.id = r.org_id);

-- pending → orgs_orgbase (org_id)
SELECT 'pending.org_id → orgs_orgbase' as fk_check, count(*) as orphans
FROM pending p
WHERE p.org_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM orgs_orgbase o WHERE o.id = p.org_id);

-- domains → orgs_orgbase (org_id)
SELECT 'domains.org_id → orgs_orgbase' as fk_check, count(*) as orphans
FROM domains d
WHERE d.org_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM orgs_orgbase o WHERE o.id = d.org_id);

-- connections → contacts (contact_id)
SELECT 'connections.contact_id → contacts' as fk_check, count(*) as orphans
FROM connections cn
WHERE cn.contact_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM contacts c WHERE c.id = cn.contact_id);

-- connections → orgs_orgbase (org_id)
SELECT 'connections.org_id → orgs_orgbase' as fk_check, count(*) as orphans
FROM connections cn
WHERE cn.org_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM orgs_orgbase o WHERE o.id = cn.org_id);

\echo '=== 4. PK SEQUENCE GAPS ==='
SELECT 'actions' as tbl, max(id) as max_id, count(*) as row_count, max(id) - count(*) as gap FROM actions
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

\echo '=== 5. EMPTY REQUIRED FIELDS (name/title on key tables) ==='
SELECT 'orgs_orgbase: empty name' as issue, count(*) as cnt FROM orgs_orgbase WHERE name IS NULL OR name = '';
SELECT 'contacts: empty name' as issue, count(*) as cnt FROM contacts WHERE (first_name IS NULL OR first_name = '') AND (last_name IS NULL OR last_name = '');
SELECT 'products_item: empty name' as issue, count(*) as cnt FROM products_item WHERE name IS NULL OR name = '';
SELECT 'projects: empty name' as issue, count(*) as cnt FROM projects WHERE name IS NULL OR name = '';
SELECT 'settings: empty key' as issue, count(*) as cnt FROM settings WHERE key IS NULL OR key = '';

\echo '=== AUDIT COMPLETE ==='
