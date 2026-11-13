# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Request schemas of the todo admin API v2."""

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from django_todo.enums import Due, Kind, Status


class _LocalDayQuery(BaseModel):
    model_config = ConfigDict(extra="ignore")

    tz: str = Field(
        default="UTC", max_length=64, description="IANA time zone of the caller's day.", examples=["Europe/Warsaw"]
    )

    @field_validator("tz")
    @classmethod
    def _known_zone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("Unknown time zone.") from None
        return value

    @property
    def zone(self) -> ZoneInfo:
        return ZoneInfo(self.tz)


class TaskListQuery(_LocalDayQuery):
    owner: str | None = Field(
        default=None, pattern=r"^(me|none|\d+)$", description="`me`, `none` (unowned) or a user id.", examples=["me"]
    )
    status: Status | None = Field(default=None, description="Only this status.", examples=["open"])
    due: Due | None = Field(
        default=None, description="Only this due bucket on the local day of `tz`.", examples=["today"]
    )
    subject_ref: str | None = Field(
        default=None, max_length=128, description="Only tasks about this subject.", examples=["leads.Company:42"]
    )
    kind: Kind | None = Field(default=None, description="Only this kind.", examples=["phone"])


class TodayQuery(_LocalDayQuery):
    pass


class TaskCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_ref: str = Field(
        min_length=1,
        max_length=128,
        description="What the task is about, `<module>.<Model>:<pk>`.",
        examples=["leads.Company:42"],
    )
    subject_label: str = Field(
        default="", max_length=255, description="What the list shows for the subject.", examples=["Example Ltd"]
    )
    contact_ref: str = Field(
        default="", max_length=128, description="A person the task is about.", examples=["leads.Contact:7"]
    )
    kind: Kind = Field(default=Kind.TODO, description="mail, phone, linkedin, meeting or todo.", examples=["phone"])
    title: str = Field(min_length=1, max_length=255, description="What to do.", examples=["Call back about the offer"])
    note: str = Field(default="", description="Details.", examples=["Asked for a call after 3 pm."])
    due_at: AwareDatetime | None = Field(
        default=None, description="Deadline with an offset; null = none.", examples=["2026-11-14T09:00:00+01:00"]
    )
    owner_id: int | None = Field(
        default=None, description="Who does it; omitted = the caller, null = nobody.", examples=[7]
    )


class TaskUpdateRequest(BaseModel):
    """Only the fields sent change."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(default="", min_length=1, max_length=255, description="What to do.", examples=["Call back"])
    note: str = Field(default="", description="Details.", examples=[""])
    due_at: AwareDatetime | None = Field(
        default=None, description="Deadline; a new one is reminded again.", examples=[None]
    )
    kind: Kind = Field(default=Kind.TODO, description="mail, phone, linkedin, meeting or todo.", examples=["mail"])
    owner_id: int | None = Field(default=None, description="Who does it; null = nobody.", examples=[7])


class TaskDoneRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome: str = Field(default="", description="What happened.", examples=["Agreed on a demo next week."])


class TaskCancelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(default="", description="Why it is cancelled; stored as the outcome.", examples=["Duplicate."])
