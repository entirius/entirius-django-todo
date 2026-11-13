# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Due reminders: one personal, bell-only notification per due task; a new due date is reminded again."""

from datetime import UTC, datetime, timedelta

import pytest
from django.utils import timezone

from django_todo.models import Task
from django_todo.services import reminder_service, task_service
from django_todo.tasks import remind_due
from tests.conftest import CHANNEL_IDX, OTHER_CHANNEL_IDX, make_task

pytestmark = pytest.mark.django_db
notifications = pytest.importorskip("django_notifications.models")


@pytest.fixture
def bell(db):
    notifications.Channel.objects.create(idx=CHANNEL_IDX, label="Default Europe")
    return notifications.Notification.objects


def _past() -> datetime:
    return timezone.now() - timedelta(minutes=5)


def test_a_due_task_gives_exactly_one_personal_bell_only_notification(bell, staff):
    task = make_task(owner_id=staff.pk, due_at=_past(), title="Call back")

    assert reminder_service.remind_due() == 1
    assert reminder_service.remind_due() == 0

    notification = bell.get()
    assert notification.recipient_user_id == staff.pk
    assert notification.escalate is False
    assert (notification.severity, notification.subject_ref, notification.title) == (
        "medium",
        "leads.Company:42",
        "Due: Call back",
    )
    assert notification.count == 1
    task.refresh_from_db()
    assert task.reminded_at is not None


def test_a_new_due_date_is_reminded_again(bell, staff):
    task = make_task(owner_id=staff.pk, due_at=_past())
    reminder_service.remind_due()
    task_service.update(task, {"due_at": _past() + timedelta(minutes=1)})

    assert reminder_service.remind_due() == 1
    # notify() counts an unread repeat inside its dedup window instead of adding a row.
    assert sum(bell.values_list("count", flat=True)) == 2


def test_never_for_done_unowned_or_not_yet_due_tasks(bell, staff):
    task_service.close(make_task(owner_id=staff.pk, due_at=_past()), outcome="", actor="anna")
    task_service.cancel(make_task(owner_id=staff.pk, due_at=_past()), actor="anna")
    make_task(due_at=_past())
    make_task(owner_id=staff.pk, due_at=timezone.now() + timedelta(hours=1))
    make_task(owner_id=staff.pk)

    assert reminder_service.remind_due() == 0
    assert not bell.exists()
    assert not Task.objects.filter(reminded_at__isnull=False).exists()


def test_a_channel_unknown_to_notifications_is_stamped_without_a_notification(bell, staff):
    task = make_task(owner_id=staff.pk, due_at=_past(), channel_idx=OTHER_CHANNEL_IDX)
    assert reminder_service.remind_due() == 0
    task.refresh_from_db()
    assert task.reminded_at is not None
    assert not bell.exists()


def test_a_reopened_due_task_is_reminded_again(bell, staff):
    task = make_task(owner_id=staff.pk, due_at=_past())
    reminder_service.remind_due()
    task_service.reopen(task_service.close(task, outcome="", actor="anna"), actor="anna")
    assert reminder_service.remind_due() == 1


def test_a_task_notify_refuses_is_stamped_and_the_batch_goes_on(monkeypatch, bell, staff):
    first = make_task(owner_id=staff.pk, due_at=datetime(2026, 1, 1, tzinfo=UTC), title="first")
    make_task(owner_id=staff.pk, due_at=_past(), title="second")
    from django_notifications.services import notify_service

    original = notify_service.notify

    def refuse_first(**kwargs):
        if kwargs["title"] == "Due: first":
            raise ValueError("Unknown recipient user")
        return original(**kwargs)

    monkeypatch.setattr(notify_service, "notify", refuse_first)
    assert reminder_service.remind_due() == 1
    first.refresh_from_db()
    assert first.reminded_at is not None
    assert list(bell.values_list("title", flat=True)) == ["Due: second"]


def test_without_notifications_nothing_is_sent_or_stamped(monkeypatch, bell, staff):
    monkeypatch.setattr(reminder_service.apps, "is_installed", lambda label: label != "django_notifications")
    task = make_task(owner_id=staff.pk, due_at=_past())
    assert reminder_service.remind_due() == 0
    task.refresh_from_db()
    assert task.reminded_at is None


def test_a_run_reminds_at_most_the_batch(monkeypatch, bell, staff):
    monkeypatch.setattr(reminder_service, "TODO_REMIND_BATCH", 1)
    oldest = make_task(owner_id=staff.pk, due_at=datetime(2026, 1, 1, tzinfo=UTC), title="old")
    make_task(owner_id=staff.pk, due_at=_past(), title="new")
    assert reminder_service.remind_due() == 1
    oldest.refresh_from_db()
    assert oldest.reminded_at is not None


def test_beat_task_runs_the_reminder(bell, staff):
    make_task(owner_id=staff.pk, due_at=_past())
    assert remind_due.name == "django_todo.remind_due"
    assert remind_due.run() == 1
