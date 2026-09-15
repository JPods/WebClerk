# Developer Setup & Requirements

> **Reading order**: [← 01-architecture-overview](01-architecture-overview.md) | [03-wcapi-gateway →](03-wcapi-gateway.md)

---

<!-- TOC START -->

## Table of Contents

- [Developer Setup & Requirements](#developer-setup--requirements)
  - [Table of Contents](#table-of-contents)
  - [Quick Start (TL;DR)](#quick-start-tldr)
  - [Python & Virtual Environment](#python--virtual-environment)
  - [Install Dependencies](#install-dependencies)
  - [Pre-commit Hooks](#pre-commit-hooks)
  - [Running Tests](#running-tests)
  - [Common Environment Vars](#common-environment-vars)
  - [Troubleshooting](#troubleshooting)

<!-- TOC END -->

This quick guide helps the team get a working environment on macOS with zsh. It covers Python, dependencies, pre-commit, and running tests.

## Quick Start (TL;DR)

```bash
# From repo root
python3 -m venv .
source bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Install pre-commit hooks (recommended)
pip install pre-commit
pre-commit install

# Fast tests
pytest -q -m fast
```

## Python & Virtual Environment

- Target versions: 3.11–3.13 (CI runs a matrix). Locally, 3.13 is fine.
- Create a virtualenv in the repo root:
  - python3 -m venv .
  - source bin/activate (zsh)
- Upgrade pip: pip install --upgrade pip

Note: The repo contains a bin/ directory; if using a fresh venv, it will be populated there.

## Install Dependencies

- Project deps: pip install -r requirements.txt
- Optional dev tools: pip install pre-commit

If psycopg2-binary fails to build, ensure Xcode Command Line Tools are installed: xcode-select --install

## Pre-commit Hooks

- Install and enable:
  - pip install pre-commit
  - pre-commit install
- Hooks enforced:
  - Documentation layout guard (docs belong in readmes/; root README.md allowed)
  - Docs index & TOC consistency (docs_index.json and readmes TOCs must be up to date)
  - Single initial migration policy (enforced on protected branches; bypass via ALLOW_MULTIPLE_MIGRATIONS=1)
  - Misc safety (e.g., prevent committing destructive flags in examples)

Temporarily bypass docs layout (transition only): export DOC_GUARD_ALLOW_LEGACY=1

## Running Tests

- Fast subset (used by pytest -q in CI smoke): pytest -q -m fast
- Full suite: pytest -q
- Integration (Postgres): pytest -q -m "integration and not slow"

## Common Environment Vars

- DJANGO_SETTINGS_MODULE=webclerk3_api.settings
- PYTEST_FORCE_DB=0 (SQLite fast path); set 1 for Postgres
- USE_SQLITE_TEST=1 (default in CI smoke)

## Troubleshooting

- Docs consistency fails: run
  - python Scripts/gen_readmes_toc.py
  - python Scripts/gen_docs_index.py
  - git add docs_index.json readmes/*.md
  - New docs to include in index: readmes/email-verification.md, readmes/exchange-review.md
- Migrations policy blocks: set ALLOW_MULTIPLE_MIGRATIONS=1 for local/wip branches, but fix before merging to protected branches.
- psycopg2 issues: ensure Postgres headers/client tools are present or use psycopg2-binary (already in requirements).

If anything in this doc goes stale, update it and run the docs generators above; CI will enforce consistency.
