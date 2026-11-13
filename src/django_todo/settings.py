# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Module settings — host overrides via Django settings of the same name."""

from django.conf import settings

QUEUE_DEFAULT = getattr(settings, "TODO_QUEUE_DEFAULT", "todo_default")

# At most this many due reminders go out per beat run; the rest wait for the next run.
TODO_REMIND_BATCH = getattr(settings, "TODO_REMIND_BATCH", 200)
