# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Due reminders: one personal, bell-only notification per open task that fell due."""

import logging

from django.apps import apps
from django.utils import timezone

from django_todo.enums import Status
from django_todo.models import Task
from django_todo.settings import TODO_REMIND_BATCH

logger = logging.getLogger(__name__)

# The recipient role of every reminder; the reminder is addressed to the owner alone (`recipient_user_id`).
REMIND_ROLE = "todo"
SEVERITY = "medium"


def remind_due() -> int:
    """Notify the owners of up to `TODO_REMIND_BATCH` due tasks; returns how many were notified.

    Without django_notifications nothing is sent and nothing is stamped.
    """
    if not apps.is_installed("django_notifications"):
        return 0
    due = Task.objects.filter(
        status=Status.OPEN, owner__isnull=False, due_at__lte=timezone.now(), reminded_at__isnull=True
    ).order_by("due_at", "pk")[:TODO_REMIND_BATCH]
    return sum(_remind(task) for task in due)


def _remind(task: Task) -> bool:
    notified = _notify_owner(task)
    # Stamped either way: a channel unknown to notifications must not hold the batch back on every run.
    Task.objects.filter(pk=task.pk).update(reminded_at=timezone.now())
    return notified


def _notify_owner(task: Task) -> bool:
    # Lazy: the notifications module is a soft dependency.
    from django_notifications.models import Channel
    from django_notifications.services.notify_service import notify

    try:
        notify(
            channel_idx=task.channel_idx,
            recipient_role=REMIND_ROLE,
            recipient_user_id=task.owner_id,
            escalate=False,
            severity=SEVERITY,
            subject_ref=task.subject_ref,
            title=f"Due: {task.title}"[:200],
        )
    except Channel.DoesNotExist:
        logger.warning("event=todo.remind skipped=unknown_channel channel=%s task=%s", task.channel_idx, task.pk)
        return False
    return True
