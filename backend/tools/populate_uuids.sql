-- Populate NULL UUIDs on all affected remote tables
-- Run: DB_MODE=remote python manage.py dbshell < tools/populate_uuids.sql
-- Uses PostgreSQL gen_random_uuid() to generate UUID v4 values

BEGIN;

\echo 'Populating UUIDs...'

UPDATE actions SET uuid = gen_random_uuid() WHERE uuid IS NULL;
\echo '  actions done'

UPDATE products_item SET uuid = gen_random_uuid() WHERE uuid IS NULL;
\echo '  products_item done'

UPDATE orgs_orgbase SET uuid = gen_random_uuid() WHERE uuid IS NULL;
\echo '  orgs_orgbase done'

UPDATE refs_mismatch_log SET uuid = gen_random_uuid() WHERE uuid IS NULL;
\echo '  refs_mismatch_log done'

UPDATE emails SET uuid = gen_random_uuid() WHERE uuid IS NULL;
\echo '  emails done'

UPDATE settings SET uuid = gen_random_uuid() WHERE uuid IS NULL;
\echo '  settings done'

UPDATE products_warehouse SET uuid = gen_random_uuid() WHERE uuid IS NULL;
\echo '  products_warehouse done'

UPDATE pending SET uuid = gen_random_uuid() WHERE uuid IS NULL;
\echo '  pending done'

UPDATE requisitions SET uuid = gen_random_uuid() WHERE uuid IS NULL;
\echo '  requisitions done'

UPDATE connections SET uuid = gen_random_uuid() WHERE uuid IS NULL;
\echo '  connections done'

UPDATE domains SET uuid = gen_random_uuid() WHERE uuid IS NULL;
\echo '  domains done'

UPDATE projects SET uuid = gen_random_uuid() WHERE uuid IS NULL;
\echo '  projects done'

UPDATE contacts SET uuid = gen_random_uuid() WHERE uuid IS NULL;
\echo '  contacts done'

UPDATE phones SET uuid = gen_random_uuid() WHERE uuid IS NULL;
\echo '  phones done'

UPDATE documents SET uuid = gen_random_uuid() WHERE uuid IS NULL;
\echo '  documents done'

UPDATE acct_currencies SET uuid = gen_random_uuid() WHERE uuid IS NULL;
\echo '  acct_currencies done'

UPDATE products_catalog SET uuid = gen_random_uuid() WHERE uuid IS NULL;
\echo '  products_catalog done'

UPDATE acct_exchanges SET uuid = gen_random_uuid() WHERE uuid IS NULL;
\echo '  acct_exchanges done'

UPDATE acct_exchange_rates SET uuid = gen_random_uuid() WHERE uuid IS NULL;
\echo '  acct_exchange_rates done'

UPDATE templates SET uuid = gen_random_uuid() WHERE uuid IS NULL;
\echo '  templates done'

UPDATE tags SET uuid = gen_random_uuid() WHERE uuid IS NULL;
\echo '  tags done'

UPDATE locations SET uuid = gen_random_uuid() WHERE uuid IS NULL;
\echo '  locations done'

UPDATE proposals SET uuid = gen_random_uuid() WHERE uuid IS NULL;
\echo '  proposals done'

UPDATE qas SET uuid = gen_random_uuid() WHERE uuid IS NULL;
\echo '  qas done'

UPDATE orders SET uuid = gen_random_uuid() WHERE uuid IS NULL;
\echo '  orders done'

COMMIT;

\echo ''
\echo '=== VERIFICATION: remaining NULL UUIDs ==='
SELECT 'actions' as tbl, count(*) as remaining FROM actions WHERE uuid IS NULL
UNION ALL SELECT 'contacts', count(*) FROM contacts WHERE uuid IS NULL
UNION ALL SELECT 'orgs_orgbase', count(*) FROM orgs_orgbase WHERE uuid IS NULL
UNION ALL SELECT 'products_item', count(*) FROM products_item WHERE uuid IS NULL
UNION ALL SELECT 'products_warehouse', count(*) FROM products_warehouse WHERE uuid IS NULL
UNION ALL SELECT 'emails', count(*) FROM emails WHERE uuid IS NULL
UNION ALL SELECT 'phones', count(*) FROM phones WHERE uuid IS NULL
UNION ALL SELECT 'settings', count(*) FROM settings WHERE uuid IS NULL
UNION ALL SELECT 'projects', count(*) FROM projects WHERE uuid IS NULL
UNION ALL SELECT 'proposals', count(*) FROM proposals WHERE uuid IS NULL
UNION ALL SELECT 'orders', count(*) FROM orders WHERE uuid IS NULL
UNION ALL SELECT 'pending', count(*) FROM pending WHERE uuid IS NULL
UNION ALL SELECT 'requisitions', count(*) FROM requisitions WHERE uuid IS NULL
UNION ALL SELECT 'connections', count(*) FROM connections WHERE uuid IS NULL
UNION ALL SELECT 'domains', count(*) FROM domains WHERE uuid IS NULL
UNION ALL SELECT 'documents', count(*) FROM documents WHERE uuid IS NULL
UNION ALL SELECT 'templates', count(*) FROM templates WHERE uuid IS NULL
UNION ALL SELECT 'tags', count(*) FROM tags WHERE uuid IS NULL
UNION ALL SELECT 'locations', count(*) FROM locations WHERE uuid IS NULL
UNION ALL SELECT 'qas', count(*) FROM qas WHERE uuid IS NULL
UNION ALL SELECT 'products_catalog', count(*) FROM products_catalog WHERE uuid IS NULL
UNION ALL SELECT 'refs_mismatch_log', count(*) FROM refs_mismatch_log WHERE uuid IS NULL
UNION ALL SELECT 'acct_currencies', count(*) FROM acct_currencies WHERE uuid IS NULL
UNION ALL SELECT 'acct_exchanges', count(*) FROM acct_exchanges WHERE uuid IS NULL
UNION ALL SELECT 'acct_exchange_rates', count(*) FROM acct_exchange_rates WHERE uuid IS NULL
ORDER BY remaining DESC;

\echo '=== UUID POPULATION COMPLETE ==='
