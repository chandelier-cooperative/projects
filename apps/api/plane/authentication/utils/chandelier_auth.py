# ruff: noqa: E501
"""Chandelier Auth for Python 3.9+.

Needs one dependency, `cryptography` (the standard library cannot verify Ed25519):
    pip install cryptography

Copy this file into your project and wire it once.

FastAPI / Starlette (ASGI):
    from chandelier_auth import Guard, ASGIMiddleware
    app.add_middleware(ASGIMiddleware, guard=Guard.from_env())   # raises if misconfigured
    # in a handler:  request.state.chandelier["sub"]   (the stable id of the person)

Flask / any WSGI app:
    from chandelier_auth import Guard, WSGIMiddleware
    app.wsgi_app = WSGIMiddleware(app.wsgi_app, Guard.from_env())
    # in a view:  request.environ["chandelier"]["sub"]

Anything else:
    r = guard.check(headers, method, path)      # headers: any mapping, names case-insensitive
    if not r.ok: ...respond r.status ("unauthenticated", no reason)
    r.claims["sub"]

It verifies the signed assertion Caddy forwards in X-Chandelier-Assertion with the public keys
Auth publishes, without calling Auth on each request. Nothing else in the request
(X-Chandelier-User, Remote-User...) is trusted.

CHANDELIER_AUTH_MODE:
  required (default)  every request needs a valid assertion for this service, or gets 401.
  dev                 standalone: no Chandelier, no Auth. A request without an assertion gets a
                      fixed development identity. One that carries an assertion is still
                      verified, so a leftover dev setting cannot let a forged one through.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import threading
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

ISSUER = "https://auth.chandelier.network"
ALGORITHM = "EdDSA"
MAX_LIFETIME = 600  # seconds: nothing Auth signs lives longer
SKEW = 30  # seconds of tolerance on exp and iat
DEFAULT_JWKS_URL = "http://host.docker.internal:7778/.well-known/jwks.json"
ASSERTION_HEADER = "x-chandelier-assertion"

log = logging.getLogger("chandelier_auth")


def _b64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _list(s: str) -> list[str]:
    return [p.strip() for p in s.split(",") if p.strip()]


@dataclass
class Result:
    ok: bool
    claims: Optional[dict] = None
    status: int = 200


@dataclass
class Config:
    mode: str = "required"  # required | dev
    jwks_url: str = DEFAULT_JWKS_URL
    audience: str = ""  # the host of the candle, e.g. quotes.chandelier.network
    # Exact paths that skip the check: the deploy and Caddy call health endpoints without an
    # assertion. They must not return anything private.
    public_paths: list[str] = field(default_factory=lambda: ["/health", "/healthz"])
    dev_user: str = "00000000-0000-4000-8000-000000000001"
    dev_name: str = "Dev local"


class _Keys:
    """JWKS cache: 5 minutes; an unknown kid reloads it at most every 10 seconds."""

    def __init__(self, url: str):
        self.url = url
        self.keys: Optional[dict[str, Ed25519PublicKey]] = None
        self.fetched_at = 0.0
        self.tried_at = 0.0
        self.lock = threading.Lock()

    def get(self, kid: str) -> Ed25519PublicKey:
        with self.lock:
            now = time.monotonic()
            fresh = self.keys is not None and now - self.fetched_at < 300
            if fresh and kid in self.keys:
                return self.keys[kid]
            if self.keys is None or not fresh or now - self.tried_at >= 10:
                self.tried_at = now
                try:
                    self._load()
                except Exception as e:  # noqa: BLE001
                    if self.keys is None:
                        raise ValueError("unknown key") from e
            if self.keys is None or kid not in self.keys:
                raise ValueError("unknown key")
            return self.keys[kid]

    def _load(self) -> None:
        with urllib.request.urlopen(self.url, timeout=5) as res:  # noqa: S310 (operator-set URL)
            if res.status != 200:
                raise ValueError(f"jwks: {res.status}")
            body = json.loads(res.read(64 << 10))
        keys: dict[str, Ed25519PublicKey] = {}
        for k in body.get("keys", []):
            if k.get("kty") != "OKP" or k.get("crv") != "Ed25519" or not k.get("kid"):
                continue
            raw = _b64(k["x"])
            if len(raw) == 32:
                keys[k["kid"]] = Ed25519PublicKey.from_public_bytes(raw)
        if not keys:
            raise ValueError("jwks: no usable key")
        self.keys, self.fetched_at = keys, time.monotonic()


class Guard:
    def __init__(self, cfg: Config):
        if cfg.mode not in ("required", "dev"):
            raise ValueError(f"chandelier_auth: CHANDELIER_AUTH_MODE={cfg.mode}: use required or dev")
        if cfg.mode == "required" and not cfg.audience:
            raise ValueError(
                "chandelier_auth: CHANDELIER_AUTH_AUDIENCE is empty (the host of the candle); "
                "to run without Chandelier set CHANDELIER_AUTH_MODE=dev"
            )
        self.cfg = cfg
        self.public = set(cfg.public_paths)
        self.keys = _Keys(cfg.jwks_url)
        if cfg.mode == "dev":
            log.warning(
                'MODE=dev. Requests without an assertion run as "%s". '
                "Never use this where the service is reachable by others.",
                cfg.dev_user,
            )

    @classmethod
    def from_env(cls, env: Mapping[str, str] = os.environ) -> "Guard":
        paths = env.get("CHANDELIER_AUTH_PUBLIC_PATHS")
        cfg = Config(
            mode=(env.get("CHANDELIER_AUTH_MODE") or "").strip().lower() or "required",
            jwks_url=(env.get("CHANDELIER_AUTH_JWKS_URL") or "").strip() or DEFAULT_JWKS_URL,
            audience=(env.get("CHANDELIER_AUTH_AUDIENCE") or "").strip(),
            dev_user=(env.get("CHANDELIER_AUTH_DEV_USER") or "").strip() or Config.dev_user,
            dev_name=(env.get("CHANDELIER_AUTH_DEV_NAME") or "").strip() or Config.dev_name,
        )
        if paths is not None:
            cfg.public_paths = _list(paths)
        return cls(cfg)

    def check(self, headers: Mapping[str, str], method: str = "GET", path: str = "/") -> Result:
        if method in ("GET", "HEAD") and path in self.public:
            return Result(True)
        h = {k.lower(): v for k, v in headers.items()}
        token = h.get(ASSERTION_HEADER, "")
        if not token and self.cfg.mode == "required":
            a = h.get("authorization", "")  # service-to-service tokens
            token = a[7:] if a.startswith("Bearer ") else ""
        if not token:
            if self.cfg.mode == "dev":
                return Result(
                    True,
                    {
                        "sub": self.cfg.dev_user,
                        "name": self.cfg.dev_name,
                        "aud": self.cfg.audience,
                        "assurance": "dev",
                        "nivel": "dev",
                        "kind": "user",
                    },
                )
            return Result(False, status=401)
        if not self.cfg.audience:
            return Result(False, status=401)
        try:
            return Result(True, self._verify(token))
        except Exception:  # noqa: BLE001  one answer, no reason
            return Result(False, status=401)

    def _verify(self, token: str) -> dict[str, Any]:
        if not token or len(token) > 8192:
            raise ValueError("malformed")
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("malformed")
        hdr = json.loads(_b64(parts[0]))
        # The algorithm is ours, not the token's: no "none", no downgrade.
        if hdr.get("alg") != ALGORITHM or not hdr.get("kid"):
            raise ValueError("alg/kid")
        sig = _b64(parts[2])
        if len(sig) != 64:
            raise ValueError("signature")
        key = self.keys.get(hdr["kid"])
        try:
            key.verify(sig, f"{parts[0]}.{parts[1]}".encode())
        except InvalidSignature as e:
            raise ValueError("signature") from e
        c = json.loads(_b64(parts[1]))
        now = int(time.time())
        if c.get("iss") != ISSUER or c.get("aud") != self.cfg.audience or not c.get("sub") or not c.get("jti"):
            raise ValueError("claims")
        exp, iat = int(c["exp"]), int(c["iat"])
        if exp + SKEW < now:
            raise ValueError("expired")
        if iat - SKEW > now or exp < iat or exp - iat > MAX_LIFETIME + SKEW:
            raise ValueError("claims")
        return c


class ASGIMiddleware:
    """FastAPI / Starlette. Puts the claims in scope["state"]["chandelier"] (request.state.chandelier)."""

    def __init__(self, app, guard: Guard):
        self.app, self.guard = app, guard

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = {k.decode("latin-1"): v.decode("latin-1") for k, v in scope["headers"]}
        # the key cache does blocking I/O on a miss: keep it off the event loop
        import asyncio

        r = await asyncio.to_thread(self.guard.check, headers, scope["method"], scope["path"])
        if not r.ok:
            await send({"type": "http.response.start", "status": r.status, "headers": [(b"content-type", b"text/plain")]})
            return await send({"type": "http.response.body", "body": b"unauthenticated"})
        scope.setdefault("state", {})["chandelier"] = r.claims
        return await self.app(scope, receive, send)


class WSGIMiddleware:
    """Flask and other WSGI apps. Puts the claims in environ["chandelier"]."""

    def __init__(self, app, guard: Guard):
        self.app, self.guard = app, guard

    def __call__(self, environ, start_response):
        headers = {
            k[5:].replace("_", "-"): v for k, v in environ.items() if k.startswith("HTTP_")
        }
        r = self.guard.check(headers, environ.get("REQUEST_METHOD", "GET"), environ.get("PATH_INFO", "/"))
        if not r.ok:
            start_response("401 Unauthorized", [("Content-Type", "text/plain")])
            return [b"unauthenticated"]
        environ["chandelier"] = r.claims
        return self.app(environ, start_response)
