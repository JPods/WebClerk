# pip Install Guide

A focused guide to install Python dependencies for this repo.

<!-- TOC START -->

## Table of Contents

- [pip Install Guide](#pip-install-guide)
  - [Table of Contents](#table-of-contents)
  - [Quick Start](#quick-start)
- [from repo root](#from-repo-root)
  - [Virtual Environment (recommended)](#virtual-environment-recommended)
  - [Install From requirements.txt](#install-from-requirementstxt)
  - [Pre-commit Hooks (recommended)](#pre-commit-hooks-recommended)
- [regenerate docs artifacts](#regenerate-docs-artifacts)
  - [Common Issues](#common-issues)
  - [Offline / Air-gapped Install](#offline-air-gapped-install)
  - [Behind a Proxy](#behind-a-proxy)

<!-- TOC END -->

## Quick Start

```bash
# from repo root
python3 -m venv .
source bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Virtual Environment (recommended)

- Create once per machine or per clone:
  - python3 -m venv .
  - source bin/activate
- Deactivate with: deactivate

## Install From requirements.txt

- Pinned, known-good versions are in requirements.txt.
- Install: pip install -r requirements.txt
- If you switch Python versions (3.11–3.13 supported), refresh the venv and reinstall.

## Pre-commit Hooks (recommended)

```bash
pip install pre-commit
pre-commit install
```

Hooks enforce docs layout and consistency, and our migration policy. If a hook fails, follow its message or run:

```bash
# regenerate docs artifacts
python Scripts/gen_readmes_toc.py
python Scripts/gen_docs_index.py
```

## Common Issues

- psycopg2-binary: Already used in requirements; if build issues occur, install Xcode CLT:
  - xcode-select --install
- SSL/Cert errors on macOS: ensure Python uses system certificates, or upgrade pip.
- Permission errors: always install inside a venv, not system Python.

## Offline / Air-gapped Install

On a connected machine:

```bash
mkdir wheels
pip download -r requirements.txt -d wheels
```

Transfer wheels/ to the target and run:

```bash
pip install --no-index --find-links wheels -r requirements.txt
```

## Behind a Proxy

Set environment variables before installing:

```bash
export http_proxy=http://user:pass@proxy.example.com:8080
export https_proxy=$http_proxy
pip install -r requirements.txt
```
