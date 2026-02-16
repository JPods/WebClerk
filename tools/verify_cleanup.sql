-- Final verification: remote database data quality
-- Run with: PGPASSWORD=wc_psql_server psql -h 76.13.185.210 -p 5432 -U postgres -d commerce_expert -f tools/verify_cleanup.sql

-- 1. NULL UUIDs remaining
SELECT 'null_uuids' AS check_name,
       (SELECT count(*) FROM (
         SELECT count(*) FROM actions WHERE uuid IS NULL UNION ALL
         SELECT count(*) FROM communications WHERE uuid IS NULL UNION ALL
         SELECT count(*) FROM contacts WHERE uuid IS NULL UNION ALL
         SELECT count(*) FROM emails WHERE uuid IS NULL UNION ALL
         SELECT count(*) FROM invoices WHERE uuid IS NULL UNION ALL
         SELECT count(*) FROM invoice_lines WHERE uuid IS NULL UNION ALL
         SELECT count(*) FROM items WHERE uuid IS NULL UNION ALL
         SELECT count(*) FROM keywords WHERE uuid IS NULL UNION ALL
         SELECT count(*) FROM locations WHERE uuid IS NULL UNION ALL
         SELECT count(*) FROM notes WHERE uuid IS NULL UNION ALL
         SELECT count(*) FROM orders WHERE uuid IS NULL UNION ALL
         SELECT count(*) FROM order_lines WHERE uuid IS NULL UNION ALL
         SELECT count(*) FROM organizations WHERE uuid IS NULL UNION ALL
         SELECT count(*) FROM phones WHERE uuid IS NULL UNION ALL
         SELECT count(*) FROM products_item WHERE uuid IS NULL UNION ALL
         SELECT count(*) FROM products_pricetier WHERE uuid IS NULL UNION ALL
         SELECT count(*) FROM proposals WHERE uuid IS NULL UNION ALL
         SELECT count(*) FROM proposal_lines WHERE uuid IS NULL UNION ALL
         SELECT count(*) FROM settings WHERE uuid IS NULL UNION ALL
         SELECT count(*) FROM templates WHERE uuid IS NULL UNION ALL
         SELECT count(*) FROM urls WHERE uuid IS NULL UNION ALL
         SELECT count(*) FROM warehouses WHERE uuid IS NULL UNION ALL
         SELECT count(*) FROM work_orders WHERE uuid IS NULL UNION ALL
         SELECT count(*) FROM work_order_lines WHERE uuid IS NULL
       ) t) AS remaining_count;

-- 2. Orphaned actions.contact_id
SELECT 'orphaned_actions_contact' AS check_name,
       count(*) AS remaining_count
FROM actions a
WHERE a.contact_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM contacts c WHERE c.id = a.contact_id);

-- 3. Any _id_id columns still present
SELECT 'id_id_columns' AS check_name,
       count(*) AS remaining_count
FROM information_schema.columns
WHERE table_schema = 'public'
  AND column_name LIKE '%_id_id';
