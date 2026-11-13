# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Signals of django_todo — all sent on commit with `sender=Task` and `task=<Task>`."""

from django.dispatch import Signal

# A new task was created (never for a dedup hit that returned an existing open task).
task_created = Signal()
# A task was closed: `status` is `done` or `cancelled`.
task_closed = Signal()
# A done or cancelled task is open again.
task_reopened = Signal()
