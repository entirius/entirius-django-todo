# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from django.contrib import admin

from django_todo.models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "channel_idx", "kind", "status", "owner", "due_at", "subject_label", "created_at")
    list_filter = ("channel_idx", "status", "kind")
    list_select_related = ("owner",)
    search_fields = ("title", "subject_ref", "subject_label")

    # Read-only: every write goes through task_service (dedup, whitelist, signals).
    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False
