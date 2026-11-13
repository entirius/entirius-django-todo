---
title: Operations
description: Day-2 — running the reminder by hand, reading its logs, erasing a subject's tasks.
---

## The reminder

```shell
python manage.py shell -c "from django_todo.services import reminder_service; print(reminder_service.remind_due())"
```

Returns how many owners were notified. A task is reminded once per due date: `reminded_at` is set even when the
channel is unknown to notifications (log `event=todo.remind skipped=unknown_channel channel=… task=…`), so such a
task is never retried. To remind it again after creating the notifications channel, clear the stamp:
`Task.objects.filter(pk=…).update(reminded_at=None)`.

Repeats of one reminder (a due date moved and passed again within a minute) are counted on the existing unread
notification by notifications' dedup window, not added as a new row.

## A backlog

At most `TODO_REMIND_BATCH` reminders per run, oldest due first. After an outage the backlog drains at that rate
every 15 minutes.

## Erasing a person

The module holds no e-mail address; the GDPR hooks return nothing. The module that owns the subject or contact
calls `task_service.scrub(subject_ref=…)` or `scrub(contact_ref=…)` when it erases the person (`concept.md`).
By hand:

```shell
python manage.py shell -c "from django_todo.services import task_service; print(task_service.scrub(subject_ref='leads.Company:42'))"
```
