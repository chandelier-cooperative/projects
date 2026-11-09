# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import uuid

import pytest
from django.core.cache import cache
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from plane.authentication.adapter.error import AUTHENTICATION_ERROR_CODES
from plane.authentication.utils.redirection_path import get_redirection_path
from plane.db.models import Profile, User
from plane.license.models import Instance

DISABLED = str(AUTHENTICATION_ERROR_CODES["SIGN_IN_METHOD_DISABLED"])


@pytest.fixture(autouse=True)
def _reset_auth_throttle_cache():
    cache.delete_pattern("throttle_authentication_*")
    yield
    cache.delete_pattern("throttle_authentication_*")


@pytest.fixture
def instance(db):
    return Instance.objects.create(
        instance_name="Projects",
        instance_id=uuid.uuid4().hex,
        current_version="1.0.0",
        last_checked_at=timezone.now(),
        is_setup_done=True,
    )


@pytest.fixture
def client():
    return Client(HTTP_USER_AGENT="Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/15.0.1")


@pytest.fixture
def chandelier_on(monkeypatch):
    monkeypatch.setenv("CHANDELIER_AUTH_AUDIENCE", "projects.chandelier.test")
    monkeypatch.delenv("CHANDELIER_AUTH_MODE", raising=False)


@pytest.fixture
def chandelier_off(monkeypatch):
    monkeypatch.delenv("CHANDELIER_AUTH_AUDIENCE", raising=False)
    monkeypatch.delenv("CHANDELIER_AUTH_MODE", raising=False)


REDIRECT_FLOW = [
    ("sign-in", "post"),
    ("sign-up", "post"),
    ("magic-sign-in", "post"),
    ("magic-sign-up", "post"),
    ("google-initiate", "get"),
    ("github-initiate", "get"),
    ("gitlab-initiate", "get"),
    ("gitea-initiate", "get"),
]


@pytest.mark.contract
class TestWhileChandelierIsActive:
    """Inside Chandelier no other way in exists."""

    @pytest.mark.django_db
    @pytest.mark.parametrize("name,method", REDIRECT_FLOW)
    def test_redirect_flow_views_refuse(self, client, instance, chandelier_on, name, method):
        response = getattr(client, method)(reverse(name), {"email": "a@example.com", "password": "x"}, follow=False)
        assert response.status_code == 302
        assert f"error_code={DISABLED}" in response.url

    @pytest.mark.django_db
    @pytest.mark.parametrize("name", ["email-check", "magic-generate", "forgot-password", "set-password"])
    def test_json_views_answer_403(self, client, instance, chandelier_on, name):
        response = client.post(reverse(name), {"email": "a@example.com"})
        assert response.status_code == 403
        assert str(response.json()["error_code"]) == DISABLED

    @pytest.mark.django_db
    def test_admin_password_sign_in_refuses(self, client, instance, chandelier_on):
        response = client.post(reverse("instance-admin-sign-in"), {"email": "a@example.com", "password": "x"})
        assert response.status_code == 302
        assert f"error_code={DISABLED}" in response.url

    @pytest.mark.django_db
    def test_no_onboarding_or_workspace_creation_redirect(self, chandelier_on):
        user = User.objects.create(email="p@example.com", username=uuid.uuid4().hex)
        assert get_redirection_path(user) == ""


@pytest.mark.contract
class TestWhileChandelierIsOff:
    """Running the project on its own keeps the usual sign-in."""

    @pytest.mark.django_db
    @pytest.mark.parametrize("name,method", [("sign-in", "post"), ("magic-sign-in", "post"), ("sign-up", "post")])
    def test_views_run(self, client, instance, chandelier_off, name, method):
        response = getattr(client, method)(reverse(name), {}, follow=False)
        assert DISABLED not in response.url

    @pytest.mark.django_db
    def test_email_check_runs(self, client, instance, chandelier_off):
        response = client.post(reverse("email-check"), {"email": "a@example.com"}, content_type="application/json")
        assert response.status_code != 403

    @pytest.mark.django_db
    def test_new_person_goes_to_onboarding(self, chandelier_off):
        user = User.objects.create(email="n@example.com", username=uuid.uuid4().hex)
        assert get_redirection_path(user) == "onboarding"

    @pytest.mark.django_db
    def test_onboarded_person_without_workspace_creates_one(self, chandelier_off):
        user = User.objects.create(email="o@example.com", username=uuid.uuid4().hex)
        Profile.objects.update_or_create(user=user, defaults={"is_onboarded": True})
        assert get_redirection_path(user) == "create-workspace"
