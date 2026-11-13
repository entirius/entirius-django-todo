# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Service: create with dedup, the update whitelist, close / cancel / reopen with their signals, scrub."""

from datetime import UTC, datetime

import pytest

from django_todo.enums import Status
from django_todo.models import Task
from django_todo.services import task_service
from django_todo.signals import task_closed, task_created, task_reopened
from tests.conftest import OTHER_CHANNEL_IDX, make_task, make_user

pytestmark = pytest.mark.django_db
DUE = datetime(2026, 11, 14, 9, 0, tzinfo=UTC)
SIGNALS = [(task_created, "created"), (task_closed, "closed"), (task_reopened, "reopened")]


def _recorder(log: list, name: str):
    def receiver(sender, task, **kwargs):
        log.append((name, task.pk))

    return receiver


@pytest.fixture
def received():
    """Records every todo signal sent: (signal name, task id)."""
    log = []
    pairs = [(signal, _recorder(log, name)) for signal, name in SIGNALS]
    for signal, receiver in pairs:
        signal.connect(receiver, weak=False)
    yield log
    for signal, receiver in pairs:
        signal.disconnect(receiver)


def test_create_stores_an_open_task_and_signals_on_commit(django_capture_on_commit_callbacks, received, staff):
    with django_capture_on_commit_callbacks(execute=True):
        task = make_task(owner_id=staff.pk, due_at=DUE, contact_ref="leads.Contact:7", source="manual")
    task.refresh_from_db()
    assert (task.status, task.owner_id, task.due_at, task.contact_ref) == (
        Status.OPEN,
        staff.pk,
        DUE,
        "leads.Contact:7",
    )
    assert received == [("created", task.pk)]


def test_signal_waits_for_the_commit(django_capture_on_commit_callbacks, received):
    with django_capture_on_commit_callbacks(execute=False) as callbacks:
        make_task()
    assert received == []
    assert len(callbacks) == 1


def test_dedup_returns_the_open_task_unchanged(django_capture_on_commit_callbacks, received):
    with django_capture_on_commit_callbacks(execute=True):
        first = make_task(dedup_key="reply:1")
        again = make_task(dedup_key="reply:1", title="Something else")
    assert again.pk == first.pk
    assert again.title == "Call back"
    assert Task.objects.count() == 1
    assert received == [("created", first.pk)]


def test_dedup_allows_a_new_task_after_closing():
    first = make_task(dedup_key="reply:1")
    task_service.close(first, outcome="Called.", actor="anna")
    second = make_task(dedup_key="reply:1")
    assert second.pk != first.pk
    assert second.status == Status.OPEN


def test_dedup_is_per_channel():
    first = make_task(dedup_key="reply:1")
    other = make_task(dedup_key="reply:1", channel_idx=OTHER_CHANNEL_IDX)
    assert other.pk != first.pk


def test_tasks_without_a_key_never_dedup():
    assert make_task().pk != make_task().pk
    assert make_task(dedup_key="").dedup_key is None


def test_create_refuses_an_unknown_kind_and_a_non_staff_owner():
    customer = make_user("customer")
    with pytest.raises(ValueError):
        make_task(kind="fax")
    with pytest.raises(ValueError, match="not an active staff user"):
        make_task(owner_id=customer.pk)
    assert not Task.objects.exists()


@pytest.mark.parametrize("field", ["status", "done_at", "dedup_key", "channel_idx", "reminded_at"])
def test_update_whitelist_refuses(field):
    task = make_task()
    with pytest.raises(ValueError, match="not editable"):
        task_service.update(task, {"title": "New", field: None})
    task.refresh_from_db()
    assert (task.title, task.status) == ("Call back", Status.OPEN)


def test_update_applies_whitelisted_fields(staff, other_staff):
    task = make_task(owner_id=staff.pk)
    task_service.update(task, {"title": "Write", "note": "n", "kind": "mail", "owner_id": other_staff.pk})
    task.refresh_from_db()
    assert (task.title, task.note, task.kind, task.owner_id) == ("Write", "n", "mail", other_staff.pk)


def test_update_refuses_a_bad_kind_or_owner():
    task = make_task()
    with pytest.raises(ValueError):
        task_service.update(task, {"kind": "fax"})
    with pytest.raises(ValueError):
        task_service.update(task, {"owner_id": 999999})


def test_a_new_due_date_clears_reminded_at_and_the_same_keeps_it():
    task = make_task(due_at=DUE)
    Task.objects.filter(pk=task.pk).update(reminded_at=DUE)
    task.refresh_from_db()
    task_service.update(task, {"due_at": DUE})
    assert task.reminded_at == DUE
    task_service.update(task, {"due_at": datetime(2026, 11, 15, tzinfo=UTC)})
    task.refresh_from_db()
    assert task.reminded_at is None


