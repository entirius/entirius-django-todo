---
title: Test suite map
description: Which test file covers what.
---

Postgres only (`tests/settings.py`): `DATABASE_URL`, else `postgresql://postgres:postgres@localhost:5432/test_todo`.
Migrations run in tests. `django_notifications` and `django_access` join `INSTALLED_APPS` when importable
(`make install` = all extras; the entirius-zeno service container has both); without them the reminder and
access-ownership files skip.

- `test_task_service.py` — create and its `task_created` on commit; dedup returns the open task unchanged, a new
  one after closing, per channel, never without a key; unknown kind and non-staff owner refused; the update
  whitelist refuses `status`, `done_at`, `dedup_key`, `channel_idx`, `reminded_at`; a new `due_at` clears
  `reminded_at`; close / cancel store outcome and emit `task_closed`; closing twice refused; reopen and its
  refusals; scrub by `subject_ref` and by `contact_ref`.
- `test_task_lists.py` — every `due` bucket on both sides of the Warsaw and Tokyo midnights; order; owner, status,
  kind and subject filters; `today()` counts, rows, cap and time zone.
- `test_reminder.py` — one personal bell-only notification per due task; again after the due date changes; never
  for done, cancelled, unowned or not-yet-due tasks; an unknown channel is stamped; without notifications nothing
  happens; the batch limit; the beat task.
- `test_admin_api.py` — `POST tasks/` then `today/` for the owner and not for another user; owner default and
  null; validation; list filters (`owner=me|none|<id>`, `due` + `tz`, `status`, pagination) and bad queries;
  PATCH whitelist; `done/` stores the outcome and emits `task_closed`; 409s; reopen; cancel; no DELETE; 404 for
  another channel; 401 / 403.
- `test_admin.py` — the Django admin lists tasks and refuses add and change.
- `test_access_ownership.py` — every admin route carries an area of this app.
- `test_openapi.py` — `spectacular --validate --fail-on-warn`.
- `test_migrations.py` — no model change without a migration.
- `test_gdpr.py` — both hooks exist and return empty results.

In the entirius-zeno harness: `make module-test MODULE=entirius-django-todo`.
