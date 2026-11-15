"""Vercel entry point: the whole demo (pages + JSON API) as one serverless function.

Branch `vercel-demo` only. See VERCEL.md.

Every request is routed here (vercel.json). The real request handler from
backend/server.py answers it, against a copy of the bundled fictional demo
database (demo/collectivize-demo.db) in /tmp. Each function instance gets its
own copy, so changes (RSVPs, profile edits) last only while that instance is
warm, then everything resets to the demo data. That is on purpose.

Public-demo settings: everyone is signed in automatically as the demo account,
no email codes, AI search off (no Anthropic calls). One public demo admin login
at /admin (username "Billy Joe", password in VERCEL.md) signs in as the fictional
platform admin Pat; it only ever sees fake data.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import shutil
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

BUNDLED_DB = ROOT / "demo" / "collectivize-demo.db"
LIVE_DB = Path(os.environ.get("TMPDIR", "/tmp")) / "collectivize" / "demo.db"
DEMO_ACCOUNT = "drew.demo@northeastern.edu"
# The public demo admin. Not a secret: the whole demo is fake data, and these
# are written in VERCEL.md so the team can open the admin side.
DEMO_ADMIN_USERNAME = "Billy Joe"
DEMO_ADMIN_PASSWORD = "collectivize-demo"
DEMO_ADMIN_ACCOUNT = "pat.demo@northeastern.edu"  # seeded platform admin

if not LIVE_DB.exists():
    LIVE_DB.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(BUNDLED_DB, LIVE_DB)
os.environ["COLLECTIVIZE_ENV"] = "test"
os.environ["COLLECTIVIZE_DB_PATH"] = str(LIVE_DB)

from backend.accounts import AccountsApi  # noqa: E402
from backend.admin_auth import AdminAuth, AdminCredential, hash_password  # noqa: E402
from backend.app_api import AppApi  # noqa: E402
from backend.config import load_config  # noqa: E402
from backend.graph.query_understanding import QueryReader  # noqa: E402
from backend.server import DemoServer, DiscoverApi, RequestHandler, demo_graph_factory  # noqa: E402
from backend.sessions import Session, SessionStore  # noqa: E402


class _NoSocketServer(DemoServer):
    """The demo server's state (graphs, sessions, settings) without opening a
    port: Vercel's runtime owns the socket and hands each request to `handler`."""

    def server_bind(self) -> None:
        pass

    def server_activate(self) -> None:
        pass


class _SignedSessionStore(SessionStore):
    """Sessions that work on every function instance.

    Vercel spreads requests over several instances, each with its own memory,
    so a sign-in held in one instance's memory is unknown to the next. Here a
    token is `<person id>.<signature>`: an instance that hasn't seen it checks
    the signature and recreates the session. The key is public (fake data
    only), which is fine: the demo admin's password is public too."""

    KEY = b"collectivize-public-demo"

    def create(
        self, person_id: str, ttl: float | None = None, *, renew: bool = False, login: str = ""
    ) -> str:
        tag = base64.urlsafe_b64encode(login.encode()).decode().rstrip("=")
        token = f"{person_id}.{tag}.{self._sign(person_id, login)}"
        with self._lock:
            self._sessions[hashlib.sha256(token.encode()).hexdigest()] = Session(person_id, login=login)
        return token

    def get(self, token: str | None) -> Session | None:
        session = super().get(token)
        if session is not None or not token or token.count(".") != 2:
            return session
        person_id, tag, signature = token.split(".")
        try:
            login = base64.urlsafe_b64decode(tag + "=" * (-len(tag) % 4)).decode()
        except ValueError:
            return None
        if not hmac.compare_digest(signature, self._sign(person_id, login)):
            return None
        with self._lock:
            session = self._sessions.setdefault(
                hashlib.sha256(token.encode()).hexdigest(), Session(person_id, login=login))
        return session

    def _sign(self, person_id: str, login: str) -> str:
        message = f"{person_id}|{login}".encode()
        return hmac.new(self.KEY, message, hashlib.sha256).hexdigest()[:32]


_graphs = demo_graph_factory(load_config(), use_ai=False)
_sessions = _SignedSessionStore()
_admin = AdminCredential(username=DEMO_ADMIN_USERNAME, email=DEMO_ADMIN_ACCOUNT,
                         password_hash=hash_password(DEMO_ADMIN_PASSWORD), role="owner")
DEMO = _NoSocketServer(
    ("127.0.0.1", 0),
    DiscoverApi(_graphs),
    app=AppApi(_graphs, reader=QueryReader(None)),
    sessions=_sessions,
    accounts=AccountsApi(_graphs, _sessions),
    admin_auth=AdminAuth((_admin,)),  # the one public demo admin, see VERCEL.md
    verifier=None,  # no email codes
    auto_login_email=DEMO_ACCOUNT,
)


class handler(RequestHandler):  # noqa: N801 (Vercel looks for this name)
    def __init__(self, request, client_address, server) -> None:  # type: ignore[no-untyped-def]
        super().__init__(request, client_address, DEMO)

    def _session(self, *, auto: bool = True):  # type: ignore[no-untyped-def]
        """Always sign the demo account in, even for the quiet /api/session check.

        Sign-ins live in one instance's memory, and Vercel spreads requests over
        several instances. Without this, an open page's 8-second check that lands
        on another instance hears "signed out" and bounces the visitor to the
        sign-in screen, which auto-signs them in again and drops them on Discover.
        Everyone is the demo account here, so there is no account to switch to."""
        return super()._session(auto=True)

    def parse_request(self) -> bool:
        """vercel.json rewrites every address to /api/index?__path=<original>;
        put the original address back before the app routes it."""
        ok = super().parse_request()
        if ok:
            url = urlsplit(self.path)
            params = parse_qsl(url.query, keep_blank_values=True)
            original = [v for k, v in params if k == "__path"]
            if original:
                rest = urlencode([(k, v) for k, v in params if k != "__path"])
                self.path = "/" + original[0].lstrip("/") + ("?" + rest if rest else "")
        return ok