def test_a_new_owner_clears_reminded_at(staff, other_staff):
    task = make_task(owner_id=staff.pk, due_at=DUE)
    Task.objects.filter(pk=task.pk).update(reminded_at=DUE)
    task.refresh_from_db()
    task_service.update(task, {"owner_id": other_staff.pk})
    task.refresh_from_db()
    assert task.reminded_at is None


def test_update_never_writes_back_a_concurrent_close():
    stale = make_task()
    task_service.close(Task.objects.get(pk=stale.pk), outcome="Done.", actor="piotr")
    task_service.update(stale, {"title": "Renamed"})
    stale.refresh_from_db()
    assert (stale.title, stale.status, stale.outcome) == ("Renamed", Status.DONE, "Done.")


def test_a_lost_dedup_race_returns_the_winners_task(monkeypatch):
    """The first lookup misses (the winner inserts right after it); the insert then hits the constraint."""
    winner = make_task(dedup_key="reply:1")
    original, calls = task_service._open_with_key, []

    def miss_first(*args):
        calls.append(args)
        return None if len(calls) == 1 else original(*args)

    monkeypatch.setattr(task_service, "_open_with_key", miss_first)
    assert make_task(dedup_key="reply:1").pk == winner.pk
    assert len(calls) == 2
    assert Task.objects.count() == 1


def test_close_stores_the_outcome_and_signals(django_capture_on_commit_callbacks, received):
    task = make_task()
    with django_capture_on_commit_callbacks(execute=True):
        task_service.close(task, outcome="Agreed on a demo.", actor="anna")
    task.refresh_from_db()
    assert (task.status, task.outcome, task.done_by) == (Status.DONE, "Agreed on a demo.", "anna")
    assert task.done_at is not None
    assert ("closed", task.pk) in received


def test_cancel_stores_the_reason_and_signals(django_capture_on_commit_callbacks, received):
    task = make_task()
    with django_capture_on_commit_callbacks(execute=True):
        task_service.cancel(task, actor="anna", reason="Duplicate.")
    assert (task.status, task.outcome) == (Status.CANCELLED, "Duplicate.")
    assert ("closed", task.pk) in received


def test_closing_a_closed_task_is_refused():
    task = task_service.close(make_task(), outcome="Done.", actor="anna")
    with pytest.raises(task_service.TaskStateError):
        task_service.close(task, outcome="Again.", actor="piotr")
    with pytest.raises(task_service.TaskStateError):
        task_service.cancel(task, actor="piotr")
    task.refresh_from_db()
    assert (task.outcome, task.done_by) == ("Done.", "anna")


def test_reopen_clears_the_closing_and_signals(django_capture_on_commit_callbacks, received):
    task = task_service.close(make_task(), outcome="Done.", actor="anna")
    Task.objects.filter(pk=task.pk).update(reminded_at=DUE)
    with django_capture_on_commit_callbacks(execute=True):
        task_service.reopen(task, actor="anna")
    assert (task.status, task.done_at, task.done_by, task.outcome) == (Status.OPEN, None, "", "Done.")
    assert task.reminded_at is None
    assert ("reopened", task.pk) in received


def test_reopen_is_refused_for_an_open_task_and_a_taken_dedup_key():
    with pytest.raises(task_service.TaskStateError, match="already open"):
        task_service.reopen(make_task(), actor="anna")
    first = task_service.close(make_task(dedup_key="reply:1"), outcome="", actor="anna")
    make_task(dedup_key="reply:1")
    with pytest.raises(task_service.TaskStateError, match="dedup key"):
        task_service.reopen(first, actor="anna")


def test_scrub_by_subject_ref():
    task = task_service.close(make_task(note="Spoke to Jan."), outcome="Jan agreed.", actor="anna")
    other = make_task(subject_ref="leads.Company:43")
    assert task_service.scrub(subject_ref="leads.Company:42") == 1
    task.refresh_from_db()
    other.refresh_from_db()
    assert (task.title, task.note, task.outcome, task.subject_label) == ("[erased]",) * 3 + ("",)
    assert (other.title, other.subject_label) == ("Call back", "Example Ltd")


def test_scrub_by_contact_ref():
    task = make_task(contact_ref="leads.Contact:7", subject_ref="leads.Company:1")
    untouched = make_task(contact_ref="leads.Contact:8", subject_ref="leads.Company:1")
    assert task_service.scrub(contact_ref="leads.Contact:7") == 1
    task.refresh_from_db()
    untouched.refresh_from_db()
    assert task.title == "[erased]"
    assert untouched.title == "Call back"


def test_scrub_needs_a_reference():
    make_task()
    with pytest.raises(ValueError):
        task_service.scrub()
    assert Task.objects.get().title == "Call back"
