"""v1.1 access: the campus-only sign-in gate (4.10), the platform admin's
read-only view-as (4.9), and org admins managing their own org only."""

import json
import threading
import urllib.error
import urllib.request
from contextlib import contextmanager

import pytest

from backend.app_api import AppApi
from backend.config import Environment
from backend.graph import CollectivizeGraph
from backend.objects.person import AVATARS
from backend.seed import seed_mock_data
from backend.server import DiscoverApi, serve
from backend.sessions import COOKIE_NAME, SessionStore

from .conftest import NOW


@pytest.fixture(scope="module")
def world():
    graph = CollectivizeGraph()
    result = seed_mock_data(graph, Environment.TEST, NOW)

    @contextmanager
    def factory():
        yield graph

    sessions = SessionStore()
    srv = serve(DiscoverApi(factory, clock=lambda: NOW), port=0,
                app=AppApi(factory, clock=lambda: NOW), sessions=sessions)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}", graph, result, sessions
    srv.shutdown()
    srv.server_close()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def call(url, body=None, token=None):
    headers = {"Content-Type": "application/json"} if body is not None else {}
    if token:
        headers["Cookie"] = f"{COOKIE_NAME}={token}"
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.build_opener(_NoRedirect).open(request) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers), error.read()


def sign_in(base, email):
    status, headers, body = call(f"{base}/api/signin", {"email": email})
    assert status == 200, body
    cookie = headers["Set-Cookie"]
    assert "HttpOnly" in cookie and "SameSite=Lax" in cookie
    return cookie.split(";", 1)[0].split("=", 1)[1], json.loads(body)


# --- 4.10 access gate --------------------------------------------------------------


def test_gmail_cannot_sign_in_and_is_told_why(world):
    base = world[0]
    status, headers, body = call(f"{base}/api/signin", {"email": "someone@gmail.com"})
    assert status == 403 and "Set-Cookie" not in headers
    assert "Northeastern email" in json.loads(body)["error"]


def test_a_demo_account_signs_in_by_email(world):
    base, _, result, _ = world
    _, me = sign_in(base, "Drew.Demo@northeastern.edu ")
    assert me["id"] == result.people["drew"] and me["viewing_as"] is None


def test_a_new_northeastern_email_gets_a_new_account(world):
    _, me = sign_in(world[0], "new.student@northeastern.edu")
    assert me["name"] == "New Student" and not me["is_platform_admin"]
    assert me["avatar"] in AVATARS  # a random animal, picked once at sign-up
    _, again = sign_in(world[0], "new.student@northeastern.edu")
    assert again["id"] == me["id"] and again["avatar"] == me["avatar"]


@pytest.mark.parametrize("page", ["discover", "profile", "network", "my-events", "org", "account"])
def test_signed_out_pages_redirect_to_the_landing_page(world, page):
    status, headers, _ = call(f"{world[0]}/{page}")
    assert status == 302
    assert headers["Location"] == f"/?next=%2F{page}"


def test_signed_out_visitors_reach_only_landing_invite_and_assets(world):
    base = world[0]
    for path in ("", "home", "invite", "landing.css", "shared.js"):
        assert call(f"{base}/{path}")[0] == 200, path
    status, _, body = call(f"{base}/api/session")  # the landing page's quiet check
    assert status == 200 and json.loads(body) == {"signed_in": False}
    assert call(f"{base}/api/discover")[0] == 401
    assert call(f"{base}/api/me")[0] == 401
    assert call(f"{base}/api/rsvp", {"event_id": "x", "status": "going"})[0] == 401


def test_signing_out_ends_the_session(world):
    base = world[0]
    token, _ = sign_in(base, "emery.demo@northeastern.edu")
    assert call(f"{base}/api/me", token=token)[0] == 200
    status, headers, _ = call(f"{base}/api/signout", {}, token=token)
    assert status == 200 and "Max-Age=0" in headers["Set-Cookie"]
    assert call(f"{base}/api/me", token=token)[0] == 401


def test_no_on_campus_toggle_or_viewing_as_in_the_pages():
    from pathlib import Path

    frontend = Path(__file__).resolve().parents[2] / "src/frontend"
    for path in frontend.glob("*.html"):
        text = path.read_text()
        if path.name != "admin.html":  # the platform admin's own page
            assert "Viewing as" not in text, path.name
        assert 'id="near"' not in text and "On campus" not in text, path.name
    for path in frontend.glob("*.js"):
        text = path.read_text()
        assert "on campus" not in text.casefold(), path.name
        assert "PersonaPicker" not in text, path.name


# --- 4.9 platform admin ------------------------------------------------------------


def test_admin_page_and_api_are_for_platform_admins_only(world):
    base = world[0]
    student, _ = sign_in(base, "casey.demo@northeastern.edu")  # an org admin, not platform
    status, headers, _ = call(f"{base}/admin", token=student)
    assert status == 302 and headers["Location"] == "/home?admin=1"  # the sign-in screen
    assert call(f"{base}/api/admin/users", token=student)[0] == 403
    assert call(f"{base}/api/admin/view-as", {"person_id": "x"}, token=student)[0] == 403
    admin, me = sign_in(base, "pat.demo@northeastern.edu")
    assert me["is_platform_admin"]
    assert call(f"{base}/admin", token=admin)[0] == 200


