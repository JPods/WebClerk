-- Remap orphaned actions.contact_id to contact 1
-- 123 records pointing to non-existent contacts (0, 3, 15, 17)
BEGIN;

UPDATE actions
SET contact_id = 1
WHERE contact_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM contacts c WHERE c.id = actions.contact_id);

COMMIT;
