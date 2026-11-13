# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Shared wiring of the admin views — auth declared explicitly, never inherited from service defaults."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Literal, TypeVar

from django_utils.api.v2_errors import raise_pydantic_as_drf
from pydantic import BaseModel, ValidationError
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAdminUser
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from django_todo.models import Task
from django_todo.services import task_service

SchemaT = TypeVar("SchemaT", bound=BaseModel)

ERROR_RESPONSES = {400: None, 401: None, 403: None, 404: None}
TAGS = ["Todo"]


class Conflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "The task's status does not allow this."
    default_code = "conflict"


class TaskAdminView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]
    access_area = "todo.tasks"

    @staticmethod
    def task(channel_idx: str, pk: int) -> Task:
        try:
            return task_service.get_task(channel_idx, pk)
        except Task.DoesNotExist:
            raise NotFound("Task not found.") from None


def parse(schema: type[SchemaT], data: object, location: Literal["body", "query"] = "body") -> SchemaT:
    """Validate request data; a Pydantic error becomes the v2 400 shape."""
    try:
        return schema.model_validate(data)
    except ValidationError as exc:
        raise_pydantic_as_drf(exc, location)


@contextmanager
def service_errors(field: str) -> Iterator[None]:
    """A refused state change → 409; a refused value (owner, kind) → 400 on `field`."""
    try:
        yield
    except task_service.TaskStateError as exc:
        raise Conflict(str(exc)) from None
    except ValueError as exc:
        raise DRFValidationError({field: [str(exc)]}) from None
