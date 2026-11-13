# AGENTS.md

entirius-django-todo (Django app `django_todo`) — tasks for people in Entirius: any module gives a person something
to do by a date, about any object; one "today" list and a bell notification when it is due. Table prefix
`django_todo_`, URL prefix `api/todo/v2/`.

## Commands

| Command | Meaning |
|---|---|
| `make install` | `uv sync --all-extras` |
| `make test` | pytest — PostgreSQL only: `DATABASE_URL`, else the default in `tests/settings.py` (`docs/testing.md`) |
| `make check` / `fix` | ruff lint + format (+ canonical `.gitleaks.toml` guard) |

## Conventions

- English only; MPL-2.0 header on every `.py` (`insert-license`); no Claude attribution trailers in commits or PRs.
- Layered: `models/` · `services/` · `schemas/` · `api/admin/` · `tasks/`. No logic in models or views.
- Never import a caller (`django_leads`, `django_communicator` …); `subject_ref` / `contact_ref` are never parsed.
- Never rename the package, the app label or the table prefix; never edit a released migration.
- Access: the area lives on the AppConfig (`access_areas`), every admin view carries `access_area`; a new admin
  route without one fails `tests/test_access_ownership.py`.
- Git flow: `develop` + `master`, PRs. Do not commit by default — the operator decides.

## Architecture

Read first: `docs/install.md` (host) · `docs/api.md` (caller) · `docs/concept.md` (why) ·
`docs/gotchas.md` (before editing). Extras `notifications` and `access` are soft.

```
src/django_todo/
├── apps.py  enums.py (Kind, Status, Due)  settings.py (read at import)  signals.py  gdpr.py  admin.py (read-only)
├── models/        task
├── schemas/       requests.py  responses.py
├── api/admin/     views/task_views.py  views/_base.py  urls.py
├── urls.py        api/todo/v2/admin/<channel_idx>/ → api.admin.urls
├── services/      task_service (the only writer of Task)  reminder_service (remind_due)
└── tasks/         remind.py (beat, QueueOnce)          queue `todo_default`
```

| Topic | Where |
|---|---|
| A setting's name, default, meaning (`TODO_QUEUE_DEFAULT`, `TODO_REMIND_BATCH`) | `settings.py`; the table in `docs/install.md` |
| Host wiring: app, URLs, beat entry, queue | `docs/install.md` |
| Request / response shape, auth, errors | `docs/api.md`; `schemas/`; `docs/openapi.yaml` (static export) |
| Dedup, the local day, reminders, signals, GDPR — why | `docs/concept.md` |
| Running the reminder, erasing a subject | `docs/operations.md` |
| Which test file covers what | `docs/testing.md` |
| What changed and why | `CHANGELOG.md` |

## Gotchas

- `docs/gotchas.md` is the only list. Read it before touching the service, the reminder or the API.
