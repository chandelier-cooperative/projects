# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The people Chandelier Auth knows, read from Projects.

Auth lists them at ``GET /api/v1/users`` to a candle the owner allowed (``directory_read``). The call carries
the signed assertion of the person who is using Projects right now, exactly as Caddy put it on that request:
it lives 60 seconds, so it is forwarded and never stored. Who of Projects may ask (workspace admins) is decided
by the caller, not here.

The browser never talks to Auth. It asks Projects, and Projects asks Auth with the assertion of that request.
"""

import json
import logging
import os
from typing import Optional
from urllib.parse import urlencode, urlsplit

import requests

from plane.authentication.utils.chandelier_auth import ASSERTION_HEADER, DEFAULT_JWKS_URL

logger = logging.getLogger("plane.authentication")

TIMEOUT = 5  # seconds
PATH = "/api/v1/users"


class DirectoryError(Exception):
    """The directory could not be read. ``status`` is what Projects answers: 401, 403 or 502."""

    def __init__(self, status: int):
        super().__init__(f"directory: {status}")
        self.status = status


def auth_base_url() -> str:
    """Auth as the container reaches it (the same host and port the keys come from)."""
    jwks = (os.environ.get("CHANDELIER_AUTH_JWKS_URL") or "").strip() or DEFAULT_JWKS_URL
    parts = urlsplit(jwks)
    return f"{parts.scheme}://{parts.netloc}"


def _get(assertion: str, params: dict) -> dict:
    if not assertion:
        raise DirectoryError(401)
    url = f"{auth_base_url()}{PATH}?{urlencode({k: v for k, v in params.items() if v not in (None, '', False)})}"
    try:
        res = requests.get(url, headers={ASSERTION_HEADER: assertion}, timeout=TIMEOUT, allow_redirects=False)
    except requests.RequestException:
        logger.error("Chandelier Auth directory is unreachable")
        raise DirectoryError(502)
    if res.status_code in (401, 403):
        raise DirectoryError(res.status_code)
    if res.status_code != 200:
        logger.error("Chandelier Auth directory answered %s", res.status_code)
        raise DirectoryError(502)
    try:
        body = res.json()
        users = body.get("users")
        if not isinstance(users, list):
            raise ValueError("no users")
    except (ValueError, json.JSONDecodeError, AttributeError):
        logger.error("Chandelier Auth directory answered something unexpected")
        raise DirectoryError(502)
    return body


def _person(u: dict) -> Optional[dict]:
    if not isinstance(u, dict) or not u.get("id"):
        return None
    return {
        "id": str(u["id"]),
        "display_name": str(u.get("display_name") or ""),
        "status": str(u.get("status") or ""),
        "logins": [str(x) for x in (u.get("logins") or []) if isinstance(x, str)],
    }


def list_people(assertion: str, q: str = "", limit: int = 50, cursor: str = "") -> dict:
    """One page of active people: ``{"users": [...], "next_cursor": str | None}``."""
    limit = max(1, min(int(limit or 50), 200))
    body = _get(assertion, {"q": q.strip(), "limit": limit, "cursor": cursor})
    users = [p for p in (_person(u) for u in body["users"]) if p and p["status"] == "active"]
    return {"users": users, "next_cursor": body.get("next_cursor") or None}


def get_active_person(assertion: str, sub: str) -> Optional[dict]:
    """The person with exactly this ``sub`` if Auth knows them and they are active, else None."""
    body = _get(assertion, {"id": sub})
    for u in body["users"]:
        p = _person(u)
        if p and p["id"] == sub and p["status"] == "active":
            return p
    return None
