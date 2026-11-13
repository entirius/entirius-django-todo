# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings
from django.db import models
from django.db.models import Q
from django_utils.models.base_model import BaseModel

from django_todo.enums import Kind, Status


class Task(BaseModel):
    """Something a person must do, about an opaque subject. Written only by `services.task_service`."""

    channel_idx = models.CharField(max_length=64, db_index=True)
    # `<module>.<Model>:<pk>` of the caller — never parsed here.
    subject_ref = models.CharField(max_length=128, db_index=True)
    subject_label = models.CharField(max_length=255, blank=True, default="")
    contact_ref = models.CharField(max_length=128, blank=True, default="")
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.TODO)
    title = models.CharField(max_length=255)
    note = models.TextField(blank=True, default="")
    due_at = models.DateTimeField(null=True, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    outcome = models.TextField(blank=True, default="")
    done_at = models.DateTimeField(null=True, blank=True)
    done_by = models.CharField(max_length=150, blank=True, default="")
    # A username or a system actor (`rule:…`, `reply`).
    created_by = models.CharField(max_length=150)
    # Machine tag of the creator (`manual`, `leads.reply.interested` …).
    source = models.CharField(max_length=64, blank=True, default="")
    # Null, not "": tasks without a key never meet in the open-task unique constraint.
    dedup_key = models.CharField(max_length=128, null=True, blank=True)  # noqa: DJ001
    reminded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["channel_idx", "status", "owner", "due_at"], name="todo_task_list_idx"),
            models.Index(fields=["channel_idx", "subject_ref"], name="todo_task_subject_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["channel_idx", "dedup_key"],
                condition=Q(status="open", dedup_key__isnull=False),
                name="todo_task_open_dedup_uniq",
            )
        ]

    def __str__(self) -> str:
        return f"[{self.kind}] {self.title}"
