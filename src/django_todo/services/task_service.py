# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tasks for people: the only writer of `Task`. `subject_ref` and `contact_ref` are opaque here."""

from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta, tzinfo
from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.db import IntegrityError, transaction
from django.db.models import Count, F, Q, QuerySet
from django.dispatch import Signal
from django.utils import timezone

from django_todo.enums import Due, Kind, Status
from django_todo.models import Task
from django_todo.signals import task_closed, task_created, task_reopened

# `update()` refuses every other field: status, closing and dedup go through their own functions.
EDITABLE_FIELDS = frozenset({"title", "note", "due_at", "kind", "owner_id"})
# A change of either clears `reminded_at`: the new date or the new owner gets the reminder.
REMIND_AGAIN_ON = ("due_at", "owner_id")
# `list_tasks(owner=NO_OWNER)` returns tasks nobody owns.
NO_OWNER = "none"
ERASED = "[erased]"
TODAY_ROWS = 50
UPCOMING_DAYS = 7


class TaskStateError(ValueError):
    """The task's status does not allow the change (closing a closed task, reopening an open one)."""


@dataclass(frozen=True)
class TodaySummary:
    overdue: int
    today: int
    upcoming_7d: int
    rows: list[Task]


def create(
    *,
    channel_idx: str,
    subject_ref: str,
    subject_label: str,
    kind: str,
    title: str,
    note: str = "",
    due_at: datetime | None = None,
    owner_id: int | None = None,
    contact_ref: str = "",
    created_by: str,
    source: str = "",
    dedup_key: str | None = None,
) -> Task:
    """A new open task; with a `dedup_key` that matches an open task of the channel, that task unchanged.

    Raises `ValueError` for an unknown kind or an owner that is not an active staff user.
    """
    if dedup_key and (existing := _open_with_key(channel_idx, dedup_key)) is not None:
        return existing
    task = Task(
        channel_idx=channel_idx, subject_ref=subject_ref, subject_label=subject_label, contact_ref=contact_ref,
        kind=Kind(kind).value, title=title, note=note, due_at=due_at, owner_id=_assignable(owner_id),
        created_by=created_by, source=source, dedup_key=dedup_key or None,
    )  # fmt: skip
    return _insert(task)


def _insert(task: Task) -> Task:
    try:
        with transaction.atomic():
            task.save()
    except IntegrityError:
        if task.dedup_key is None:
            raise
        # A concurrent create with the same key won the open-task constraint: return its task, or insert again
        # when it was closed in the meantime.
        existing = _open_with_key(task.channel_idx, task.dedup_key)
        return existing if existing is not None else _insert(task)
    _send_on_commit(task_created, task)
    return task


def _open_with_key(channel_idx: str, dedup_key: str) -> Task | None:
    return Task.objects.filter(channel_idx=channel_idx, dedup_key=dedup_key, status=Status.OPEN).first()


def _assignable(owner_id: int | None) -> int | None:
    if owner_id is None:
        return None
    if not get_user_model().objects.filter(pk=owner_id, is_active=True, is_staff=True).exists():
        raise ValueError(f"Owner {owner_id} is not an active staff user.")
    return owner_id


def update(task: Task, updates: dict[str, Any]) -> Task:
    """Apply whitelisted fields; a changed `due_at` or owner clears `reminded_at`, so it is reminded again.

    Saves only those fields: a concurrent close or reminder stamp is never written back.
    """
    invalid = set(updates) - EDITABLE_FIELDS
    if invalid:
        raise ValueError(f"Fields not editable via update: {sorted(invalid)}")
    if "kind" in updates:
        updates = {**updates, "kind": Kind(updates["kind"]).value}
    if "owner_id" in updates:
        _assignable(updates["owner_id"])
    if any(field in updates and updates[field] != getattr(task, field) for field in REMIND_AGAIN_ON):
        task.reminded_at = None
    for field, value in updates.items():
        setattr(task, field, value)
    task.save(update_fields=[*updates, "reminded_at", "modified_at"])
    return task


def close(task: Task, *, outcome: str, actor: str) -> Task:
    """Done with what happened. Raises `TaskStateError` when the task is not open."""
    return _finish(task, Status.DONE, outcome=outcome, actor=actor)


def cancel(task: Task, *, actor: str, reason: str = "") -> Task:
    """Cancelled — a mistake or no longer needed; the reason is the outcome. Raises `TaskStateError`."""
    return _finish(task, Status.CANCELLED, outcome=reason, actor=actor)


def _finish(task: Task, status: Status, *, outcome: str, actor: str) -> Task:
    changes = {"status": status, "outcome": outcome, "done_at": timezone.now(), "done_by": actor}
    if not Task.objects.filter(pk=task.pk, status=Status.OPEN).update(**changes, modified_at=timezone.now()):
        raise TaskStateError("Only an open task can be closed.")
    task.refresh_from_db()
    _send_on_commit(task_closed, task)
    return task


