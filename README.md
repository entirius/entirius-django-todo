# entirius-django-todo

A Django module for tasks for people in Entirius, the open-source modular ecommerce platform.
Any module gives a person something to do by a date, about any object; the person sees it in one "today" list and
gets a bell notification when it is due.

[![PyPI](https://img.shields.io/pypi/v/entirius-django-todo.svg)](https://pypi.org/project/entirius-django-todo/)
[![Python](https://img.shields.io/pypi/pyversions/entirius-django-todo.svg)](https://pypi.org/project/entirius-django-todo/)
[![License: MPL-2.0](https://img.shields.io/badge/license-MPL--2.0-blue.svg)](https://github.com/entirius/entirius-django-todo/blob/develop/LICENSE)

## What it does

- Stores tasks (`mail`, `phone`, `linkedin`, `meeting`, `todo`) about an opaque subject reference, with a due
  date, an owner and an outcome when closed.
- Lets a calling module create a task idempotently through a `dedup_key`.
- Lists tasks by owner, status, due bucket (`overdue`, `today`, `upcoming`, `none`) in the caller's time zone, and
  sums up one person's day (`today/`).
- Sends one personal, non-escalating bell notification when a task falls due (with `entirius-django-notifications`).
- Exposes an admin API (JWT, Pydantic schemas, OpenAPI) for the CMS.

## Installation

```shell
uv add entirius-django-todo
pip install entirius-django-todo
```

Optional extras: `entirius-django-todo[notifications]` (the due reminder), `entirius-django-todo[access]` (the
`todo.tasks` access area). Without notifications the reminder task does nothing.

```python
INSTALLED_APPS = [
    # ...
    "django_utils",
    "django_todo",
]

# main/urls.py
urlpatterns.append(path("", include("django_todo.urls")))
```

The module needs a Celery worker consuming the `todo_default` queue and the reminder beat entry. Settings
(`TODO_QUEUE_DEFAULT`, `TODO_REMIND_BATCH`) and the beat entry: `docs/install.md` —
https://github.com/entirius/entirius-django-todo/blob/develop/docs/install.md

## Quick start

```python
from django_todo.services import task_service

task_service.create(
    channel_idx="my-channel",
    subject_ref="leads.Company:42",
    subject_label="Example Ltd",
    kind="phone",
    title="Call back about the offer",
    owner_id=7,
    created_by="rule:reply-interested",
    source="leads.reply.interested",
    dedup_key="reply:1234",
)
```

## Requirements

- Python 3.11 or newer, Django 4.2 or newer.
- PostgreSQL.
- A Celery worker consuming the `todo_default` queue, Celery beat and a `celery_once` backend.
- Entirius packages pulled in: `entirius-django-utils`.

## Documentation

- Module docs: https://github.com/entirius/entirius-django-todo/tree/develop/docs
- Entirius documentation: https://docs.entirius.com/
- Changelog: https://github.com/entirius/entirius-django-todo/blob/develop/CHANGELOG.md

## Part of Entirius

This module runs inside the Entirius backend service (Volkanos); other modules create tasks for people.

- Backend service: https://github.com/entirius/entirius-service-volkanos
- Docker harness: https://github.com/entirius/entirius-zeno
- Sibling modules: https://github.com/entirius/entirius-django-notifications, https://github.com/entirius/entirius-django-leads

## Development

```shell
make install     # sync dependencies (uv, incl. extras)
make check       # lint + format check (ruff)
make test        # test suite (pytest; PostgreSQL through DATABASE_URL)
```

Development and agent instructions: https://github.com/entirius/entirius-django-todo/blob/develop/AGENTS.md

## License

Mozilla Public License 2.0 (MPL-2.0) — see https://github.com/entirius/entirius-django-todo/blob/develop/LICENSE.
