# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from django_todo.models import Task
from django_todo.services import task_service

CHANNEL_IDX = "default-europe"
OTHER_CHANNEL_IDX = "other-channel"


def make_user(username: str, **flags):
    return get_user_model().objects.create_user(username=username, **flags)


@pytest.fixture
def staff(db):
    return make_user("anna", is_staff=True, first_name="Anna", last_name="Nowak")


@pytest.fixture
def other_staff(db):
    return make_user("piotr", is_staff=True)


def api_for(user) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return client


@pytest.fixture
def staff_api(staff) -> APIClient:
    return api_for(staff)


def make_task(**overrides) -> Task:
    fields = {
        "channel_idx": CHANNEL_IDX,
        "subject_ref": "leads.Company:42",
        "subject_label": "Example Ltd",
        "kind": "phone",
        "title": "Call back",
        "created_by": "anna",
        **overrides,
    }
    return task_service.create(**fields)


def api_url(path: str, channel_idx: str = CHANNEL_IDX) -> str:
    return f"/api/todo/v2/admin/{channel_idx}/{path}"
