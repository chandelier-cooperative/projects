# ruff: noqa: E501
"""Run with: python3 -m unittest -v"""

import base64
import json
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from plane.authentication.utils.chandelier_auth import Config, Guard

AUD = "quotes.chandelier.network"


def b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


class Key:
    def __init__(self):
        self.priv = Ed25519PrivateKey.generate()
        self.x = b64(self.priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw))

    def mint(self, alg="EdDSA", kid="k1", **over):
        now = int(time.time())
        c = {
            "iss": "https://auth.chandelier.network",
            "sub": "u-1",
            "aud": AUD,
            "iat": now,
            "exp": now + 60,
            "jti": "j1",
        }
        c.update(over)
        signing = f"{b64(json.dumps({'alg': alg, 'typ': 'JWT', 'kid': kid}).encode())}.{b64(json.dumps(c).encode())}"
        return f"{signing}.{b64(self.priv.sign(signing.encode()))}"


class JWKS:
    def __init__(self, key: Key):
        body = json.dumps(
            {"keys": [{"kty": "OKP", "crv": "Ed25519", "kid": "k1", "use": "sig", "alg": "EdDSA", "x": key.x}]}
        ).encode()

        class H(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                self.send_response(200)
                self.send_header("content-type", "application/json")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass

        self.srv = HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.srv.server_port}/jwks"

    def close(self):
        self.srv.shutdown()
        self.srv.server_close()


class Tests(unittest.TestCase):
    def setUp(self):
        self.key = Key()
        self.jwks = JWKS(self.key)
        self.addCleanup(self.jwks.close)

    def guard(self, **kw):
        return Guard(Config(audience=AUD, jwks_url=self.jwks.url, **kw))

    def test_required(self):
        g = self.guard()
        now = int(time.time())
        ok = g.check({"X-Chandelier-Assertion": self.key.mint()})
        self.assertTrue(ok.ok)
        self.assertEqual(ok.claims["sub"], "u-1")
        bad = {
            "no token": "",
            "wrong audience": self.key.mint(aud="grafana.chandelier.network"),
            "wrong issuer": self.key.mint(iss="https://evil"),
            "expired": self.key.mint(iat=now - 400, exp=now - 300),
            "issued in the future": self.key.mint(iat=now + 3600, exp=now + 3660),
            "lives too long": self.key.mint(exp=now + 7200),
            "alg none": self.key.mint(alg="none"),
            "alg HS256": self.key.mint(alg="HS256"),
            "unknown kid": self.key.mint(kid="nope"),
            "no sub": self.key.mint(sub=""),
            "another key": Key().mint(),
            "garbage": "a.b.c",
        }
        for name, tok in bad.items():
            r = g.check({"X-Chandelier-Assertion": tok} if tok else {})
            self.assertFalse(r.ok, name)
            self.assertEqual(r.status, 401, name)
        # convenience headers alone are worth nothing
        self.assertFalse(g.check({"X-Chandelier-User": "u-1", "Remote-User": "u-1"}).ok)
        # Authorization: Bearer works in required mode
        self.assertTrue(g.check({"Authorization": "Bearer " + self.key.mint()}).ok)

    def test_public_paths_are_exact_and_get_head_only(self):
        g = self.guard()
        at = lambda m, p: g.check({}, m, p).ok  # noqa: E731
        self.assertTrue(at("GET", "/health"))
        self.assertTrue(at("HEAD", "/healthz"))
        self.assertFalse(at("POST", "/health"))
        self.assertFalse(at("GET", "/health/x"))
        self.assertFalse(at("GET", "/healthy"))
        self.assertFalse(at("GET", "/"))

    def test_dev(self):
        with self.assertLogs("chandelier_auth", "WARNING"):
            alone = Guard(Config(mode="dev"))
        d = alone.check({})
        self.assertTrue(d.ok)
        self.assertEqual(d.claims["assurance"], "dev")
        # an assertion that arrives is verified, not ignored: with no audience it cannot be
        self.assertFalse(alone.check({"X-Chandelier-Assertion": "whatever"}).ok)

        with self.assertLogs("chandelier_auth", "WARNING"):
            wired = Guard(Config(mode="dev", audience=AUD, jwks_url=self.jwks.url))
        self.assertFalse(wired.check({"X-Chandelier-Assertion": "a.b.c"}).ok)
        real = wired.check({"X-Chandelier-Assertion": self.key.mint()})
        self.assertTrue(real.ok)
        self.assertEqual(real.claims["sub"], "u-1")
        # Authorization: Bearer is ignored in dev
        self.assertEqual(wired.check({"Authorization": "Bearer x"}).claims["assurance"], "dev")

    def test_misconfiguration_refuses_to_start_instead_of_opening(self):
        with self.assertRaisesRegex(ValueError, "MODE is empty"):
            Guard.from_env({})
        with self.assertRaisesRegex(ValueError, "MODE is empty"):
            Guard.from_env({"CHANDELIER_AUTH_AUDIENCE": AUD})  # audience alone never picks a mode
        with self.assertRaisesRegex(ValueError, "AUDIENCE"):
            Guard.from_env({"CHANDELIER_AUTH_MODE": "required"})
        with self.assertRaisesRegex(ValueError, "required or dev"):
            Guard.from_env({"CHANDELIER_AUTH_MODE": "off"})
        with self.assertLogs("chandelier_auth", "WARNING"):
            Guard.from_env({"CHANDELIER_AUTH_MODE": "dev"})


if __name__ == "__main__":
    unittest.main()
