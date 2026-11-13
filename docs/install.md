---
title: Install
description: What a host needs — prerequisites, extras, wiring, the beat entry and the queue, the settings table.
---

## Prerequisites

| Requirement | Why | Verify |
|---|---|---|
| `django_todo` in `INSTALLED_APPS` | the model and the admin API | `manage.py check` |
| PostgreSQL | the open-task dedup constraint is a partial unique index; the suite has no sqlite path | `manage.py migrate` |
| `rest_framework_simplejwt` | the admin views authenticate with `JWTAuthentication` explicitly | a 401 without a token |
| A Celery worker consuming **`todo_default`** | `remind_due` runs there | `celery -A main worker -Q …,todo_default` |
| Celery beat with the reminder entry (below) and a `celery_once` backend (`app.conf.ONCE`) | nothing is reminded without it; `QueueOnce` keeps two runs from overlapping | a bell notification within 15 min of a due date |
| `SPECTACULAR_SETTINGS["OAS_VERSION"] = "3.1.0"` | Pydantic documents examples as JSON Schema 2020-12 | `manage.py spectacular --validate` |
| *Optional:* extra `notifications` + `django_notifications` in `INSTALLED_APPS`, a notifications `Channel` per `channel_idx` | the due reminder; without the package the run is a no-op; a channel unknown to notifications is stamped without a notification (warning `event=todo.remind skipped=unknown_channel`) | a `Due: …` row in the bell |
| *Optional:* extra `access` + `django_access` | the `todo.tasks` area (read from the AppConfig, nothing imported) | `GET api/access/v2/admin/catalogue/` lists it |

```shell
pip install "entirius-django-todo[notifications,access]"
```

## Wiring

```python
INSTALLED_APPS += ["django_todo"]
urlpatterns.append(path("", include("django_todo.urls")))  # api/todo/v2/admin/<channel_idx>/
CELERY_BEAT_SCHEDULE["todo-remind-due"] = {"task": "django_todo.remind_due", "schedule": 900.0}
```

Route the queue the way the host routes the others (every task declares `queue=TODO_QUEUE_DEFAULT`, so a worker
that consumes `todo_default` is all it needs).

## Settings

Read **once, at import** of `django_todo.settings` — set them in the host settings file.

| Setting | Default | Meaning |
|---|---|---|
| `TODO_QUEUE_DEFAULT` | `todo_default` | the queue of `remind_due` |
| `TODO_REMIND_BATCH` | `200` | at most this many reminders per run; the rest wait for the next run, oldest due first |

## Bootstrap order

1. Install the package (with the extras), add the app, mount the URLs.
2. `manage.py migrate` (`django_todo` 0001).
3. Add the beat entry, let a worker consume `todo_default`, restart worker and beat.
4. With notifications: make sure every channel that has tasks has a notifications `Channel`.