def reopen(task: Task, *, actor: str) -> Task:
    """Open again; `done_at`, `done_by` and `reminded_at` clear, the outcome stays. Raises `TaskStateError` when the
    task is open or another open task holds its `dedup_key`."""
    changes = {
        "status": Status.OPEN,
        "done_at": None,
        "done_by": "",
        "reminded_at": None,
        "modified_at": timezone.now(),
    }
    try:
        with transaction.atomic():
            reopened = Task.objects.filter(pk=task.pk).exclude(status=Status.OPEN).update(**changes)
    except IntegrityError:
        raise TaskStateError("Another open task holds the same dedup key.") from None
    if not reopened:
        raise TaskStateError("The task is already open.")
    task.refresh_from_db()
    _send_on_commit(task_reopened, task)
    return task


def _send_on_commit(signal: Signal, task: Task) -> None:
    transaction.on_commit(lambda: signal.send(sender=Task, task=task))


def get_task(channel_idx: str, pk: int) -> Task:
    """Raises `Task.DoesNotExist` for a missing row or another channel's."""
    return Task.objects.select_related("owner").get(channel_idx=channel_idx, pk=pk)


def list_tasks(
    channel_idx: str,
    *,
    owner: int | str | None = None,
    status: str | None = None,
    due: str | None = None,
    subject_ref: str | None = None,
    kind: str | None = None,
    tz: tzinfo = UTC,
) -> QuerySet[Task]:
    """Filtered tasks of a channel, soonest due first, no deadline last. `owner`: a user id or `NO_OWNER`;
    `due`: a `Due` bucket on the local day of `tz`."""
    qs = Task.objects.filter(channel_idx=channel_idx).select_related("owner")
    if owner is not None:
        qs = qs.filter(owner__isnull=True) if owner == NO_OWNER else qs.filter(owner_id=owner)
    if due is not None:
        qs = qs.filter(_due_filter(Due(due), tz))
    exact = {"status": status, "subject_ref": subject_ref, "kind": kind}
    qs = qs.filter(**{field: value for field, value in exact.items() if value is not None})
    return qs.order_by(F("due_at").asc(nulls_last=True), "pk")


def _local_midnight(tz: tzinfo, days_ahead: int = 0) -> datetime:
    """Start of the local day `days_ahead` from today in `tz`, as an aware datetime."""
    local_today = timezone.now().astimezone(tz).date()
    return datetime.combine(local_today + timedelta(days=days_ahead), time.min, tzinfo=tz)


def _due_filter(due: Due, tz: tzinfo) -> Q:
    today, tomorrow = _local_midnight(tz), _local_midnight(tz, 1)
    return {
        Due.OVERDUE: Q(due_at__lt=today),
        Due.TODAY: Q(due_at__gte=today, due_at__lt=tomorrow),
        Due.UPCOMING: Q(due_at__gte=tomorrow),
        Due.NONE: Q(due_at__isnull=True),
    }[due]


def today(channel_idx: str, user: AbstractBaseUser, *, tz: tzinfo = UTC) -> TodaySummary:
    """The user's open tasks: counts per bucket and the first rows of overdue + today, oldest due first."""
    mine = Task.objects.filter(channel_idx=channel_idx, status=Status.OPEN, owner_id=user.pk)
    week_end = _local_midnight(tz, 1 + UPCOMING_DAYS)
    counts = mine.aggregate(
        overdue=Count("pk", filter=_due_filter(Due.OVERDUE, tz)),
        today=Count("pk", filter=_due_filter(Due.TODAY, tz)),
        upcoming_7d=Count("pk", filter=_due_filter(Due.UPCOMING, tz) & Q(due_at__lt=week_end)),
    )
    due_by_tonight = mine.filter(due_at__lt=_local_midnight(tz, 1)).select_related("owner")
    rows = list(due_by_tonight.order_by("due_at", "pk")[:TODAY_ROWS])
    return TodaySummary(**counts, rows=rows)


def scrub(*, subject_ref: str | None = None, contact_ref: str | None = None) -> int:
    """Erase the free text of every task about the subject or the contact (called by the module owning them).

    `title`, `note`, `outcome` become `[erased]`, `subject_label` clears; returns the number of tasks.
    """
    if not subject_ref and not contact_ref:
        raise ValueError("scrub needs a subject_ref or a contact_ref.")
    match = Q(subject_ref=subject_ref) if subject_ref else Q()
    if contact_ref:
        match |= Q(contact_ref=contact_ref)
    erased = {"title": ERASED, "note": ERASED, "outcome": ERASED, "subject_label": ""}
    return Task.objects.filter(match).update(**erased, modified_at=timezone.now())
