# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""The GDPR hooks exist (the leads registry needs both) and hold nothing keyed by an address."""

import pytest

from django_todo import gdpr
from tests.conftest import make_task

pytestmark = pytest.mark.django_db


def test_hooks_return_empty_results_and_touch_nothing():
    task = make_task(title="Call jan@example.test", contact_ref="leads.Contact:7")
    assert gdpr.gdpr_export("jan@example.test") == {}
    assert gdpr.gdpr_erase("jan@example.test") == {}
    task.refresh_from_db()
    assert task.title == "Call jan@example.test"
