"""Account management: a person's own account (settings, sign out
everywhere, deletion) and the platform admin's account tools, over HTTP.
Every admin method must refuse non-admins, validate input, and be logged."""

import json
import threading
import urllib.request
from contextlib import contextmanager

import pytest

from backend.accounts import AccountsApi
from backend.app_api import AppApi
from backend.audit import AuditLog
from backend.config import Environment
from backend.graph import CollectivizeGraph, PermissionDeniedError
from backend.objects import Person
from backend.objects.person import AVATARS
from backend.seed import seed_mock_data
from backend.server import DiscoverApi, serve
from backend.sessions import COOKIE_NAME, SessionStore

from .conftest import NOW
from .test_access import call, sign_in

PAT = "pat.demo@northeastern.edu"
DREW = "drew.demo@northeastern.edu"
CASEY = "casey.demo@northeastern.edu"
ADMIN_POSTS = ["/api/admin/account", "/api/admin/account/create", "/api/admin/admins",
               "/api/admin/account/signout", "/api/admin/account/delete"]


@pytest.fixture
def world(tmp_path):
    graph = CollectivizeGraph()
    result = seed_mock_data(graph, Environment.TEST, NOW)

    @contextmanager
    def factory():
        yield graph

    sessions = SessionStore()
    audit = AuditLog(tmp_path / "admin_audit.log")
    accounts = AccountsApi(factory, sessions, audit=audit, clock=lambda: NOW)
    srv = serve(DiscoverApi(factory, clock=lambda: NOW), port=0,
                app=AppApi(factory, clock=lambda: NOW), sessions=sessions, accounts=accounts)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}", graph, result, sessions, audit
    srv.shutdown()
    srv.server_close()


def post(base, path, body, token):
    status, _, raw = call(f"{base}{path}", body, token=token)
    return status, json.loads(raw)


def get(base, path, token):
    status, _, raw = call(f"{base}{path}", token=token)
    return status, json.loads(raw)


# --- your own account ----------------------------------------------------------------


def test_my_account_shows_my_email_and_settings(world):
    base, _, result, *_ = world
    token, _ = sign_in(base, DREW)
    status, account = get(base, "/api/account", token)
    assert status == 200 and account["id"] == result.people["drew"]
    assert account["email"] == DREW and account["sessions"] == 1
    assert account["settings"]["analytics_consent"] is False
    assert account["settings"]["ai_uses_history"] is True


def test_account_calls_need_a_session(world):
    base = world[0]
    assert call(f"{base}/api/account")[0] == 401
    assert call(f"{base}/api/account/delete", {"confirm": DREW})[0] == 401
    assert call(f"{base}/api/admin/account/delete", {"person_id": "x"})[0] == 401


def test_i_can_change_my_consent_settings_and_nothing_else(world):
    base, graph, result, *_ = world
    token, _ = sign_in(base, DREW)
    status, account = post(base, "/api/account", {"analytics_consent": True}, token)
    assert status == 200 and account["settings"]["analytics_consent"] is True
    assert graph.store.node(result.people["drew"], Person).analytics_consent is True
    for bad in ({"analytics_consent": "yes"}, {"is_platform_admin": True}, {},
                {"analytics_consent": True, "email": "x@northeastern.edu"}):
        assert post(base, "/api/account", bad, token)[0] == 400, bad
    assert not graph.store.node(result.people["drew"], Person).is_platform_admin


def test_sign_out_everywhere_ends_all_my_sessions_only(world):
    base = world[0]
    first, _ = sign_in(base, DREW)
    second, _ = sign_in(base, DREW)
    other, _ = sign_in(base, CASEY)
    status, data = post(base, "/api/account/signout-all", {}, first)
    assert status == 200 and data["sessions_ended"] == 2
    assert get(base, "/api/me", first)[0] == 401 and get(base, "/api/me", second)[0] == 401
    assert get(base, "/api/me", other)[0] == 200


def test_deleting_my_account_needs_my_email_and_erases_everything(world):
    base, graph, result, *_ = world
    drew = result.people["drew"]
    token, _ = sign_in(base, DREW)
    for wrong in (None, "", CASEY, drew):
        assert post(base, "/api/account/delete", {"confirm": wrong}, token)[0] == 400
    assert graph.store.has_node(drew)
    status, data = post(base, "/api/account/delete", {"confirm": " Drew.Demo@northeastern.edu"}, token)
    assert status == 200 and data == {"deleted": True}
    assert not graph.store.has_node(drew) and graph.store.edges_touching(drew) == []
    assert get(base, "/api/me", token)[0] == 401  # the session went with it


def test_the_last_platform_admin_cannot_delete_their_account(world):
    base, graph, result, *_ = world
    token, _ = sign_in(base, PAT)
    status, data = post(base, "/api/account/delete", {"confirm": PAT}, token)
    assert status == 400 and "last platform admin" in data["error"]
    assert graph.store.has_node(result.people["pat"])


