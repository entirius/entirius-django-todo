# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models


class Kind(models.TextChoices):
    MAIL = "mail", "Mail"
    PHONE = "phone", "Phone"
    LINKEDIN = "linkedin", "LinkedIn"
    MEETING = "meeting", "Meeting"
    TODO = "todo", "To do"


class Status(models.TextChoices):
    OPEN = "open", "Open"
    DONE = "done", "Done"
    CANCELLED = "cancelled", "Cancelled"


class Due(models.TextChoices):
    """Buckets of `due_at` on the caller's local day."""

    OVERDUE = "overdue", "Overdue"
    TODAY = "today", "Today"
    UPCOMING = "upcoming", "Upcoming"
    NONE = "none", "No deadline"
