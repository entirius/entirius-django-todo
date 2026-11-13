# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Admin API URL routing — manual `path()` per Volkanos convention. URL names start with `todo-`."""

from django.urls import path

from django_todo.api.admin.views.task_views import (
    TaskCancelView,
    TaskDetailView,
    TaskDoneView,
    TaskListView,
    TaskReopenView,
    TodayView,
)

urlpatterns = [
    path("tasks/", TaskListView.as_view(), name="todo-tasks-list"),
    path("tasks/<int:pk>/", TaskDetailView.as_view(), name="todo-tasks-detail"),
    path("tasks/<int:pk>/done/", TaskDoneView.as_view(), name="todo-tasks-done"),
    path("tasks/<int:pk>/cancel/", TaskCancelView.as_view(), name="todo-tasks-cancel"),
    path("tasks/<int:pk>/reopen/", TaskReopenView.as_view(), name="todo-tasks-reopen"),
    path("today/", TodayView.as_view(), name="todo-today"),
]