# --- platform admins -----------------------------------------------------------------


def test_every_admin_account_call_refuses_non_admins(world):
    base, graph, result, _, audit = world
    drew = result.people["drew"]
    student, _ = sign_in(base, CASEY)  # an org admin, not a platform admin
    assert get(base, f"/api/admin/account?id={drew}", student)[0] == 403
    body = {"person_id": drew, "confirm": DREW, "email": "new@northeastern.edu",
            "is_platform_admin": True, "display_name": "Hacked"}
    for path in ADMIN_POSTS:
        assert post(base, path, body, student)[0] == 403, path
    person = graph.store.node(drew, Person)
    assert person.email == DREW and not person.is_platform_admin
    assert audit.entries() == []


def test_a_student_cannot_make_themselves_an_admin(world):
    base, graph, result, *_ = world
    token, _ = sign_in(base, CASEY)
    casey = result.people["casey"]
    assert post(base, "/api/admin/account", {"person_id": casey, "is_platform_admin": True}, token)[0] == 403
    assert post(base, "/api/admin/admins", {"person_id": casey, "is_admin": True}, token)[0] == 403
    assert post(base, "/api/profile", {"is_platform_admin": True}, token)[0] == 200  # ignored
    assert not graph.store.node(casey, Person).is_platform_admin


def test_admin_reads_and_edits_an_account_and_it_is_logged(world, tmp_path):
    base, graph, result, _, audit = world
    drew = result.people["drew"]
    admin, _ = sign_in(base, PAT)
    status, account = get(base, f"/api/admin/account?id={drew}", admin)
    assert status == 200 and account["email"] == DREW and account["counts"]["connections"] > 0
    status, account = post(base, "/api/admin/account", {
        "person_id": drew, "bio": "Edited by staff", "profile_visibility": "private",
        "rsvp_visibility": "private", "email": "Drew.New@northeastern.edu",
    }, admin)
    assert status == 200, account
    person = graph.store.node(drew, Person)
    assert person.bio == "Edited by staff" and person.email == "drew.new@northeastern.edu"
    assert account["settings"]["profile_visibility"] == "private"
    assert account["settings"]["rsvp_visibility"] == "private"
    entry = audit.entries()[-1]
    assert entry["admin"] == result.people["pat"] and entry["target"] == drew
    assert entry["action"] == "update" and "email" in entry["detail"] and "bio" in entry["detail"]
    logged = (tmp_path / "admin_audit.log").read_text()
    assert "Edited by staff" not in logged and "drew.new" not in logged  # names only, no values
    status, data = get(base, "/api/admin/audit", admin)
    assert data["entries"][0]["action"] == "update"


@pytest.mark.parametrize(("change", "status"), [
    ({"email": "someone@gmail.com"}, 400),
    ({"email": "not an email"}, 400),
    ({"email": CASEY}, 409),  # someone else's
    ({"email": 7}, 400),
    ({"is_platform_admin": True}, 400),  # the owner's tool, not an account field
    ({"analytics_consent": True}, 400),  # consent is the person's alone
    ({"ai_uses_history": False}, 400),
    ({"id": "other"}, 400),
    ({"profile_visibility": "everyone"}, 400),
    ({"display_name": "x" * 500}, 400),
])
def test_admin_edits_are_validated(world, change, status):
    base, graph, result, _, audit = world
    drew = result.people["drew"]
    before = graph.store.node(drew, Person)
    admin, _ = sign_in(base, PAT)
    assert post(base, "/api/admin/account", {"person_id": drew, **change}, admin)[0] == status
    assert graph.store.node(drew, Person) == before and audit.entries() == []


def test_admin_edit_of_a_missing_account_is_404(world):
    base = world[0]
    admin, _ = sign_in(base, PAT)
    assert post(base, "/api/admin/account", {"person_id": "nope", "bio": "x"}, admin)[0] == 404
    assert get(base, "/api/admin/account?id=nope", admin)[0] == 404
    assert get(base, "/api/admin/account", admin)[0] == 400


def test_admin_creates_an_account_once(world):
    base, graph, result, _, audit = world
    admin, _ = sign_in(base, PAT)
    status, account = post(base, "/api/admin/account/create",
                           {"email": "New.Person@northeastern.edu", "display_name": " New Person "}, admin)
    assert status == 200 and account["email"] == "new.person@northeastern.edu"
    assert account["name"] == "New Person" and not account["is_platform_admin"]
    created = graph.store.node(account["id"], Person)
    assert created.provenance.created_by == result.people["pat"]
    assert created.avatar in AVATARS
    assert audit.entries()[-1]["action"] == "create"
    again = post(base, "/api/admin/account/create", {"email": "new.person@northeastern.edu"}, admin)
    assert again[0] == 409
    assert post(base, "/api/admin/account/create", {"email": "a@gmail.com"}, admin)[0] == 400
    assert post(base, "/api/admin/account/create", {"email": "b@northeastern.edu", "display_name": ""}, admin)[0] == 400


