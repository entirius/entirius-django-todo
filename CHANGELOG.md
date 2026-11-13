# Changelog

## Unreleased — 0.1.0

First release. Tasks for people: any module gives a person something to do by a date, about any object.

- `Task` (`channel_idx`, opaque `subject_ref` / `contact_ref`, `subject_label`, kind `mail | phone | linkedin |
  meeting | todo`, `due_at`, `owner`, status `open | done | cancelled`, outcome, `dedup_key`, `reminded_at`).
- `task_service`: `create` (idempotent through `dedup_key` among open tasks), `update` (field whitelist), `close`,
  `cancel`, `reopen`, `list_tasks` (owner, status, due bucket on the caller's local day, subject, kind), `today`,
  `scrub`. Signals `task_created`, `task_closed`, `task_reopened`, on commit.
- Beat `django_todo.remind_due` (queue `todo_default`): one personal, bell-only notification per due task through
  `entirius-django-notifications` 0.3.0 (soft dependency).
- Admin API v2 under `api/todo/v2/admin/<channel_idx>/`: `tasks/` (list, create), `tasks/<id>/` (get, patch),
  `done/`, `cancel/`, `reopen/`, `today/`. Access area `todo.tasks`.
- `django_todo.__version__ = "0.1.0"` (munin reports it); a test keeps it equal to `pyproject.toml`.
- GDPR hooks with empty results: the module holds references, not addresses.
