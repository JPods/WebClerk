"""Create PostgreSQL VIEW 'agenda' merging touches + actions."""
from django.db import migrations


CREATE_VIEW = """
CREATE OR REPLACE VIEW agenda AS

-- Touches with follow-up due
SELECT
    t.id * 2 AS id,
    'touch' AS source_model,
    t.id AS source_id,
    CASE t.channel
        WHEN 'call' THEN '📞'
        WHEN 'email' THEN '✉'
        WHEN 'visit' THEN '📋'
        WHEN 'text' THEN '💬'
        WHEN 'meeting' THEN '🤝'
        ELSE '📞'
    END AS icon,
    COALESCE(t.subject, '') AS title,
    COALESCE(t.outcome, '') AS status,
    COALESCE(t.purpose, '') AS purpose,
    t.dt_next AS dt_due,
    t.dt_created,
    t.impact,
    COALESCE(t.direction, '') AS direction,
    t.contact_id,
    t.org_id,
    COALESCE(t.org_model, '') AS org_model,
    t.logged_by,
    COALESCE(t.summary, '') AS detail_text,
    t.is_active
FROM touches t
WHERE t.dt_next > 0 AND t.is_active = true

UNION ALL

-- Actions with deadlines
SELECT
    a.id * 2 + 1 AS id,
    'action' AS source_model,
    a.id AS source_id,
    '🏃' AS icon,
    COALESCE(a.action->>'en', a.action::text, '') AS title,
    COALESCE(a.status, '') AS status,
    COALESCE(a.purpose, '') AS purpose,
    a.dt_deadline AS dt_due,
    a.dt_created,
    COALESCE(a.priority, 0) AS impact,
    '' AS direction,
    a.contact_id,
    0 AS org_id,
    '' AS org_model,
    0 AS logged_by,
    COALESCE(a.description->>'en', a.description::text, '') AS detail_text,
    a.is_active
FROM actions a
WHERE a.dt_deadline > 0
  AND a.status IN ('open', 'in_progress')
  AND a.is_active = true

ORDER BY dt_due ASC;
"""

DROP_VIEW = "DROP VIEW IF EXISTS agenda;"


class Migration(migrations.Migration):

    dependencies = [
        ('communications', '0015_add_touch_dt_next'),
    ]

    operations = [
        migrations.RunSQL(CREATE_VIEW, DROP_VIEW),
    ]
