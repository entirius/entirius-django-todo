# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from celery import shared_task
from celery_once import QueueOnce

from django_todo.services import reminder_service
from django_todo.settings import QUEUE_DEFAULT


@shared_task(base=QueueOnce, once={"graceful": True}, name="django_todo.remind_due", queue=QUEUE_DEFAULT)
def remind_due() -> int:
    """Beat entry (host `CELERY_BEAT_SCHEDULE`): `{"task": "django_todo.remind_due", "schedule": 900.0}`."""
    return reminder_service.remind_due()
