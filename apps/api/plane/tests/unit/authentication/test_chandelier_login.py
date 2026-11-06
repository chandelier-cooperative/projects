# ruff: noqa: E501
# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import base64
import json
import time
import uuid

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.utils import timezone

from plane.authentication.provider import chandelier as provider
from plane.db.models import Account, User
from plane.license.models import Instance, InstanceAdmin

AUD = "projects.chandelier.test"
ADMIN_SUB = "11111111-1111-4111-8111-111111111111"
PERSON_SUB = "22222222-2222-4222-8222-222222222222"
APP_URL = "/auth/chandelier/"
ADMIN_URL = "/api/instances/admins/chandelier/"


def b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


class FakeKeys:
    """Stands in for the JWKS cache so no Auth is needed."""

    def __init__(self, key):
        self.key = key

    def get(self, kid):
        if kid != "k1":
            raise ValueError("unknown key")
        return self.key.public_key()


@pytest.fixture
def signer(monkeypatch):
    monkeypatch.setenv("CHANDELIER_AUTH_AUDIENCE", AUD)
    monkeypatch.delenv("CHANDELIER_AUTH_MODE", raising=False)
    monkeypatch.setenv("CHANDELIER_ADMIN_SUB", ADMIN_SUB)
    provider.reset_guard()
    key = Ed25519PrivateKey.generate()
    provider.get_guard().keys = FakeKeys(key)

    def mint(sub=PERSON_SUB, aud=AUD, **claims):
        now = int(time.time())
        c = {
            "iss": "https://auth.chandelier.network",
            "sub": sub,
            "aud": aud,
            "iat": now,
            "exp": now + 60,
            "jti": uuid.uuid4().hex,
        }
        c.update(claims)
        signing = (
            f"{b64(json.dumps({'alg': 'EdDSA', 'typ': 'JWT', 'kid': 'k1'}).encode())}.{b64(json.dumps(c).encode())}"
        )
        return f"{signing}.{b64(key.sign(signing.encode()))}"

    yield mint
    provider.reset_guard()


@pytest.fixture
def instance(db):
    return Instance.objects.create(
        instance_name="Projects",
        instance_id=uuid.uuid4().hex,
        current_version="1.0.0",
        last_checked_at=timezone.now(),
        is_setup_done=True,
    )


def get(client, url, token=None, **extra):
    # Plane stores the user agent on login (not null), and real browsers always send one.
    extra.setdefault("HTTP_USER_AGENT", "pytest")
    if token:
        extra["HTTP_X_CHANDELIER_ASSERTION"] = token
    return client.get(url, **extra)


