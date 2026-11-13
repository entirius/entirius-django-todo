# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Response schemas of the todo admin API v2."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserRef(BaseModel):
    id: int = Field(description="User id.", examples=[7])
    username: str = Field(description="Login name.", examples=["anna"])
    name: str = Field(description="Full name; empty when not set.", examples=["Anna Nowak"])


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Task id.", examples=[12])
    subject_ref: str = Field(description="What the task is about.", examples=["leads.Company:42"])
    subject_label: str = Field(description="What the list shows for the subject.", examples=["Example Ltd"])
    contact_ref: str = Field(description="A person the task is about; empty when none.", examples=[""])
    kind: str = Field(description="mail, phone, linkedin, meeting or todo.", examples=["phone"])
    title: str = Field(description="What to do.", examples=["Call back about the offer"])
    note: str = Field(description="Details.", examples=[""])
    due_at: datetime | None = Field(description="Deadline; null = none.", examples=["2026-11-14T08:00:00Z"])
    owner: UserRef | None = Field(description="Who does it; null = nobody.", examples=[None])
    status: str = Field(description="open, done or cancelled.", examples=["open"])
    outcome: str = Field(description="What happened, or why it was cancelled.", examples=[""])
    done_at: datetime | None = Field(description="When it was closed.", examples=[None])
    done_by: str = Field(description="Username of who closed it.", examples=[""])
    created_by: str = Field(description="Username or system actor that created it.", examples=["anna"])
    source: str = Field(description="Machine tag of the creator.", examples=["manual"])
    created: datetime = Field(
        validation_alias="created_at", description="When it was created.", examples=["2026-11-13T08:00:00Z"]
    )

    @field_validator("owner", mode="before")
    @classmethod
    def _user_ref(cls, user: Any) -> Any:
        if user is None or isinstance(user, dict | UserRef):
            return user
        return {"id": user.pk, "username": user.get_username(), "name": user.get_full_name()}


class TaskListResponse(BaseModel):
    count: int = Field(description="Total matching tasks.", examples=[1])
    next: str | None = Field(description="Next page URL.", examples=[None])
    previous: str | None = Field(description="Previous page URL.", examples=[None])
    results: list[TaskResponse] = Field(description="Soonest due first, no deadline last.", examples=[[]])


class TodayResponse(BaseModel):
    overdue: int = Field(description="Open tasks of the caller due before today.", examples=[2])
    today: int = Field(description="Open tasks of the caller due today.", examples=[3])
    upcoming_7d: int = Field(description="Open tasks of the caller due in the next 7 days after today.", examples=[4])
    results: list[TaskResponse] = Field(
        description="The first 50 overdue and today tasks, oldest due first.", examples=[[]]
    )
