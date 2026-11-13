# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""GDPR hooks (art. 15 export, art. 17 erasure), discovered by `django_leads.gdpr.registry`.

The contract is keyed by e-mail address and a task holds none: it points at subjects and contacts through opaque
references. Both hooks return empty results. The module that owns a subject or a contact erases the free text of
its tasks through `task_service.scrub(subject_ref=…, contact_ref=…)` when it erases that person (docs/concept.md).
"""

from typing import Any


def gdpr_export(email: str) -> dict[str, Any]:
    return {}


def gdpr_erase(email: str) -> dict[str, int]:
    return {}
