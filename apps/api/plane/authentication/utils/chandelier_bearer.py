# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""API clients signed in with a Chandelier Auth access token (OAuth 2.0 Bearer).

Auth issues short-lived access tokens (5 to 10 minutes) signed with the same keys as the assertion.
A client sends one as ``Authorization: Bearer <token>``. The token is verified like an assertion,
for this candle's audience only. Its ``sub`` must already be a Projects user: this path never creates
accounts (sign-in through the browser does that).

Only in ``required`` mode. In ``dev`` a Bearer header is ignored, so the standalone identity can never
be reached through it.
"""

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from plane.authentication.provider.chandelier import find_user_by_sub, get_guard, is_chandelier_enabled

BEARER = "bearer"


class ChandelierBearerAuthentication(BaseAuthentication):
    def authenticate(self, request):
        if not is_chandelier_enabled():
            return None
        parts = request.META.get("HTTP_AUTHORIZATION", "").split(None, 1)
        if not parts or parts[0].lower() != BEARER:
            return None  # not ours: let the next authentication class look
        token = parts[1].strip() if len(parts) > 1 else ""  # "Bearer" with no token is refused below

        try:
            guard = get_guard()
        except ValueError:
            raise AuthenticationFailed("Invalid token.")
        if guard.cfg.mode != "required":
            return None

        result = guard.check({"Authorization": f"Bearer {token}"}, request.method, request.path)
        claims = result.claims
        # A public path answers ok without claims: a token is required here, so that is a refusal too.
        if not result.ok or not claims or not claims.get("sub"):
            raise AuthenticationFailed("Invalid token.")
        if claims.get("kind", "user") != "user":
            raise AuthenticationFailed("Invalid token.")

        user = find_user_by_sub(str(claims["sub"]))
        if user is None or not user.is_active:
            raise AuthenticationFailed("Invalid token.")
        return (user, claims)

    def authenticate_header(self, request):
        return BEARER
