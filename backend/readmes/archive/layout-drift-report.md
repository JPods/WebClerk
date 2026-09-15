# Layout ↔ Schema Drift Report

> Generated: 2026-08-26 05:44  
> Models scanned: 0  
> Total issues (excl. info): 0

**Trend:** 📈 improving (200 total corrections over 28 scans)

## Summary

| Severity | Count |
|----------|-------|
| 🔴 High (phantom fields) | 0 |
| 🟡 Medium (required unrendered) | 0 |
| 🔵 Low (optional unrendered) | 0 |
| ℹ️  Info (detail-only) | 0 |

---

## Page File Inventory

| Model | Detail | List | Display |
|-------|--------|------|---------|

---

## Workflow

1. **Review** this report — focus on 🔴 High issues first
2. **Fix** real mismatches in the React/Django code
3. **Dismiss** intentional mismatches: `manage.py ai_intelligence --task layout --dismiss model:field:type --reason 'explanation'`
4. **Re-scan**: `manage.py ai_intelligence --task layout --report`
5. **Review corrections**: resolved issues are tracked automatically — the LLM learns from your fixes
