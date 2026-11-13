# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""The Django admin lists tasks read-only: every write goes through the service."""

import pytest
from django.contrib.auth import get_user_model

from tests.conftest import make_task

pytestmark = pytest.mark.django_db


def test_admin_lists_tasks_and_refuses_writes(client):
    task = make_task()
    client.force_login(get_user_model().objects.create_superuser("root", "root@example.test", "pw"))
    assert client.get("/admin/django_todo/task/").status_code == 200
    assert client.get("/admin/django_todo/task/add/").status_code == 403
    assert client.post(f"/admin/django_todo/task/{task.pk}/change/", {"title": "x"}).status_code == 403
