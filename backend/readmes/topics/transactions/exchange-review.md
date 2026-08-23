# Bundle review and acknowledgement


<!-- TOC START -->

## Table of Contents

- [Bundle review and acknowledgement](#bundle-review-and-acknowledgement)
  - [Table of Contents](#table-of-contents)

<!-- TOC END -->

Foreign/provider data is not applied automatically. Each `sync.Bundle` created by an integration has a `response.review.status` field that starts as `pending`. An authorized reviewer must accept or reject the bundle before changes are committed to core records.

Workflow (email verification example):

1) A Celery task performs verification and creates an `Bundle` with `response.review.status: pending` and `response.provider/status/deliverability` populated.
2) A reviewer accepts or rejects the bundle (admin actions provided). On acceptance, the decision service updates the target record (`Email.is_verified` and `Email.metadata.versioning.validation.review`) and marks the `Bundle` as `accepted` (or `rejected`).

Admin:

- Use the Bundles admin to bulk accept/reject. Actions call `apps.sync.services.decisions.accept_email_verification` or `reject_exchange`.

Notes:

- No migrations required; decision state is stored in JSON fields.
- Extend the decision services for other resource types by adding targeted accept_* functions.
