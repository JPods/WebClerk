# webClerk3

Project Docs Link: 
[Google Docs](https://docs.google.com/document/d/1a8ZYgSVpJsa6VhhEPkW5bOreRfY4mZ0tuRk0NHJIFJI/edit?usp=sharing)

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
  - python venv .
  - source ./bin/activate
  - pip install -r requirements.txt
  - psql -U an7or -d postgres | psql -U williamjames -d postgres
  - CREATE DATABASE commerce_expert;
  - CTRL+Z
  - rm */migrations/0*.py
  - python manage.py makemigrations
  - python manage.py migrate
  - python manage.py createsuperuser
  - python manage.py runserver

#### if you face postgres issues, reset it:
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
  - python manage.py runserver