---
title: Concept
description: Why the module exists, what a task is, dedup, the local day, reminders, signals and GDPR.
---

## One list of things to do

Any module can give a person something to do by a date, about any object: leads asks a salesperson to call back
an interested reply, a future module asks someone to check a contract. The person sees every task in one list
and one "today" summary, and gets a bell notification when a task falls due. The module knows nothing about its
callers: it never imports them, and it never parses their references.

## A task

| Part | Meaning |
|---|---|
| `channel_idx` | the channel the task belongs to; every read is scoped to one |
| `subject_ref` | what the task is about, `<module>.<Model>:<pk>` of the caller (`leads.Company:42`); opaque here |
| `subject_label` | what the list shows for the subject (a company name), written by the caller — no lookup back |
| `contact_ref` | a person the task is about, opaque, optional |
| `kind` | `mail`, `phone`, `linkedin`, `meeting`, `todo` — how it is done; the CMS picks the icon |
| `title`, `note` | what to do, details |
| `due_at` | the deadline, stored in UTC; null = no deadline |
| `owner` | the staff user who does it; null = nobody yet. A deleted user leaves the task unowned |
| `status` | `open` → `done` or `cancelled` → `open` again (reopen) |
| `outcome`, `done_at`, `done_by` | what happened (or why it was cancelled), when and who closed it |
| `created_by`, `source` | a username or a system actor (`rule:…`, `reply`); a machine tag of the creator (`manual`, `leads.reply.interested`) |
| `dedup_key` | the caller's idempotency key (below) |
| `reminded_at` | when the due notification went out |

There is no delete: a mistake is cancelled, so the record of what was asked stays.

## Writes go through one service

`services/task_service.py` is the only writer. `update()` changes only `title`, `note`, `due_at`, `kind` and
`owner_id`; status changes go through `close()`, `cancel()` and `reopen()`, which refuse a change the status does
not allow (`TaskStateError`, HTTP 409). An owner must be an active staff user. The Django admin is read-only.

## Dedup

A caller that reacts to events (a reply, a rule run) passes a `dedup_key`. While an open task of the channel holds
that key, `create()` returns it unchanged and sends no signal; once it is closed, the same key creates a new task.
A partial unique constraint (`channel_idx`, `dedup_key` among open tasks) makes this hold under concurrency, and a
reopen that would make two open tasks share a key is refused.

## The local day

Due dates are stored in UTC. "Overdue", "today" and "upcoming" are computed on the caller's local day: the API takes
an IANA `tz` (default `UTC`). A task due at 23:30 in Warsaw is "today" there and "overdue" in Tokyo the next
morning. `due=none` lists tasks without a deadline.

`today(channel_idx, user)` is one person's day: counts of their open tasks overdue, due today and due in the 7 days
after today, and the first 50 overdue and today tasks, oldest due first.

## Reminders

Beat runs `django_todo.remind_due` every 15 minutes. Every open task with an owner, a `due_at` in the past and no
`reminded_at` gets one notification through `django_notifications.notify()` — addressed to the owner alone
(`recipient_user_id`), bell-only (`escalate=False`), severity `medium`, recipient role `todo`, title
`Due: <title>`, the task's `subject_ref` — and is stamped `reminded_at`. A changed `due_at`, a new owner and a
reopen clear the stamp, so the new date or the new owner is reminded again. A task `notify()` refuses (a channel
unknown to notifications, an owner gone in the meantime) is stamped and logged, so it never holds the batch back.
Without the notifications module the run sends nothing and stamps nothing.

## Signals

All sent on commit with `sender=Task, task=<Task>`: `task_created` (not for a dedup hit), `task_closed` (done or
cancelled — read `task.status`), `task_reopened`. A caller shows closed tasks in its own timeline from them.

## GDPR

The GDPR contract of the platform (`gdpr_export(email)`, `gdpr_erase(email)`, discovered by the leads registry) is
keyed by an e-mail address, and a task holds none: it points at subjects and contacts through references. Both
hooks in `gdpr.py` return empty results. Free text may still name a person, so the module that owns the subject or
the contact erases its tasks when it erases that person:

```python
from django_todo.services import task_service

task_service.scrub(subject_ref="leads.Company:42")  # or contact_ref="leads.Contact:7"
```

`scrub()` replaces `title`, `note` and `outcome` with `[erased]` and clears `subject_label` of every matching task,
in every channel, and returns how many it changed. The owner (a staff user) is not a data subject of this flow.
