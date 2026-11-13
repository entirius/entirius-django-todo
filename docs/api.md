---
title: Admin API
description: Tasks of a channel and the caller's day — list, create, detail, edit, done, cancel, reopen, today; auth and errors.
---

Eight operations under `/api/todo/v2/admin/<channel_idx>/` (the host mounts `django_todo.urls`). Views are thin
(`api/admin/views/task_views.py`): parse into a Pydantic schema, call `services.task_service`, serialise. The
static spec is `docs/openapi.yaml`.

## Auth

| | |
|---|---|
| Authentication | `JWTAuthentication` — declared on the view, never inherited from the host defaults |
| Permission | `IsAdminUser` (staff) |
| Access area | `todo.tasks` (sensitive `pii`) on every view — reads need `read`, writes `write` |
| Throttle | none of its own; the host's defaults apply |

Every staff user with the area sees every task of the channel; `owner` is a filter, not a boundary.

## Endpoints

| Method | Path | Body / query | Response |
|---|---|---|---|
| GET | `tasks/` | `owner` (`me`, `none`, a user id), `status`, `due` (`overdue`, `today`, `upcoming`, `none`), `subject_ref`, `kind`, `tz`, `page`, `page_size` (≤ 100, default 20) | `TaskListResponse` — `count`, `next`, `previous`, `results`, soonest due first, no deadline last |
| POST | `tasks/` | `TaskCreateRequest` — `subject_ref`, `title` required; `subject_label`, `contact_ref`, `kind` (default `todo`), `note`, `due_at` (with an offset), `owner_id` (omitted = the caller, null = nobody) | 201 `TaskResponse`; `created_by` = the caller, `source` = `manual` |
| GET | `tasks/<id>/` | — | `TaskResponse` |
| PATCH | `tasks/<id>/` | `TaskUpdateRequest` — any of `title`, `note`, `due_at`, `kind`, `owner_id` | `TaskResponse`; a new `due_at` is reminded again |
| POST | `tasks/<id>/done/` | `{outcome}` | `TaskResponse` with `status` `done`; emits `task_closed` |
| POST | `tasks/<id>/cancel/` | `{reason}` (stored as `outcome`) | `TaskResponse` with `status` `cancelled`; emits `task_closed` |
| POST | `tasks/<id>/reopen/` | — | `TaskResponse` with `status` `open`; emits `task_reopened` |
| GET | `today/` | `tz` | `TodayResponse` — `overdue`, `today`, `upcoming_7d` counts of the caller's open tasks, `results`: the first 50 overdue and today tasks, oldest due first |

There is no DELETE (405): a mistake is cancelled.

`TaskResponse`: `id, subject_ref, subject_label, contact_ref, kind, title, note, due_at, owner{id, username, name}
| null, status, outcome, done_at, done_by, created_by, source, created`. Times are ISO 8601 in UTC.

## Errors

The v2 error shape (`error`, `message`, `debug_id`, `details[]`) of `django_utils.api.v2_errors`.

| Status | When |
|---|---|
| 400 | a body or query that fails its schema (unknown field, bad `kind`, a `due_at` without an offset, an unknown `tz`, `owner` not `me`/`none`/digits — `location` `query` for the list); an owner that is not an active staff user (`field` `owner_id`) |
| 401 / 403 | no or bad JWT / not staff or without the `todo.tasks` level |
| 404 | an unknown task or another channel's |
| 409 `CONFLICT` | done or cancel on a task that is not open; reopen on an open task, or while another open task holds its `dedup_key` |
