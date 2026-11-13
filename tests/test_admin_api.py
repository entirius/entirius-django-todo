# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Admin API: create, list filters, today, edit, done / cancel / reopen, auth and errors."""

import pytest
from django.utils import timezone

from django_todo.enums import Status
from django_todo.models import Task
from django_todo.signals import task_closed
from tests.conftest import OTHER_CHANNEL_IDX, api_for, api_url, make_task, make_user

pytestmark = pytest.mark.django_db
CREATE = {"subject_ref": "leads.Company:42", "subject_label": "Example Ltd", "kind": "phone", "title": "Call back"}


def _now_iso() -> str:
    return timezone.now().isoformat()


def test_created_task_shows_in_today_for_its_owner_only(staff_api, other_staff):
    created = staff_api.post(api_url("tasks/"), {**CREATE, "due_at": _now_iso()}, format="json")
    assert created.status_code == 201

    mine = staff_api.get(api_url("today/")).json()
    theirs = api_for(other_staff).get(api_url("today/")).json()

    assert mine["today"] == 1
    assert [row["id"] for row in mine["results"]] == [created.json()["id"]]
    assert (theirs["today"], theirs["results"]) == (0, [])


def test_create_defaults_the_owner_to_the_caller_and_returns_the_row(staff_api, staff):
    body = staff_api.post(api_url("tasks/"), {**CREATE, "contact_ref": "leads.Contact:7"}, format="json").json()
    assert body["owner"] == {"id": staff.pk, "username": "anna", "name": "Anna Nowak"}
    assert (body["status"], body["created_by"], body["source"], body["contact_ref"]) == (
        "open",
        "anna",
        "manual",
        "leads.Contact:7",
    )
    assert set(body) == {
        "id", "subject_ref", "subject_label", "contact_ref", "kind", "title", "note", "due_at", "owner", "status",
        "outcome", "done_at", "done_by", "created_by", "source", "created",
    }  # fmt: skip


def test_create_with_null_owner_is_unowned_and_a_bad_owner_is_400(staff_api):
    assert staff_api.post(api_url("tasks/"), {**CREATE, "owner_id": None}, format="json").json()["owner"] is None
    customer = make_user("customer")
    response = staff_api.post(api_url("tasks/"), {**CREATE, "owner_id": customer.pk}, format="json")
    assert response.status_code == 400
    assert response.json()["details"][0]["field"] == "owner_id"


@pytest.mark.parametrize(
    "payload",
    [
        {**CREATE, "kind": "fax"},
        {**CREATE, "title": ""},
        {**CREATE, "due_at": "2026-11-14T09:00:00"},
        {**CREATE, "status": "done"},
        {**CREATE, "dedup_key": "x"},
    ],
)
def test_create_validation(staff_api, payload):
    assert staff_api.post(api_url("tasks/"), payload, format="json").status_code == 400
    assert not Task.objects.exists()


def test_list_owner_filters(staff_api, staff, other_staff):
    make_task(title="mine", owner_id=staff.pk)
    make_task(title="theirs", owner_id=other_staff.pk)
    make_task(title="nobody's")

    def titles(**params):
        return [row["title"] for row in staff_api.get(api_url("tasks/"), params).json()["results"]]

    assert titles(owner="me") == ["mine"]
    assert titles(owner="none") == ["nobody's"]
    assert titles(owner=str(other_staff.pk)) == ["theirs"]
    assert len(titles()) == 3


def test_list_due_and_status_filters_and_pagination(staff_api):
    make_task(title="today", due_at=timezone.now())
    make_task(title="none")
    task = make_task(title="done")
    Task.objects.filter(pk=task.pk).update(status=Status.DONE)

    def titles(**params):
        return [row["title"] for row in staff_api.get(api_url("tasks/"), params).json()["results"]]

    assert titles(due="today", tz="Europe/Warsaw") == ["today"]
    assert titles(due="none", status="open") == ["none"]
    page = staff_api.get(api_url("tasks/"), {"page_size": 2}).json()
    assert (page["count"], len(page["results"])) == (3, 2)
    assert page["next"] is not None


@pytest.mark.parametrize("params", [{"tz": "Mars/Base"}, {"owner": "everyone"}, {"due": "soon"}, {"status": "x"}])
def test_list_rejects_bad_queries(staff_api, params):
    response = staff_api.get(api_url("tasks/"), params)
    assert response.status_code == 400
    assert response.json()["details"][0]["location"] == "query"


def test_patch_changes_whitelisted_fields_only(staff_api, other_staff):
    task = make_task()
    url = api_url(f"tasks/{task.pk}/")
    body = staff_api.patch(url, {"title": "Write", "owner_id": other_staff.pk}, format="json").json()
    assert (body["title"], body["owner"]["id"], body["kind"]) == ("Write", other_staff.pk, "phone")
    assert staff_api.patch(url, {"status": "done"}, format="json").status_code == 400
    assert staff_api.patch(url, {"title": None}, format="json").status_code == 400
    assert Task.objects.get().status == Status.OPEN


def test_done_stores_the_outcome_and_emits_task_closed(staff_api, django_capture_on_commit_callbacks):
    task = make_task()
    closed = []

    def receiver(sender, task, **kwargs):
        closed.append(task.pk)

    task_closed.connect(receiver)
    try:
        with django_capture_on_commit_callbacks(execute=True):
            body = staff_api.post(api_url(f"tasks/{task.pk}/done/"), {"outcome": "Demo booked."}, format="json").json()
    finally:
        task_closed.disconnect(receiver)
    assert (body["status"], body["outcome"], body["done_by"]) == ("done", "Demo booked.", "anna")
    assert body["done_at"] is not None
    assert closed == [task.pk]


def test_done_twice_is_409_then_reopen_and_cancel(staff_api):
    task = make_task()
    assert staff_api.post(api_url(f"tasks/{task.pk}/done/"), {}, format="json").status_code == 200
    again = staff_api.post(api_url(f"tasks/{task.pk}/done/"), {}, format="json")
    assert again.status_code == 409
    assert again.json()["error"] == "CONFLICT"

    assert staff_api.post(api_url(f"tasks/{task.pk}/reopen/")).json()["status"] == "open"
    assert staff_api.post(api_url(f"tasks/{task.pk}/reopen/")).status_code == 409
    cancelled = staff_api.post(api_url(f"tasks/{task.pk}/cancel/"), {"reason": "Duplicate."}, format="json").json()
    assert (cancelled["status"], cancelled["outcome"]) == ("cancelled", "Duplicate.")


def test_no_delete(staff_api):
    task = make_task()
    assert staff_api.delete(api_url(f"tasks/{task.pk}/")).status_code == 405
    assert Task.objects.filter(pk=task.pk).exists()


def test_another_channels_task_is_404(staff_api):
    task = make_task(channel_idx=OTHER_CHANNEL_IDX)
    assert staff_api.get(api_url(f"tasks/{task.pk}/")).status_code == 404
    assert staff_api.post(api_url(f"tasks/{task.pk}/done/"), {}, format="json").status_code == 404


def test_api_requires_a_staff_jwt(client, db):
    assert client.get(api_url("tasks/")).status_code == 401
    customer = api_for(make_user("customer"))
    assert customer.get(api_url("today/")).status_code == 403
    assert customer.post(api_url("tasks/"), CREATE, format="json").status_code == 403
