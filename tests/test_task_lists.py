# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Service reads: list filters, due buckets at the local day boundary in two time zones, the today summary."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone

from django_todo.services import task_service
from tests.conftest import OTHER_CHANNEL_IDX, make_task

pytestmark = pytest.mark.django_db

# 22:30 UTC: 23:30 on Nov 13 in Warsaw (UTC+1), 07:30 on Nov 14 in Tokyo (UTC+9).
NOW = datetime(2026, 11, 13, 22, 30, tzinfo=UTC)
WARSAW, TOKYO = ZoneInfo("Europe/Warsaw"), ZoneInfo("Asia/Tokyo")


@pytest.fixture
def frozen_now(monkeypatch):
    monkeypatch.setattr(timezone, "now", lambda: NOW)


def _titles(qs) -> list[str]:
    return [task.title for task in qs]


@pytest.fixture
def boundary_tasks(frozen_now):
    """Due dates on both sides of the Warsaw and the Tokyo midnights."""
    for title, due_at in [
        ("t1", datetime(2026, 11, 12, 22, 59, 59, tzinfo=UTC)),  # 23:59:59 Nov 12 Warsaw
        ("t2", datetime(2026, 11, 12, 23, 0, tzinfo=UTC)),  # midnight Nov 13 Warsaw
        ("t3", datetime(2026, 11, 13, 14, 59, 59, tzinfo=UTC)),  # 23:59:59 Nov 13 Tokyo
        ("t4", datetime(2026, 11, 13, 15, 0, tzinfo=UTC)),  # midnight Nov 14 Tokyo
        ("t5", datetime(2026, 11, 13, 23, 0, tzinfo=UTC)),  # midnight Nov 14 Warsaw
        ("t6", datetime(2026, 11, 14, 15, 0, tzinfo=UTC)),  # midnight Nov 15 Tokyo
        ("t7", None),
    ]:
        make_task(title=title, due_at=due_at)


@pytest.mark.parametrize(
    ("tz", "expected"),
    [
        (WARSAW, {"overdue": ["t1"], "today": ["t2", "t3", "t4"], "upcoming": ["t5", "t6"], "none": ["t7"]}),
        (TOKYO, {"overdue": ["t1", "t2", "t3"], "today": ["t4", "t5"], "upcoming": ["t6"], "none": ["t7"]}),
    ],
)
def test_due_buckets_at_the_day_boundary(boundary_tasks, tz, expected):
    for due, titles in expected.items():
        assert _titles(task_service.list_tasks("default-europe", due=due, tz=tz)) == titles, due


def test_list_orders_soonest_due_first_and_no_deadline_last(boundary_tasks):
    assert _titles(task_service.list_tasks("default-europe")) == ["t1", "t2", "t3", "t4", "t5", "t6", "t7"]


def test_list_filters(staff, other_staff):
    mine = make_task(title="mine", owner_id=staff.pk, kind="mail")
    make_task(title="theirs", owner_id=other_staff.pk, subject_ref="leads.Company:43")
    make_task(title="nobody's")
    make_task(title="elsewhere", owner_id=staff.pk, channel_idx=OTHER_CHANNEL_IDX)
    task_service.close(make_task(title="closed", owner_id=staff.pk), outcome="", actor="anna")

    assert _titles(task_service.list_tasks("default-europe", owner=staff.pk)) == ["mine", "closed"]
    assert _titles(task_service.list_tasks("default-europe", owner=task_service.NO_OWNER)) == ["nobody's"]
    assert _titles(task_service.list_tasks("default-europe", status="done")) == ["closed"]
    assert _titles(task_service.list_tasks("default-europe", kind="mail")) == ["mine"]
    assert _titles(task_service.list_tasks("default-europe", subject_ref="leads.Company:43")) == ["theirs"]
    assert mine.pk in {task.pk for task in task_service.list_tasks("default-europe", owner=staff.pk, status="open")}


def test_today_counts_and_rows_of_one_owner(frozen_now, staff, other_staff):
    for title, days in [("week-old", -7), ("yesterday", -1), ("now", 0), ("in 3 days", 3), ("in 7 days", 7)]:
        make_task(title=title, owner_id=staff.pk, due_at=NOW + timedelta(days=days))
    make_task(title="in 8 days", owner_id=staff.pk, due_at=NOW + timedelta(days=8))
    make_task(title="no deadline", owner_id=staff.pk)
    make_task(title="someone else's", owner_id=other_staff.pk, due_at=NOW)
    task_service.close(make_task(title="done", owner_id=staff.pk, due_at=NOW), outcome="", actor="anna")

    summary = task_service.today("default-europe", staff, tz=UTC)

    assert (summary.overdue, summary.today, summary.upcoming_7d) == (2, 1, 2)
    assert _titles(summary.rows) == ["week-old", "yesterday", "now"]


def test_today_uses_the_callers_zone(frozen_now, staff):
    make_task(title="Warsaw today", owner_id=staff.pk, due_at=datetime(2026, 11, 13, 14, 0, tzinfo=UTC))
    assert task_service.today("default-europe", staff, tz=WARSAW).today == 1
    assert task_service.today("default-europe", staff, tz=TOKYO).overdue == 1


def test_today_rows_are_capped(monkeypatch, frozen_now, staff):
    monkeypatch.setattr(task_service, "TODAY_ROWS", 2)
    for days in (-3, -2, -1):
        make_task(title=f"{days}", owner_id=staff.pk, due_at=NOW + timedelta(days=days))
    summary = task_service.today("default-europe", staff)
    assert summary.overdue == 3
    assert _titles(summary.rows) == ["-3", "-2"]
