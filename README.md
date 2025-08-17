# webClerk3

Project Docs Link: 
[Google Docs](https://docs.google.com/document/d/1a8ZYgSVpJsa6VhhEPkW5bOreRfY4mZ0tuRk0NHJIFJI/edit?usp=sharing)

CONTRIBUTING:

- Antor Ahmed
- Riju Karar
- Samir Biswas
- Sanjutka Patra
- CoPilot
- Bill James

Data basics
data:  all_tables_export.json
import function: core/management/commands/import_all_tables.py

Path basics

webClerk3/
├── core/
│   ├── models.py
│   ├── views.py
│   ├── tasks.py      # <--- Put tasks here for core app
│   └── locale/
├── communications/
│   ├── models.py
│   ├── views.py
│   ├── tasks.py      # <--- Put tasks here for communications app
│   └── locale/
├── webclerk3_api/
│   ├── settings.py
│   ├── celery.py     # <--- Celery app config only
│   └── ...
├── templates/
├── static/
├── media/
├── logs/
├── .env
├── manage.py
└── README.md

-----------------------------
### Install:
-----------------------------

  - Celery
  -- video
  - Redis
  -- video
  
-----------------------------
### How to run this project:
-----------------------------
#### a. if everything OK, just run:
  - source ./bin/activate
  - python manage.py runserver

#### if not run for: Port is already in use:
  - kill -9 $(lsof -t -i :8000)

#### b. if add/remove/modify table or column:
  - source ./bin/activate
  - python manage.py makemigrations
  - python manage.py migrate
  - python manage.py runserver

#### c. if running for the first time:
  - python -m venv .
  - source ./bin/activate
  - pip install -r requirements.txt
  - psql -U an7or -d postgres | psql -U williamjames -d postgres
  - CREATE DATABASE commerce_expert;
  - CTRL+Z
  - rm */migrations/0*.py
  - python manage.py makemigrations
  - python manage.py migrate
  - python manage.py createsuperuser
  - python manage.py load_default_access
  - python manage.py runserver

#### if you face postgres issues, reset it:
  - source ./bin/activate
  - psql -U an7or -d postgres | psql -U williamjames -d postgres
  - SELECT pg_terminate_backend(pid) FROM pg_stat_activity 
    WHERE datname = 'commerce_expert' AND pid <> pg_backend_pid();
  - DROP DATABASE IF EXISTS commerce_expert;
  - CREATE DATABASE commerce_expert;
  - CTRL+Z
  - rm */migrations/0*.py
  - python manage.py makemigrations
  - python manage.py migrate
  - python manage.py createsuperuser
  - python manage.py load_default_access
  - python manage.py runserver


#### working with github:
  -Start working -- every day at start
    - git pull origin dev
    - Run python [manage.py](http://_vscodecontentref_/0) check_services or ./check_services.sh before starting development.

  - After adding a feature add changes to git site
    -  git add .
    -  git commit -m"message"
    -  git push

  -go to [github.com](https://github.com/JPods/webClerk3/branches)
    - click Pull requests tab
    - click button New pull request
    - Comparing changes dev <- user_dev
    - Click through the buttons



  ## 🎯 Architecture Overview

**Universal API System** - One API pattern handles all data operations across all tables (contacts, actions, emails, phones, domains, addresses).

### Pattern Structure for development use without front end
```
core/templates/
├── base.html                 # Main base with lesson1-style nav
├── core/
│   ├── home.html            # Landing page
│   ├── about.html           # About page
│   └── contact.html         # Contact detail (if still needed)
└── auth/
    ├── login.html           # Authentication
    └── signup.html          # Registration
```

### Universal API Endpoints
  - details are below other project commands

-----------------------------
### How to run this project:
-----------------------------

#### a. if everything OK, just run:
  - `source ./bin/activate`
  - `python manage.py runserver`
  - Visit: `http://localhost:8000/`

#### if not run for: Port is already in use:
  - `kill -9 $(lsof -t -i :8000)`

#### b. if add/remove/modify table or column:
  - `source ./bin/activate`
  - `python manage.py makemigrations`
  - `python manage.py migrate`
  - `python manage.py runserver`

#### c. if running for the first time:
  - `python -m venv .`
  - `source ./bin/activate`
  - `pip install -r requirements.txt`
  - `psql -U an7or -d postgres` | `psql -U williamjames -d postgres`
  - `CREATE DATABASE commerce_expert;`
  - `CTRL+Z`
  - `rm */migrations/0*.py`
  - `python manage.py makemigrations`
  - `python manage.py migrate`
  - `python manage.py createsuperuser`
  - `python manage.py load_default_access`
  - `python manage.py runserver`

#### scripts are in webclerk3/core/management/commands:
  -  build demo data: python manage.py populate_test_data
        runs populate_test_data.py
  % 

#### if you face postgres issues, reset it:
  - `source ./bin/activate`
  - `psql -U an7or -d postgres` | `psql -U williamjames -d postgres`
  - `SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'commerce_expert' AND pid <> pg_backend_pid();`
  - `DROP DATABASE IF EXISTS commerce_expert;`
  - `CREATE DATABASE commerce_expert;`
  - `CTRL+Z`
  - `rm */migrations/0*.py`
  - `python manage.py makemigrations`
  - `python manage.py migrate`
  - `python manage.py createsuperuser`
  - `python manage.py load_default_access`
  - `python manage.py runserver`

-----------------------------
### Universal API Usage Examples:
  - webclerk3/core/urls.py

#### View All Contacts:
`http://localhost:8000/wcapi/manage/?table_name=contacts`

#### View Specific Contact:
`http://localhost:8000/wcapi/manage/?table_name=contacts&id=123`

#### Manage Contact's Emails:
`http://localhost:8000/wcapi/manage/?table_name=emails&contact_id=123`

#### Create New Action:
`http://localhost:8000/wcapi/manage/?table_name=actions&mode=create`

#### API Data Retrieval:
`http://localhost:8000/wcapi/get/?table_name=contacts&id=123`

-----------------------------
### Key Features:
-----------------------------

✅ **Universal API** - One pattern for all tables
✅ **Contact-Centric** - Everything revolves around contacts
✅ **Relationship Management** - JSON refs system
✅ **Lesson1-Style Navigation** - Clean, emoji-driven nav
✅ **Bootstrap 5 UI** - Modern, responsive design
✅ **Django Default 404** - Developer-friendly error pages
✅ **Consolidated Patterns** - All in core/templates/
✅ **Future-Proof** - Ready for React front-end migration

-----------------------------
### Navigation Structure:
-----------------------------

🏠 **Home** → Landing page with system overview
**About** → System documentation and features
**Contacts** → `/wcapi/manage/?table_name=contacts`
**Actions** → `/wcapi/manage/?table_name=actions`
**Communications** → `/wcapi/manage/?table_name=emails`
🥳 **New Contact** → Quick create contact
**Admin** → Django admin (superusers only)
🤚 **Logout** → Clean session termination

pip install pydot (in your virtual environment)

https://graphviz.org/doc/build.html
brew install graphviz (on your Mac, for image output)

Draft model
% manage.py graph_models --pydot -a -g -o webclerk3_visualized.png

## Celery Monitoring

Flower is a web-based tool for monitoring and administrating Celery clusters.

**To install and run Flower:**
```bash
pip install flower
celery -A webclerk3_api flower
```

Visit [http://localhost:5555](http://localhost:5555) in your browser to view the dashboard.

If you see warnings like `Inspect method ... failed`, it usually means there are no active tasks or workers for those commands. Flower will still show task status, history, and queue info.

## API Rate Limiting

All API endpoints are rate limited using Django REST Framework:
- Authenticated users: 1000 requests/day
- Unauthenticated users: 100 requests/day

## Logging

All API requests and errors are logged to [webclerk3.log](http://_vscodecontentref_/0).  
Check this file for debugging and monitoring.

## Running Tests
python manage.py test

python [manage.py](http://_vscodecontentref_/1) test

Production Deployment
Add basic instructions for deploying to production (gunicorn, nginx, HTTPS, etc.).

## Environment Variables

Create a `.env` file in the project root with:

```
SECRET_KEY=your_secret_key
DEBUG=True
DATABASE_NAME=your_db_name
DATABASE_USER=your_db_user
DATABASE_PASS=your_db_password
DATABASE_HOST=localhost
DATABASE_PORT=5432
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=your_email@example.com
EMAIL_HOST_PASSWORD=your_email_password
SENTRY_DSN=
```

API Documentation Access
Document how to access your OpenAPI/Swagger docs (e.g., /api/schema/, /api/docs/).

## Internationalization (i18n)

We will used multiple languages ONLY for warning messages where clarity and speed are both required. React will manage all other language issues.

To add a new language:
1. Add the language code to `LANGUAGES` in `settings.py`.
2. Mark all user-facing strings with `{% trans %}` or `gettext_lazy`.
3. Run `python manage.py makemessages -l <lang>`.
4. Edit the `.po` files in `locale/<lang>/LC_MESSAGES/`.
5. Run `python manage.py compilemessages`.


