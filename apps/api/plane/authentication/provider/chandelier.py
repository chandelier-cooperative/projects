# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Sign in with Chandelier Auth.

Chandelier Auth (backed by Tailscale) tells us who the person is through a short-lived signed
assertion that Caddy forwards in ``X-Chandelier-Assertion``. This module verifies it and maps the
person (identified by the stable ``sub`` claim) onto a Projects user. No password is involved.

Configuration (environment, none of it secret):

CHANDELIER_AUTH_AUDIENCE   host of the candle, e.g. projects.chandelier.network. Enables the feature.
CHANDELIER_AUTH_MODE       ``required`` (default) or ``dev`` (local only, never deployed).
CHANDELIER_AUTH_JWKS_URL   where Auth publishes its keys (default reaches Auth from a container).
CHANDELIER_ADMIN_SUB       ``sub`` (comma separated for several) of the people who administer the instance.
"""

# Python imports
import logging
import os
import threading
import uuid
from typing import Optional

# Django imports
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

# Module imports
from plane.authentication.adapter.base import Adapter
from plane.authentication.adapter.error import AUTHENTICATION_ERROR_CODES, AuthenticationException
from plane.authentication.utils.chandelier_auth import ASSERTION_HEADER, Guard
from plane.db.models import Account, Profile, User
from plane.license.models import Instance, InstanceAdmin

logger = logging.getLogger("plane.authentication")

PROVIDER = "chandelier"
SYNTHETIC_EMAIL_DOMAIN = "chandelier.local"

_guard: Optional[Guard] = None
_guard_lock = threading.Lock()


def is_chandelier_enabled() -> bool:
    """The feature is on only when the operator configured it. Off means the endpoints answer 404."""
    mode = (os.environ.get("CHANDELIER_AUTH_MODE") or "").strip().lower()
    return bool((os.environ.get("CHANDELIER_AUTH_AUDIENCE") or "").strip()) or mode == "dev"


def get_guard() -> Guard:
    """Process-wide verifier, so the key cache is shared. Raises ValueError when misconfigured."""
    global _guard
    with _guard_lock:
        if _guard is None:
            _guard = Guard.from_env()
        return _guard


def reset_guard() -> None:
    global _guard
    with _guard_lock:
        _guard = None


def admin_subs() -> set:
    return {s.strip() for s in (os.environ.get("CHANDELIER_ADMIN_SUB") or "").split(",") if s.strip()}


def _failed() -> AuthenticationException:
    # One generic answer for any verification failure: no reason leaks to the caller.
    return AuthenticationException(
        error_code=AUTHENTICATION_ERROR_CODES["AUTHENTICATION_FAILED_SIGN_IN"],
        error_message="AUTHENTICATION_FAILED_SIGN_IN",
    )


def get_claims(request) -> dict:
    """Verify the assertion of this request and return its claims.

    Only the signed assertion is trusted: the convenience identity headers are ignored, and only the
    assertion header is handed to the verifier (never ``Authorization``).
    """
    try:
        guard = get_guard()
    except ValueError:
        logger.error("Chandelier Auth is misconfigured")
        raise _failed()

    headers = {}
    token = request.META.get("HTTP_" + ASSERTION_HEADER.upper().replace("-", "_"))
    if token:
        headers[ASSERTION_HEADER] = token

    result = guard.check(headers, "GET", request.path)
    claims = result.claims
    if not result.ok or not claims or not claims.get("sub"):
        raise _failed()
    # Only people sign in to Projects. A device carrying tags (kind=service) does not.
    if claims.get("kind", "user") != "user":
        raise _failed()
    return claims


def split_name(name: str) -> tuple:
    parts = (name or "").strip().split(None, 1)
    return (parts[0] if parts else "", parts[1] if len(parts) > 1 else "")


def email_for(claims: dict) -> str:
    """``ext`` (the Tailscale account) when the operator enabled ``share-ids``, else a synthetic address."""
    ext = str(claims.get("ext") or "").strip().lower()
    if ext:
        try:
            validate_email(ext)
            return ext
        except ValidationError:
            pass
    return f"{claims['sub']}@{SYNTHETIC_EMAIL_DOMAIN}".lower()


def find_user_by_sub(sub: str) -> Optional[User]:
    account = Account.objects.filter(provider=PROVIDER, provider_account_id=sub).select_related("user").first()
    return account.user if account else None


def is_instance_admin(user: User) -> bool:
    return InstanceAdmin.objects.filter(user=user).exists()


def promote_instance_admin(user: User, instance: Instance) -> None:
    """Make the user an instance admin and mark the instance as set up (replaces the god-mode onboarding)."""
    InstanceAdmin.objects.get_or_create(user=user, instance=instance, defaults={"role": 20})
    if not instance.is_setup_done:
        instance.is_setup_done = True
        if not instance.instance_name:
            instance.instance_name = "Projects"
        instance.save()


class ChandelierProvider(Adapter):
    provider = PROVIDER

    def __init__(self, request, claims, callback=None):
        super().__init__(request=request, provider=PROVIDER, callback=callback)
        self.claims = claims
        self.sub = str(claims["sub"])

    def _resolve_email(self) -> str:
        # The sub is the identity. If this person already has a user, keep that user's email.
        linked = find_user_by_sub(self.sub)
        return linked.email if linked else email_for(self.claims)

    def set_user_data(self):
        first_name, last_name = split_name(self.claims.get("name", ""))
        email = self._resolve_email()
        super().set_user_data(
            {
                "email": email,
                "user": {
                    "provider_id": self.sub,
                    "email": email,
                    "avatar": "",
                    "first_name": first_name,
                    "last_name": last_name,
                    "is_password_autoset": True,
                },
            }
        )

    def provision_user(self) -> User:
        """Create the user (and profile) if there is none yet, skipping the ENABLE_SIGNUP check.

        Used for the instance admins: they must be able to enter even when sign-up is closed.
        """
        email = self.sanitize_email(self.user_data["email"])
        user = User.objects.filter(email=email).first()
        if user:
            return user
        first_name, last_name = split_name(self.claims.get("name", ""))
        user = User(email=email, username=uuid.uuid4().hex, first_name=first_name, last_name=last_name)
        user.set_password(uuid.uuid4().hex)
        user.is_password_autoset = True
        user.is_email_verified = True
        user.save()
        Profile.objects.create(user=user)
        return user

    def link_account(self, user: User) -> None:
        # A user is bound to a single Chandelier person: refuse to attach a second sub.
        conflict = Account.objects.filter(user=user, provider=PROVIDER).exclude(provider_account_id=self.sub).exists()
        if conflict:
            logger.warning("User already linked to another Chandelier identity")
            raise _failed()
        Account.objects.get_or_create(
            provider=PROVIDER,
            provider_account_id=self.sub,
            defaults={"user": user, "access_token": "", "metadata": {}},
        )

    def authenticate(self, provision: bool = False) -> User:
        self.set_user_data()
        email = self.sanitize_email(self.user_data["email"])
        # Refuse before touching anything if this email belongs to a user tied to another person.
        existing = User.objects.filter(email=email).first()
        if (
            existing
            and Account.objects.filter(user=existing, provider=PROVIDER).exclude(provider_account_id=self.sub).exists()
        ):
            logger.warning("Email belongs to a user linked to another Chandelier identity")
            raise _failed()
        if provision:
            self.provision_user()
        user = self.complete_login_or_signup()
        self.link_account(user)
        return user
