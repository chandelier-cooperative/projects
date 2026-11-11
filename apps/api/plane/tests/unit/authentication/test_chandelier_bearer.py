# ruff: noqa: E501
# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import base64
import json
import time
import uuid
from types import SimpleNamespace
from unittest import mock

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory

from plane.authentication.provider import chandelier as provider
from plane.authentication.utils.chandelier_bearer import ChandelierBearerAuthentication

AUD = "projects.chandelier.test"
PERSON_SUB = "22222222-2222-4222-8222-222222222222"


def b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


class FakeKeys:
    def __init__(self, key):
        self.key = key

    def get(self, kid):
        if kid != "k1":
            raise ValueError("unknown key")
        return self.key.public_key()


@pytest.fixture
def key(monkeypatch):
    monkeypatch.setenv("CHANDELIER_AUTH_AUDIENCE", AUD)
    monkeypatch.setenv("CHANDELIER_AUTH_MODE", "required")
    provider.reset_guard()
    k = Ed25519PrivateKey.generate()
    provider.get_guard().keys = FakeKeys(k)
    yield k
    provider.reset_guard()


def mint(key, sub=PERSON_SUB, aud=AUD, **claims):
    now = int(time.time())
    c = {"iss": "https://auth.chandelier.network", "sub": sub, "aud": aud, "iat": now, "exp": now + 300, "jti": uuid.uuid4().hex, "kind": "user"}
    c.update(claims)
    signing = f"{b64(json.dumps({'alg': 'EdDSA', 'typ': 'JWT', 'kid': 'k1'}).encode())}.{b64(json.dumps(c).encode())}"
    return f"{signing}.{b64(key.sign(signing.encode()))}"


def request(token=None, path="/api/workspaces/", method="get"):
    factory = APIRequestFactory()
    headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"} if token is not None else {}
    return getattr(factory, method)(path, **headers)


KNOWN_USER = SimpleNamespace(is_active=True)


@pytest.mark.unit
class TestChandelierBearer:
    def test_no_header_is_not_ours(self, key):
        assert ChandelierBearerAuthentication().authenticate(request()) is None

    def test_other_schemes_are_not_ours(self, key):
        req = APIRequestFactory().get("/api/workspaces/", HTTP_AUTHORIZATION="Basic abc")
        assert ChandelierBearerAuthentication().authenticate(req) is None

    def test_inert_without_chandelier(self, key, monkeypatch):
        monkeypatch.delenv("CHANDELIER_AUTH_AUDIENCE")
        assert ChandelierBearerAuthentication().authenticate(request(mint(key))) is None

    def test_dev_mode_ignores_bearer(self, key, monkeypatch):
        monkeypatch.setenv("CHANDELIER_AUTH_MODE", "dev")
        provider.reset_guard()
        provider.get_guard().keys = FakeKeys(key)
        with mock.patch("plane.authentication.utils.chandelier_bearer.find_user_by_sub", return_value=KNOWN_USER):
            assert ChandelierBearerAuthentication().authenticate(request(mint(key))) is None

    def test_valid_access_token_for_known_person(self, key):
        with mock.patch("plane.authentication.utils.chandelier_bearer.find_user_by_sub", return_value=KNOWN_USER) as find:
            user, claims = ChandelierBearerAuthentication().authenticate(request(mint(key)))
        assert user is KNOWN_USER
        assert claims["sub"] == PERSON_SUB
        find.assert_called_once_with(PERSON_SUB)

    def test_unknown_person_is_refused_not_created(self, key):
        with mock.patch("plane.authentication.utils.chandelier_bearer.find_user_by_sub", return_value=None):
            with pytest.raises(AuthenticationFailed):
                ChandelierBearerAuthentication().authenticate(request(mint(key)))

    def test_inactive_person_is_refused(self, key):
        with mock.patch("plane.authentication.utils.chandelier_bearer.find_user_by_sub", return_value=SimpleNamespace(is_active=False)):
            with pytest.raises(AuthenticationFailed):
                ChandelierBearerAuthentication().authenticate(request(mint(key)))

    @pytest.mark.parametrize(
        "token",
        [
            pytest.param(lambda k: mint(k, aud="grafana.chandelier.test"), id="other audience"),
            pytest.param(lambda k: mint(k, kind=""), id="id token (no kind)"),
            pytest.param(lambda k: mint(k, kind="service"), id="service device"),
            pytest.param(lambda k: mint(k, exp=int(time.time()) - 400, iat=int(time.time()) - 700), id="expired"),
            pytest.param(lambda k: "a.b.c", id="garbage"),
            pytest.param(lambda k: "", id="empty bearer"),
        ],
    )
    def test_refuses_what_is_not_a_person_access_token(self, key, token):
        with mock.patch("plane.authentication.utils.chandelier_bearer.find_user_by_sub", return_value=KNOWN_USER):
            with pytest.raises(AuthenticationFailed):
                ChandelierBearerAuthentication().authenticate(request(token(key)))

    def test_public_path_with_bearer_is_still_refused(self, key):
        # /health answers ok to the guard without claims; an API call must not pass on that alone.
        req = request("whatever", path="/health")
        with pytest.raises(AuthenticationFailed):
            ChandelierBearerAuthentication().authenticate(req)

    def test_authenticate_header_is_bearer(self):
        assert ChandelierBearerAuthentication().authenticate_header(request()) == "bearer"


@pytest.mark.unit
@pytest.mark.django_db
class TestBearerOnThePublicApi:
    """End to end through a real view (plane/api sets its own authentication_classes)."""

    URL = "/api/v1/users/me/"

    @pytest.fixture
    def person(self):
        from plane.db.models import Account, User

        user = User.objects.create(email=f"{PERSON_SUB}@chandelier.local", username=uuid.uuid4().hex)
        Account.objects.create(user=user, provider="chandelier", provider_account_id=PERSON_SUB, access_token="", metadata={})
        return user

    def test_access_token_opens_the_api(self, key, person):
        from rest_framework.test import APIClient

        res = APIClient().get(self.URL, HTTP_AUTHORIZATION=f"Bearer {mint(key)}")
        assert res.status_code == 200
        assert res.json()["email"] == person.email

    # The public API answers 403 to a refused request (APIKeyAuthentication has no WWW-Authenticate,
    # and DRF takes that header from the first authenticator). What matters is that it is refused.
    def test_no_token_or_unknown_person_is_refused(self, key, person):
        from rest_framework.test import APIClient

        assert APIClient().get(self.URL).status_code in (401, 403)
        res = APIClient().get(self.URL, HTTP_AUTHORIZATION=f"Bearer {mint(key, sub='33333333-3333-4333-8333-333333333333')}")
        assert res.status_code in (401, 403)

    def test_other_audience_is_refused(self, key, person):
        from rest_framework.test import APIClient

        res = APIClient().get(self.URL, HTTP_AUTHORIZATION=f"Bearer {mint(key, aud='grafana.chandelier.test')}")
        assert res.status_code in (401, 403)