@pytest.mark.unit
class TestChandelierAppLogin:
    def test_disabled_without_configuration_is_404(self, client, instance, monkeypatch):
        monkeypatch.delenv("CHANDELIER_AUTH_AUDIENCE", raising=False)
        monkeypatch.delenv("CHANDELIER_AUTH_MODE", raising=False)
        assert get(client, APP_URL).status_code == 404

    def test_creates_user_from_ext_and_logs_in(self, client, signer, instance):
        res = get(client, APP_URL, signer(ext="Ana@Example.com", name="Ana Lopez Ruiz"))
        assert res.status_code == 302
        assert "error_code" not in res["Location"]
        user = User.objects.get(email="ana@example.com")
        assert (user.first_name, user.last_name) == ("Ana", "Lopez Ruiz")
        assert user.is_password_autoset
        assert Account.objects.filter(user=user, provider="chandelier", provider_account_id=PERSON_SUB).exists()
        assert client.session.get("_auth_user_id") == str(user.id)

    def test_synthetic_email_without_share_ids(self, client, signer, instance):
        get(client, APP_URL, signer())
        assert User.objects.filter(email=f"{PERSON_SUB}@chandelier.local").exists()

    def test_sub_keeps_user_when_ext_changes(self, client, signer, instance):
        get(client, APP_URL, signer(ext="old@example.com"))
        client.logout()
        get(client, APP_URL, signer(ext="new@example.com"))
        assert User.objects.filter(email="old@example.com").count() == 1
        assert not User.objects.filter(email="new@example.com").exists()

    def test_links_existing_user_by_email(self, client, signer, instance):
        existing = User.objects.create(email="ana@example.com", username=uuid.uuid4().hex)
        get(client, APP_URL, signer(ext="ana@example.com"))
        assert User.objects.filter(email="ana@example.com").count() == 1
        assert Account.objects.filter(user=existing, provider="chandelier").exists()

    def test_second_person_cannot_take_a_linked_user(self, client, signer, instance):
        get(client, APP_URL, signer(ext="ana@example.com"))
        client.logout()
        other = "33333333-3333-4333-8333-333333333333"
        res = get(client, APP_URL, signer(sub=other, ext="ana@example.com"))
        assert "error_code" in res["Location"]
        assert not client.session.get("_auth_user_id")

    def test_rejects_other_audience(self, client, signer, instance):
        res = get(client, APP_URL, signer(aud="other.chandelier.network"))
        assert "error_code" in res["Location"]
        assert not User.objects.exists()

    def test_rejects_missing_assertion_and_convenience_headers(self, client, signer, instance):
        res = get(client, APP_URL, HTTP_X_CHANDELIER_USER=PERSON_SUB, HTTP_REMOTE_USER=PERSON_SUB)
        assert "error_code" in res["Location"]
        assert not User.objects.exists()

    def test_rejects_service_tokens(self, client, signer, instance):
        res = get(client, APP_URL, signer(kind="service"))
        assert "error_code" in res["Location"]
        assert not User.objects.exists()

    def test_bearer_token_is_not_accepted(self, client, signer, instance):
        res = get(client, APP_URL, HTTP_AUTHORIZATION=f"Bearer {signer()}")
        assert "error_code" in res["Location"]

    def test_signup_closed_blocks_new_people(self, client, signer, instance, monkeypatch):
        monkeypatch.setenv("ENABLE_SIGNUP", "0")
        res = get(client, APP_URL, signer(ext="ana@example.com"))
        assert "error_code" in res["Location"]
        assert not User.objects.filter(email="ana@example.com").exists()

    def test_deactivated_user_is_rejected(self, client, signer, instance):
        User.objects.create(
            email="ana@example.com", username=uuid.uuid4().hex, is_active=False, last_logout_time=timezone.now()
        )
        res = get(client, APP_URL, signer(ext="ana@example.com"))
        assert "error_code" in res["Location"]
        assert not client.session.get("_auth_user_id")

    def test_next_path_is_honoured(self, client, signer, instance):
        res = get(client, APP_URL + "?next_path=/acme/", signer(ext="ana@example.com"))
        assert res["Location"].endswith("/acme/")


@pytest.mark.unit
class TestChandelierSetup:
    def test_admin_completes_setup_even_with_signup_closed(self, client, signer, instance, monkeypatch):
        monkeypatch.setenv("ENABLE_SIGNUP", "0")
        instance.is_setup_done = False
        instance.save()
        res = get(client, APP_URL, signer(sub=ADMIN_SUB, ext="boss@example.com"))
        assert "error_code" not in res["Location"]
        instance.refresh_from_db()
        assert instance.is_setup_done
        user = User.objects.get(email="boss@example.com")
        assert InstanceAdmin.objects.filter(user=user, instance=instance).exists()

    def test_others_cannot_enter_before_setup(self, client, signer, instance):
        instance.is_setup_done = False
        instance.save()
        res = get(client, APP_URL, signer(ext="ana@example.com"))
        assert "error_code" in res["Location"]
        assert not User.objects.filter(email="ana@example.com").exists()
        instance.refresh_from_db()
        assert not instance.is_setup_done

    def test_admin_endpoint_signs_admin_in_to_god_mode(self, client, signer, instance):
        res = get(client, ADMIN_URL, signer(sub=ADMIN_SUB, ext="boss@example.com"))
        assert res.status_code == 302
        assert "error_code" not in res["Location"]
        assert res["Location"].endswith("general/")
        assert InstanceAdmin.objects.filter(user__email="boss@example.com").exists()

    def test_admin_endpoint_refuses_regular_people_and_creates_nobody(self, client, signer, instance):
        res = get(client, ADMIN_URL, signer(ext="ana@example.com"))
        assert "error_code" in res["Location"]
        assert not User.objects.filter(email="ana@example.com").exists()

    def test_admin_endpoint_lets_existing_instance_admins_in(self, client, signer, instance):
        get(client, APP_URL, signer(ext="ana@example.com"))
        client.logout()
        user = User.objects.get(email="ana@example.com")
        InstanceAdmin.objects.create(user=user, instance=instance)
        res = get(client, ADMIN_URL, signer(ext="ana@example.com"))
        assert "error_code" not in res["Location"]

    def test_admin_endpoint_disabled_is_404(self, client, instance, monkeypatch):
        monkeypatch.delenv("CHANDELIER_AUTH_AUDIENCE", raising=False)
        assert get(client, ADMIN_URL).status_code == 404
