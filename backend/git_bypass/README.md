# Git Bypass Folder Guide

Action:
Function:
Frequency:
Process:

Action: Keep local-only configuration and instruction assets outside normal source control flow.
Function: Local developer environment setup, workspace behavior, and AI instruction fallbacks.
Frequency: Review during machine setup, environment changes, and onboarding.
Process:
1. Keep machine-specific or secret-bearing files here when they must not be pushed.
2. Document each local-only item and how to recreate it on a new machine.
3. Keep committed templates in readmes and keep this folder as the local execution layer.

## Why this folder exists

This folder is for items that are useful in day-to-day development but should not be part of standard repository history, either because they are local-machine specific, hidden by ignore rules, or contain sensitive configuration values.

## What is in this folder

- copilot.instructions.md
  - Purpose: Local instruction profile for coding assistant behavior.
  - Why here: Lets local instruction experiments happen without forcing repo-wide policy changes.

- wcapi.instructions.md
  - Purpose: Local WCAPI guidance used during focused backend work.
  - Why here: Allows local tuning or temporary instruction overlays while keeping canonical docs elsewhere.

- save_env
  - Purpose: Local environment variable file for webClerk3 runtime.
  - Why here: Contains sensitive values and machine-specific settings.
  - Source of truth for template: readmes/env-setup.md and .env-example.

- vscode-env-settings-local-only.md
  - Purpose: Record of VS Code settings that are intentionally local and not pushed.
  - Why here: Some workspace settings are hidden by repository or global git ignore rules.

## Relationship to committed docs

- Committed environment setup documentation lives in readmes/env-setup.md.
- Committed template values should live in .env-example without secrets.
- This folder documents and stores the local layer needed to run the system safely on a specific machine.

## Safety rules

- Do not place this folder contents into commits unless explicitly sanitized and approved.
- Never store new production secrets in committed files.
- When adding a new local-only file, update this README with purpose, risk, and rebuild steps.

## Rebuild checklist for a new machine

1. Recreate workspace settings from vscode-env-settings-local-only.md.
2. Recreate environment values from .env-example plus local secret sources.
3. Verify database mode and dataset labels before running server startup.
4. Confirm Python interpreter path and terminal env injection behavior in VS Code.
