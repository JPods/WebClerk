# Third-Party Notices

> **Mandatory:** When adding or removing any outside dependency, update this file
> AND the corresponding dependency file (requirements.txt / package.json) in the
> same commit. See CLAUDE.md "Dependency Discipline" rule.

WebClerk is built with the following open-source libraries. We are grateful
to their authors and communities. Each library retains its own license.

Last updated: 2026-09-03

---

## Backend (Python)

| Library | Version | License | Purpose |
|---------|---------|---------|---------|
| [Django](https://djangoproject.com) | 5.2.8 | BSD-3-Clause | Web framework |
| [Django REST Framework](https://django-rest-framework.org) | 3.16.0 | BSD | API layer |
| [djangorestframework-simplejwt](https://github.com/jazzband/djangorestframework-simplejwt) | 5.5.0 | MIT | JWT authentication |
| [django-cors-headers](https://github.com/adamchainz/django-cors-headers) | 4.7.0 | MIT | CORS handling |
| [django-filter](https://github.com/carltongibson/django-filter) | 25.1 | BSD | Queryset filtering |
| [django-celery-beat](https://github.com/celery/django-celery-beat) | 2.8.1 | BSD-3-Clause | Periodic task scheduling |
| [django-celery-results](https://github.com/celery/django-celery-results) | 2.6.0 | BSD-3-Clause | Task result storage |
| [Celery](https://docs.celeryq.dev) | 5.5.3 | BSD-3-Clause | Distributed task queue |
| [Redis](https://github.com/redis/redis-py) | 6.4.0 | MIT | Cache and message broker client |
| [psycopg2-binary](https://www.psycopg.org) | 2.9.10 | LGPL (with exceptions) | PostgreSQL adapter |
| [Pillow](https://python-pillow.org) | 12.1.0 | HPND (MIT-like) | Image processing, sanitization re-encoding |
| [Pydantic](https://docs.pydantic.dev) | 2.13.5 | MIT | Data validation, JSON schemas |
| [cryptography](https://cryptography.io) | 46.0.3 | Apache-2.0 / BSD-3-Clause | Encryption, Athena signing |
| [PyJWT](https://pyjwt.readthedocs.io) | 2.9.0 | MIT | JSON Web Token handling |
| [google-api-python-client](https://github.com/googleapis/google-api-python-client) | 2.147.0 | Apache-2.0 | Google Calendar sync |
| [google-auth-oauthlib](https://github.com/googleapis/google-auth-library-python-oauthlib) | 1.2.1 | Apache-2.0 | Google OAuth flow |
| [Stripe](https://github.com/stripe/stripe-python) | 11.3.0 | MIT | Payment gateway |
| [PayPal REST SDK](https://github.com/paypal/PayPal-Python-SDK) | 1.13.2 | Apache-2.0 | Payment gateway |
| [Sentry SDK](https://github.com/getsentry/sentry-python) | 2.35.0 | MIT | Error tracking |
| [ChromaDB](https://www.trychroma.com) | 1.5.1 | Apache-2.0 | Vector store (Alice RAG) |
| [sentence-transformers](https://www.sbert.net) | 5.2.3 | Apache-2.0 | Embedding models (Alice) |
| [WeasyPrint](https://weasyprint.org) | 69.0+ | BSD-3-Clause | PDF generation |
| [openpyxl](https://openpyxl.readthedocs.io) | 3.1.5+ | MIT | Excel export |
| [python-docx](https://python-docx.readthedocs.io) | 1.2.0+ | MIT | Word document generation |
| [python-barcode](https://github.com/WhyNotHugo/python-barcode) | 0.16.1+ | MIT | Barcode generation |
| [qrcode](https://github.com/lincolnloop/python-qrcode) | 8.2+ | BSD | QR code generation |
| [num2words](https://github.com/savoirfairelinux/num2words) | 0.5.14+ | LGPL-2.1 | Number-to-words conversion |
| [drf-spectacular](https://github.com/tfranzel/drf-spectacular) | 0.29.0 | BSD-3-Clause | OpenAPI schema generation |
| [Faker](https://faker.readthedocs.io) | 20.1.0 | MIT | Test data generation |
| [Flower](https://flower.readthedocs.io) | 2.0.1 | BSD-3-Clause | Celery monitoring |
| [httpx](https://www.python-httpx.org) | 0.28.1 | BSD-3-Clause | Async HTTP client |
| [python-decouple](https://github.com/HBNetwork/python-decouple) | 3.8 | MIT | Environment config |
| [pytest](https://pytest.org) | 8.3.2 | MIT | Testing framework |
| [pytest-django](https://pytest-django.readthedocs.io) | 4.9.0 | BSD-3-Clause | Django test integration |
| [factory-boy](https://factoryboy.readthedocs.io) | 3.3.3 | MIT | Test fixture generation |
| [nameparser](https://github.com/derek73/python-nameparser) | 2.2.0 | LGPL-2.1 | Contact name parsing |
| [django-extensions](https://github.com/django-extensions/django-extensions) | 4.1 | MIT | Management command utilities |
| [humanize](https://github.com/jmoiron/humanize) | 4.12.3 | MIT | Human-readable formatting |
| [pytest-cov](https://github.com/pytest-dev/pytest-cov) | 7.0.0 | MIT | Test coverage reporting |

### Optional (document sanitization pipeline)

| Library | License | Purpose |
|---------|---------|---------|
| [pyclamd](https://github.com/xael-fry/pyClam) | LGPL-3.0 | ClamAV Python wrapper |
| [ClamAV](https://www.clamav.net) | GPL-2.0 | Antivirus scanning daemon |

---

## Frontend (TypeScript / React)

| Library | Version | License | Purpose |
|---------|---------|---------|---------|
| [React](https://react.dev) | 19.x | MIT | UI framework |
| [React DOM](https://react.dev) | 19.x | MIT | DOM rendering |
| [React Router](https://reactrouter.com) | 7.x | MIT | Client-side routing |
| [Redux Toolkit](https://redux-toolkit.js.org) | 2.x | MIT | State management |
| [React Redux](https://react-redux.js.org) | 9.x | MIT | React-Redux bindings |
| [Axios](https://axios-http.com) | 1.x | MIT | HTTP client |
| [Tailwind CSS](https://tailwindcss.com) | 4.x | MIT | Utility-first CSS |
| [pdfme](https://pdfme.com) | 6.x | MIT | PDF template design and generation |
| [ApexCharts](https://apexcharts.com) | 4.x | MIT | Charts and dashboards |
| [React ApexCharts](https://github.com/apexcharts/react-apexcharts) | 1.x | MIT | React chart wrapper |
| [Lucide React](https://lucide.dev) | 0.518.x | ISC | Icon library |
| [React Icons](https://react-icons.github.io/react-icons) | 5.x | MIT | Icon library |
| [date-fns](https://date-fns.org) | 4.x | MIT | Date utilities |
| [Zod](https://zod.dev) | 3.x | MIT | Schema validation |
| [React Hook Form](https://react-hook-form.com) | 7.x | MIT | Form handling |
| [@hookform/resolvers](https://github.com/react-hook-form/resolvers) | 5.x | MIT | Form validation resolvers (Zod) |
| [React DnD](https://react-dnd.github.io/react-dnd) | 16.x | MIT | Drag and drop (Kanban) |
| [clsx](https://github.com/lukeed/clsx) | 2.x | MIT | Classname utility |
| [Sass](https://sass-lang.com) | 1.x | MIT | CSS preprocessor |
| [react-international-phone](https://github.com/nicothin/react-international-phone) | 4.x | MIT | Phone input formatting |
| [react-helmet-async](https://github.com/staylor/react-helmet-async) | 2.x | Apache-2.0 | Document head manager |
| [tailwind-merge](https://github.com/dcastil/tailwind-merge) | 3.x | MIT | Tailwind class merging |
| [@uiw/react-md-editor](https://uiwjs.github.io/react-md-editor) | 4.x | MIT | Markdown editor |

### Build tools

| Library | Version | License | Purpose |
|---------|---------|---------|---------|
| [Vite](https://vite.dev) | 6.x | MIT | Build tool and dev server |
| [TypeScript](https://typescriptlang.org) | 5.7.x | Apache-2.0 | Type system |
| [ESLint](https://eslint.org) | 9.x | MIT | Linting |
| [Vitest](https://vitest.dev) | 4.x | MIT | Unit testing |
| [vite-plugin-svgr](https://github.com/pd4d10/vite-plugin-svgr) | 4.x | MIT | SVG React component loader |

---

## Infrastructure

| Software | License | Purpose |
|----------|---------|---------|
| [PostgreSQL](https://postgresql.org) | PostgreSQL License (MIT-like) | Primary database |
| [Redis](https://redis.io) | RSALv2 / SSPLv1 (server); MIT (client) | Cache, Celery broker |
| [Ollama](https://ollama.com) | MIT | Local LLM runtime (Alice, Allie) |
| [Nginx](https://nginx.org) | BSD-2-Clause | Reverse proxy (production) |
| [Cloudflare](https://cloudflare.com) | Proprietary (service) | CDN, DNS, Access (production) |

---

## License compatibility

WebClerk is released under the **Apache License, Version 2.0**
(Copyright 2024-2026 JPods LLC). All dependencies listed above are
compatible with Apache-2.0 distribution. LGPL libraries (psycopg2,
num2words, nameparser, pyclamd) are used as dynamically-linked dependencies, not
modified or statically embedded. GPL-2.0 (ClamAV) is an optional runtime
dependency invoked via socket — not linked.
