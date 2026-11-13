# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from django.apps import AppConfig

TASKS_AREA = "todo.tasks"


class DjangoTodoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_todo"
    label = "django_todo"
    verbose_name = "Todo"
    is_volkanos = True
    # Free text (title, note, outcome) may name people.
    access_areas = [
        {"key": TASKS_AREA, "label": "Tasks for people", "sensitive": ("pii",)},
    ]
    # Every admin view carries its access_area; no route needs a path rule.
    access_route_rules = []
