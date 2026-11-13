---
title: Gotchas
description: Read before editing the service, the reminder or the API.
---

- **`subject_ref` and `contact_ref` are opaque.** Never parse them, never import the module they point at. The
  caller writes `subject_label` for display.
- **`dedup_key` is null, never `""`.** The partial unique constraint only covers non-null keys of open tasks;
  `create()` turns an empty key into null.
- **`update()` is a whitelist** (`EDITABLE_FIELDS`). Status, closing fields, `dedup_key`, `channel_idx` and
  `reminded_at` are refused — add a dedicated service function instead of widening it.
- **A changed `due_at` clears `reminded_at`**; the same value keeps it. Reopen keeps `reminded_at`, so a reopened
  overdue task is not reminded again until its due date changes.
- **Signals are sent on commit.** A receiver in a test needs `django_capture_on_commit_callbacks(execute=True)`.
- **The day is the caller's.** Buckets use the `tz` query parameter (default UTC), not `TIME_ZONE`.
- **The reminder needs a notifications `Channel` with the same idx.** Without it the task is stamped and skipped.
- **`notify()` requires `entirius-django-notifications` 0.3.0** (`recipient_user_id`, `escalate`). Until it is on
  PyPI, `pyproject.toml` resolves the sibling clone through `[tool.uv.sources]`; drop that block at its release.
- **No top-level `tasks` beyond the Celery package.** The app label is `django_todo`; URL names start with
  `todo-`, operation ids with `todo_` (enrichment owns `admin-tasks-*`).
