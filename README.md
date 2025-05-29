# webClerk3

Project Docs Link: [Google Docs](https://docs.google.com/document/d/1a8ZYgSVpJsa6VhhEPkW5bOreRfY4mZ0tuRk0NHJIFJI/edit?usp=sharing)

### How to run this project:
1. *in project root path terminal:* `source ./bin/activate`
   1. *For the first timer:*
      1. `python venv .`
      2. `pip install -r requirements.txt`
2. *clear old migration:* `rm core/migrations/0*.py`
3. *create migration:* `python manage.py makemigrations`
4. *apply migration:* `python manage.py migrate`
5. *run server:* `python manage.py runserver`

*Note: create a superuser if you don't have:* `python manage.py createsuperuser`

#### Close all postgreSQL connection:
```
psql -U an7or -d postgres
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'commerce_expert'
  AND pid <> pg_backend_pid();
```

#### Drop & create database:
```
DROP DATABASE IF EXISTS commerce_expert;
CREATE DATABASE commerce_expert;
```

#### Drop table:
```
DROP TABLE IF EXISTS contacts;
```

#### Clear core/migrations:
```
rm core/migrations/0*.py
```