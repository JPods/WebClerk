-- Sample orphaned actions
SELECT id, contact_id, status, action
FROM actions
WHERE contact_id IN (0, 3, 15, 17)
ORDER BY contact_id, id;
