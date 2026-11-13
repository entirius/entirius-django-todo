# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Standalone test settings — Postgres via DATABASE_URL (zeno `make module-test` passes its own), else a neutral CI default."""

from importlib.util import find_spec

import dj_database_url

SECRET_KEY = "not so secret test secret for the todo suite"  # noqa: S105 — test-only
DEBUG = True
ALLOWED_HOSTS = ["*"]
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "django_todo",
]
# Soft dependencies when importable (zeno, `make install`): the reminder and the access declarations are tested.
if find_spec("django_notifications"):
    INSTALLED_APPS += ["django_regional", "django_notifications"]
if find_spec("django_access"):
    INSTALLED_APPS.append("django_access")
MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]
ROOT_URLCONF = "tests.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "django_utils.api.v2_errors.v2_exception_handler",
}
SPECTACULAR_SETTINGS = {"TITLE": "django-todo Admin API v2", "VERSION": "2.0.0", "OAS_VERSION": "3.1.0"}

DATABASES = {"default": dj_database_url.config(default="postgresql://postgres:postgres@localhost:5432/test_todo")}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
TIME_ZONE = "UTC"