def test_admin_role_changes_have_guard_rails(world):
    base, graph, result, _, audit = world
    admin, _ = sign_in(base, PAT)
    pat, drew = result.people["pat"], result.people["drew"]
    status, data = post(base, "/api/admin/admins", {"person_id": pat, "is_admin": False}, admin)
    assert status == 400 and "your own admin role" in data["error"]
    # The role is not an ordinary account field any more.
    assert post(base, "/api/admin/account", {"person_id": drew, "is_platform_admin": True}, admin)[0] == 400
    assert post(base, "/api/admin/admins", {"person_id": drew, "is_admin": True}, admin)[0] == 200
    assert graph.store.node(drew, Person).is_platform_admin
    drew_token, me = sign_in(base, DREW)
    assert me["is_platform_admin"]
    # Removing the role signs the ex-admin out, so no old admin session lingers.
    assert post(base, "/api/admin/admins", {"person_id": drew, "is_admin": False}, admin)[0] == 200
    assert get(base, "/api/me", drew_token)[0] == 401
    assert [e["action"] for e in audit.entries()] == ["make admin", "remove admin"]


def test_admin_signs_someone_out(world):
    base, _, result, _, audit = world
    admin, _ = sign_in(base, PAT)
    token, _ = sign_in(base, DREW)
    status, data = post(base, "/api/admin/account/signout", {"person_id": result.people["drew"]}, admin)
    assert status == 200 and data["sessions_ended"] == 1
    assert get(base, "/api/me", token)[0] == 401 and get(base, "/api/me", admin)[0] == 200
    assert audit.entries()[-1]["action"] == "sign-out"


def test_admin_delete_needs_the_email_and_is_not_for_yourself(world):
    base, graph, result, _, audit = world
    admin, _ = sign_in(base, PAT)
    drew, pat = result.people["drew"], result.people["pat"]
    token, _ = sign_in(base, DREW)
    assert post(base, "/api/admin/account/delete", {"person_id": drew}, admin)[0] == 400
    assert post(base, "/api/admin/account/delete", {"person_id": drew, "confirm": PAT}, admin)[0] == 400
    assert post(base, "/api/admin/account/delete", {"person_id": pat, "confirm": PAT}, admin)[0] == 400
    assert graph.store.has_node(drew) and audit.entries() == []
    status, data = post(base, "/api/admin/account/delete", {"person_id": drew, "confirm": DREW}, admin)
    assert status == 200 and data["deleted"]
    assert not graph.store.has_node(drew) and graph.store.edges_touching(drew) == []
    assert get(base, "/api/me", token)[0] == 401
    assert audit.entries()[-1]["action"] == "delete"


def test_admin_cannot_change_accounts_while_viewing_as_someone(world):
    base, graph, result, *_ = world
    admin, _ = sign_in(base, PAT)
    drew = result.people["drew"]
    assert post(base, "/api/admin/view-as", {"person_id": drew}, admin)[0] == 200
    assert post(base, "/api/admin/account", {"person_id": drew, "bio": "x"}, admin)[0] == 403
    assert post(base, "/api/account/delete", {"confirm": DREW}, admin)[0] == 403
    assert graph.store.has_node(drew)


# --- cross-site requests ---------------------------------------------------------------


def test_a_post_from_another_site_is_refused(world):
    base, graph, result, *_ = world
    token, _ = sign_in(base, DREW)

    def send(origin):
        request = urllib.request.Request(
            f"{base}/api/account/delete", data=json.dumps({"confirm": DREW}).encode(),
            headers={"Content-Type": "application/json", "Origin": origin,
                     "Cookie": f"{COOKIE_NAME}={token}"})
        try:
            with urllib.request.urlopen(request) as response:
                return response.status
        except urllib.error.HTTPError as error:
            return error.code

    assert send("https://evil.example") == 403
    assert graph.store.has_node(result.people["drew"])
    assert send(base) == 200


# --- the graph layer's own check -------------------------------------------------------


def test_only_the_person_or_a_platform_admin_can_edit_a_profile(world):
    _, graph, result, *_ = world
    drew, casey, pat = (result.people[k] for k in ("drew", "casey", "pat"))
    with pytest.raises(PermissionDeniedError):
        graph.profiles.update(drew, casey, bio="nope")
    with pytest.raises(PermissionDeniedError):
        graph.profiles.update(drew, "no-such-person", bio="nope")
    assert graph.profiles.update(drew, pat, bio="by staff").bio == "by staff"
