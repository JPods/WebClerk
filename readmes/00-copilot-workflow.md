# Copilot Agent Workflow Agreement

> **Established:** January 12, 2026

This document defines the working agreement between the developer and GitHub Copilot agent for this project.

---

## Execution Mode: Full Autonomy

### Copilot Can Execute Without Approval

| Action | Examples |
|--------|----------|
| **File operations** | Create, modify, delete files |
| **Terminal commands** | npm, pnpm, python, pip, git |
| **Database operations** | Django migrations, management commands, direct queries |
| **Package management** | Install/update dependencies |
| **Git operations** | Branch, commit, push to feature branches |

### Copilot Will Confirm Before

| Action | Reason |
|--------|--------|
| Push to `main` or `dev` | Protected branches |
| Production database changes | Safety (though no legacy data currently) |
| Major architectural changes | Outside agreed plan scope |

---

## Workflow

```
1. Developer describes the task
2. Copilot outlines the plan briefly
3. Developer confirms (or implies agreement)
4. Copilot executes all steps without stopping
5. Review results together; fix any issues
```

---

## Documentation Practice

**All significant work should be documented in READMEs:**

- New features → Document in relevant `readmes/topics/` file
- API changes → Update `readmes/topics/api/` docs
- Infrastructure changes → Update `readmes/topics/infrastructure/` docs
- Integration work → Create/update integration docs (e.g., `kanban-integration.md`)

This ensures:
- Context persists across sessions (Copilot doesn't retain memory)
- Other developers can understand the system
- Decisions and implementations are traceable

---

## VS Code Settings for Agent Mode

Add to `settings.json`:

```json
{
  "chat.agent.enabled": true,
  "github.copilot.chat.agent.runTasks.setupShell": "always",
  "chat.tools.autoApprove": true
}
```

---

## Project Structure

| Folder | Purpose |
|--------|---------|
| `React2025/` | React frontend (r25) |
| `webClerk3/` | Django backend (wc3) |
| `vue2020/` | Legacy Vue frontend (reference only) |

---

## Recent Work Log

### January 12, 2026

- **Kanban Board Integration** ([kanban-integration.md](topics/kanban-integration.md))
  - Project-scoped contacts via `project.refs.links.contact`
  - Contact Manager modal for managing project contacts
  - Assignee dropdown in task modals uses project contacts
  - "All projects" mode fetches all active contacts
  - Created `populate_project_contacts` Django management command
