# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Admin API v2 — tasks of a channel: list, create, detail, edit, done, cancel, reopen, and the caller's day."""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response

from django_todo.api.admin.views._base import ERROR_RESPONSES, TAGS, TaskAdminView, parse, service_errors
from django_todo.models import Task
from django_todo.schemas.requests import (
    TaskCancelRequest,
    TaskCreateRequest,
    TaskDoneRequest,
    TaskListQuery,
    TaskUpdateRequest,
    TodayQuery,
)
from django_todo.schemas.responses import TaskListResponse, TaskResponse, TodayResponse
from django_todo.services import task_service

MANUAL_SOURCE = "manual"
TZ_PARAMETER = OpenApiParameter("tz", str, description="IANA time zone of the caller's day; default UTC.")


class TaskPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


def _owner_filter(value: str | None, request: Request) -> int | str | None:
    """`me` → the caller's id, a digit string → that id, `none` and absent as they are."""
    if value == "me":
        return request.user.pk
    return int(value) if value and value.isdigit() else value


def _task_payload(task: Task, code: int = status.HTTP_200_OK) -> Response:
    return Response(TaskResponse.model_validate(task).model_dump(mode="json"), status=code)


class TaskListView(TaskAdminView):
    @extend_schema(
        tags=TAGS,
        operation_id="todo_tasks_list",
        summary="List tasks of the channel",
        description="Soonest due first, no deadline last; paginated (`page`, `page_size` ≤ 100).",
        parameters=[
            OpenApiParameter("owner", str, description="`me`, `none` (unowned) or a user id."),
            OpenApiParameter("status", str, enum=["open", "done", "cancelled"], description="Only this status."),
            OpenApiParameter(
                "due", str, enum=["overdue", "today", "upcoming", "none"], description="Due bucket on the local day."
            ),
            OpenApiParameter("subject_ref", str, description="Only tasks about this subject."),
            OpenApiParameter("kind", str, enum=["mail", "phone", "linkedin", "meeting", "todo"], description="Kind."),
            TZ_PARAMETER,
            OpenApiParameter("page", int, description="Page number."),
        ],
        responses={200: TaskListResponse, **ERROR_RESPONSES},
    )
    def get(self, request: Request, channel_idx: str) -> Response:
        query = parse(TaskListQuery, request.query_params.dict(), "query")
        owner = _owner_filter(query.owner, request)
        qs = task_service.list_tasks(
            channel_idx, owner=owner, status=query.status, due=query.due, subject_ref=query.subject_ref,
            kind=query.kind, tz=query.zone,
        )  # fmt: skip
        paginator = TaskPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        payload = TaskListResponse(
            count=paginator.page.paginator.count,
            next=paginator.get_next_link(),
            previous=paginator.get_previous_link(),
            results=[TaskResponse.model_validate(task) for task in page],
        )
        return Response(payload.model_dump(mode="json"))

    @extend_schema(
        tags=TAGS,
        operation_id="todo_tasks_create",
        summary="Create a task",
        description="The owner defaults to the caller; `owner_id: null` creates an unowned task.",
        request=TaskCreateRequest,
        responses={201: TaskResponse, **ERROR_RESPONSES},
    )
    def post(self, request: Request, channel_idx: str) -> Response:
        body = parse(TaskCreateRequest, request.data)
        fields = body.model_dump()
        if "owner_id" not in body.model_fields_set:
            fields["owner_id"] = request.user.pk
        with service_errors("owner_id"):
            task = task_service.create(
                channel_idx=channel_idx, created_by=request.user.get_username(), source=MANUAL_SOURCE, **fields
            )
        return _task_payload(task_service.get_task(channel_idx, task.pk), status.HTTP_201_CREATED)


class TaskDetailView(TaskAdminView):
    @extend_schema(
        tags=TAGS,
        operation_id="todo_tasks_retrieve",
        summary="Get one task",
        responses={200: TaskResponse, **ERROR_RESPONSES},
    )
    def get(self, request: Request, channel_idx: str, pk: int) -> Response:
        return _task_payload(self.task(channel_idx, pk))

    @extend_schema(
        tags=TAGS,
        operation_id="todo_tasks_update",
        summary="Edit a task",
        description="Only the fields sent change: title, note, due_at, kind, owner_id. A new due date is reminded again.",
        request=TaskUpdateRequest,
        responses={200: TaskResponse, **ERROR_RESPONSES},
    )
    def patch(self, request: Request, channel_idx: str, pk: int) -> Response:
        updates = parse(TaskUpdateRequest, request.data).model_dump(exclude_unset=True)
        with service_errors("owner_id"):
            task_service.update(self.task(channel_idx, pk), updates)
        return _task_payload(self.task(channel_idx, pk))


class TaskDoneView(TaskAdminView):
    @extend_schema(
        tags=TAGS,
        operation_id="todo_tasks_done",
        summary="Mark a task done with its outcome",
        request=TaskDoneRequest,
        responses={200: TaskResponse, 409: None, **ERROR_RESPONSES},
    )
    def post(self, request: Request, channel_idx: str, pk: int) -> Response:
        body = parse(TaskDoneRequest, request.data or {})
        with service_errors("outcome"):
            task = task_service.close(
                self.task(channel_idx, pk), outcome=body.outcome, actor=request.user.get_username()
            )
        return _task_payload(task)


class TaskCancelView(TaskAdminView):
    @extend_schema(
        tags=TAGS,
        operation_id="todo_tasks_cancel",
        summary="Cancel a task",
        description="There is no delete: a mistake is cancelled.",
        request=TaskCancelRequest,
        responses={200: TaskResponse, 409: None, **ERROR_RESPONSES},
    )
    def post(self, request: Request, channel_idx: str, pk: int) -> Response:
        body = parse(TaskCancelRequest, request.data or {})
        with service_errors("reason"):
            task = task_service.cancel(
                self.task(channel_idx, pk), actor=request.user.get_username(), reason=body.reason
            )
        return _task_payload(task)


class TaskReopenView(TaskAdminView):
    @extend_schema(
        tags=TAGS,
        operation_id="todo_tasks_reopen",
        summary="Reopen a done or cancelled task",
        request=None,
        responses={200: TaskResponse, 409: None, **ERROR_RESPONSES},
    )
    def post(self, request: Request, channel_idx: str, pk: int) -> Response:
        with service_errors("status"):
            task = task_service.reopen(self.task(channel_idx, pk), actor=request.user.get_username())
        return _task_payload(task)


class TodayView(TaskAdminView):
    @extend_schema(
        tags=TAGS,
        operation_id="todo_today",
        summary="The caller's day",
        description="Counts of the caller's open tasks overdue, due today and in the next 7 days, and the first 50 "
        "overdue and today tasks, oldest due first.",
        parameters=[TZ_PARAMETER],
        responses={200: TodayResponse, **ERROR_RESPONSES},
    )
    def get(self, request: Request, channel_idx: str) -> Response:
        query = parse(TodayQuery, request.query_params.dict(), "query")
        summary = task_service.today(channel_idx, request.user, tz=query.zone)
        payload = TodayResponse(
            overdue=summary.overdue,
            today=summary.today,
            upcoming_7d=summary.upcoming_7d,
            results=[TaskResponse.model_validate(task) for task in summary.rows],
        )
        return Response(payload.model_dump(mode="json"))