def test_view_as_is_read_only_logged_and_exits(world):
    base, _, result, sessions = world
    admin, _ = sign_in(base, "pat.demo@northeastern.edu")
    alice = result.people["alice"]
    status, _, body = call(f"{base}/api/admin/view-as", {"person_id": alice}, token=admin)
    assert status == 200 and json.loads(body)["viewing_as"]["id"] == alice
    assert sessions.audit[-1]["action"] == "start" and sessions.audit[-1]["target"] == alice

    me = json.loads(call(f"{base}/api/me", token=admin)[2])
    assert me["viewing_as"]["id"] == alice and me["is_platform_admin"]
    event = result.events["demo_day"]
    status, _, body = call(f"{base}/api/rsvp", {"event_id": event, "status": "going"}, token=admin)
    assert status == 403 and "Read-only" in json.loads(body)["error"]

    status, _, body = call(f"{base}/api/admin/view-as", {"person_id": None}, token=admin)
    assert status == 200 and json.loads(body)["viewing_as"] is None
    assert sessions.audit[-1]["action"] == "stop"


# --- 4.9 org admins ----------------------------------------------------------------


def test_org_admin_adds_and_removes_members_of_their_own_org_only(world):
    base, graph, result, _ = world
    casey, _ = sign_in(base, "casey.demo@northeastern.edu")  # Robotics Club admin
    robotics, surf = result.orgs["robotics"], result.orgs["surf"]
    emery = result.people["emery"]

    status, _, body = call(f"{base}/api/org/members",
                           {"org_id": robotics, "action": "add", "email": "emery.demo@northeastern.edu"},
                           token=casey)
    assert status == 200, body
    assert graph.membership.is_member(emery, robotics)

    status, _, _ = call(f"{base}/api/org/members",
                        {"org_id": robotics, "action": "remove", "person_id": emery}, token=casey)
    assert status == 200 and not graph.membership.is_member(emery, robotics)

    status, _, _ = call(f"{base}/api/org/members",
                        {"org_id": surf, "action": "remove", "person_id": result.people["bob"]},
                        token=casey)
    assert status == 403 and graph.membership.is_member(result.people["bob"], surf)


def test_org_page_member_list_follows_the_rule(world):
    base, _, result, _ = world
    bob, _ = sign_in(base, "bob.demo@northeastern.edu")  # Surf Club member
    alice, _ = sign_in(base, "alice.demo@northeastern.edu")  # not a member; knows Bob
    surf = result.orgs["surf"]
    as_member = json.loads(call(f"{base}/api/org?id={surf}", token=bob)[2])
    as_other = json.loads(call(f"{base}/api/org?id={surf}", token=alice)[2])
    assert as_member["members_complete"] and len(as_member["members"]) == as_member["member_count"]
    assert as_other["member_count"] == as_member["member_count"]
    assert [m["id"] for m in as_other["members"]] == [result.people["bob"]]
    assert not as_other["can_manage"]


# --- development: serve.py --no-login ------------------------------------------------


@pytest.fixture(scope="module")
def no_login(world):
    _, graph, result, _ = world

    @contextmanager
    def factory():
        yield graph

    srv = serve(DiscoverApi(factory, clock=lambda: NOW), port=0,
                app=AppApi(factory, clock=lambda: NOW), sessions=SessionStore(),
                auto_login_email="alice.demo@northeastern.edu")
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}", result
    srv.shutdown()
    srv.server_close()


def test_no_login_signs_everyone_in_with_a_real_session(no_login):
    base, result = no_login
    status, headers, _ = call(f"{base}/discover")
    assert status == 200  # no redirect to sign-in
    token = headers["Set-Cookie"].split(";", 1)[0].split("=", 1)[1]
    status, headers, body = call(f"{base}/api/me")  # an API call with no cookie works too
    assert status == 200 and json.loads(body)["id"] == result.people["alice"]
    status, headers, body = call(f"{base}/api/me", token=token)  # and the cookie sticks
    assert json.loads(body)["id"] == result.people["alice"] and "Set-Cookie" not in headers


def test_no_login_still_lets_you_switch_accounts(no_login):
    base, result = no_login
    status, _, body = call(f"{base}/api/session")  # the landing page's check stays honest
    assert status == 200 and json.loads(body) == {"signed_in": False}
    token, me = sign_in(base, "carol.demo@northeastern.edu")
    assert me["id"] == result.people["carol"]
    assert json.loads(call(f"{base}/api/me", token=token)[2])["id"] == result.people["carol"]


def test_login_is_on_unless_asked(world):
    base = world[0]
    assert call(f"{base}/discover")[0] == 302
    assert call(f"{base}/api/me")[0] == 401


def test_no_login_refuses_a_non_campus_account(world):
    _, graph, _, _ = world

    @contextmanager
    def factory():
        yield graph

    with pytest.raises(Exception, match="Northeastern"):
        serve(DiscoverApi(factory), port=0, auto_login_email="me@gmail.com")


# --- the sign-in switch (config.LOGIN_REQUIRED, serve.py --login / --no-login) -------


def load_serve_script():
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "scripts" / "serve.py"
    spec = importlib.util.spec_from_file_location("serve_script", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(("flag", "default", "expected"), [
    (None, True, True), (None, False, False),  # no flag: the config decides
    (True, False, True), (False, True, False),  # a flag wins for that run
])
def test_sign_in_follows_the_config_switch_unless_a_flag_overrides_it(flag, default, expected):
    assert load_serve_script().login_is_on(flag, default) is expected


def test_the_config_switch_is_what_serve_uses_by_default():
    from backend import config

    assert load_serve_script().login_is_on(None) is config.LOGIN_REQUIRED
