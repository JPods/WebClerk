<!-- Migrated from apps/support/README.md (deleted in app). -->

# Support Notes

Original external document link (may contain richer operational playbooks):

- Google Doc: <https://docs.google.com/document/d/1a8ZYgSVpJsa6VhhEPkW5bOreRfY4mZ0tuRk0NHJIFJI/edit?usp=sharing>

## Currency Reference

Sample Frankfurter API call (EUR->USD):

```http
GET https://api.frankfurter.dev/v1/latest?base=EUR&symbols=USD
```

Sample response:

```json
{"amount":1.0,"base":"EUR","date":"2025-08-22","rates":{"USD":1.1608}}
```

Use this only for development demos; production conversion rules may differ.
