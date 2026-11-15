"""The local demo server: the JSON API behind the Discover page, its input
checks and cache, and the HTTP layer (static files, errors, headers).
No real API calls: the conftest fixture blocks the Anthropic client, so AI
search falls back to keywords unless a test passes a fake."""

import json
import threading
import urllib.error
import urllib.request
from contextlib import contextmanager
from http import HTTPStatus
from pathlib import Path

import pytest

from backend.config import DatabaseConfig, Environment
from backend.graph import CollectivizeGraph
from backend.seed import seed_mock_data
from backend.server import (
    PER_PAGE,
    ApiError,
    DiscoverApi,
    demo_graph_factory,
    resolve_static,
    serve,
)
from backend.sessions import COOKIE_NAME, SessionStore

from .conftest import NOW


@pytest.fixture(scope="module")
def seeded():
    graph = CollectivizeGraph()
    result = seed_mock_data(graph, Environment.TEST, NOW)
    return graph, result


def api_for(graph, **kwargs):
    @contextmanager
    def factory():
        yield graph
    return DiscoverApi(factory, clock=lambda: NOW, **kwargs)


@pytest.fixture(scope="module")
def api(seeded):
    return api_for(seeded[0])


# --- personas and tags ---------------------------------------------------------------


def test_personas_list_every_demo_person_with_suggestions_first(api, seeded):
    people = api.personas()["personas"]
    assert len(people) == len(seeded[1].people)
    assert [p["name"] for p in people[:4]] == ["Drew", "Avery", "Casey", "Kai"]
    assert all(p["featured"] for p in people[:4]) and not people[4]["featured"]
    drew = people[0]
    assert drew["description"] == "student · Sigma Chi Pi Chapter"
    assert "[Demo]" not in json.dumps(people) and "@" not in json.dumps(people)


def test_tags_are_listed_by_label(api):
    labels = [t["label"] for t in api.tags()["tags"]]
    assert labels == sorted(labels) and "Robotics" in labels


# --- discover ------------------------------------------------------------------------


def test_discover_ranks_events_for_the_viewer(api, seeded):
    drew = seeded[1].people["drew"]
    data = api.discover({"viewer": drew, "near": "1"})
    first = data["items"][0]
    assert data["total"] >= 1 and data["page"] == 1 and data["per_page"] == PER_PAGE
    assert first["score"] >= data["items"][-1]["score"]
    assert first["distance_km"] is not None
    assert {"title", "starts_at", "host", "reasons", "friends_going", "going_count"} <= set(first)


def test_logged_out_visitors_get_events_without_personal_signals(api):
    data = api.discover({})
    assert data["items"] and all(i["friends_going"] == [] and i["my_rsvp"] is None
                                 for i in data["items"])


def test_without_near_there_are_no_distances(api, seeded):
    data = api.discover({"viewer": seeded[1].people["drew"]})
    assert all(i["distance_km"] is None for i in data["items"])


def test_topic_filter(api):
    data = api.discover({"tag": "robotics"})
    assert data["items"] and all("Robot" in i["title"] or "Robotics" in i["title"]
                                 for i in data["items"])


def test_paging_past_the_end_is_empty_and_page_count_is_right(api):
    data = api.discover({"page": "99"})
    assert data["items"] == [] and data["pages"] == max(1, -(-data["total"] // PER_PAGE))


@pytest.mark.parametrize("params", [
    {"viewer": "not-a-person"}, {"page": "0"}, {"page": "-1"}, {"page": "abc"},
    {"page": "1001"}, {"tag": "not-a-topic"},
])
def test_bad_discover_input_is_rejected(api, params):
    with pytest.raises(ApiError) as error:
        api.discover(params)
    assert error.value.status is HTTPStatus.BAD_REQUEST


def test_an_org_id_is_not_a_viewer(api, seeded):
    with pytest.raises(ApiError):
        api.discover({"viewer": seeded[1].orgs["chapter"]})


# --- search --------------------------------------------------------------------------


def test_search_falls_back_to_keywords_without_ai(api, seeded):
    data = api.search({"viewer": seeded[1].people["drew"], "query": "puzzles", "near": True})
    assert data["used_ai"] is False and data["note"]
    assert data["items"] and data["cached"] is False


class CountingClient:
    """A fake Anthropic client that picks the first event it finds."""

    def __init__(self):
        from types import SimpleNamespace
        self.calls = 0
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        from types import SimpleNamespace
        self.calls += 1
        if self.calls % 2 == 1:
            block = SimpleNamespace(type="tool_use", id=f"t{self.calls}", name="search_events",
                                    input={"keywords": None, "tags": [], "org_name": None,
                                           "within_days": None, "max_distance_km": None,
                                           "limit": 5})
        else:
            block = SimpleNamespace(type="tool_use", id=f"t{self.calls}", name="submit_picks",
                                    input={"goal": "A fun night", "picks": [
                                        {"ref": "e1", "fit": 0.9, "reason": "lively"}]})
        return SimpleNamespace(stop_reason="tool_use", content=[block])


def test_search_uses_the_agent_and_caches_repeat_searches(seeded):
    client = CountingClient()
    graph = CollectivizeGraph(seeded[0].store, agent_client=client)
    api = api_for(graph)
    body = {"viewer": seeded[1].people["drew"], "query": "something fun", "near": False}
    first = api.search(body)
    assert first["used_ai"] and first["goal"] == "A fun night" and len(first["items"]) == 1
    assert [s["text"] for s in first["steps"]] == ["Searched events", "Picked the best matches"]
    again = api.search({**body, "query": "  Something   FUN "})  # same search, tidied
    assert again["cached"] is True and client.calls == 2


@pytest.mark.parametrize("body", [
    {}, {"query": 5}, {"query": ""}, {"query": "   "}, {"query": "x" * 501},
    {"query": "fun", "viewer": 7}, {"query": "fun", "viewer": "nobody"},
])
def test_bad_search_input_is_rejected(api, body):
    with pytest.raises((ApiError, ValueError)):
        api.search(body)


# --- safety --------------------------------------------------------------------------


def test_the_demo_server_refuses_the_production_database(tmp_path):
    config = DatabaseConfig(Environment.PRODUCTION, tmp_path / "production.db")
    with pytest.raises(PermissionError):
        demo_graph_factory(config, use_ai=False)


def test_the_no_ai_factory_never_uses_ai(tmp_path):
    config = DatabaseConfig(Environment.TEST, tmp_path / "test.db")
    factory = demo_graph_factory(config, use_ai=False)
    with factory() as graph:
        seed_mock_data(graph, Environment.TEST, NOW)
    api = DiscoverApi(factory, clock=lambda: NOW)
    assert api.search({"query": "robots"})["used_ai"] is False


@pytest.fixture
def site(tmp_path):
    for folder in ("src/frontend", "public", "app", "data", "src/backend"):
        (tmp_path / folder).mkdir(parents=True)
    (tmp_path / "src/frontend/discover.html").write_text("<html></html>")
    (tmp_path / "src/frontend/.secret").write_text("x")
    (tmp_path / "data/test.db").write_text("db")
    (tmp_path / "src/backend/server.py").write_text("code")
    (tmp_path / "src/frontend/escape").symlink_to(tmp_path / "data")
    return tmp_path


@pytest.mark.parametrize("path", [
    "/data/test.db", "/src/frontend/../../data/test.db", "/src/frontend/%2e%2e/%2e%2e/data/test.db",
    "/src/backend/server.py", "/src/frontend/.secret", "/src/frontend/escape/test.db",
    "/src/frontend/", "/", "/src/frontend/missing.html", "/src/frontend/discover.html%00.db",
    "/%2fetc/passwd", "//etc/passwd",
])
def test_static_files_never_escape_the_allowed_folders(site, path):
    assert resolve_static(path, site) is None


def test_static_files_inside_the_allowed_folders_are_served(site):
    assert resolve_static("/src/frontend/discover.html", site) == (
        site / "src/frontend/discover.html"
    ).resolve()


# --- over HTTP -----------------------------------------------------------------------


SESSIONS = SessionStore()


@pytest.fixture(scope="module")
def server(api, seeded):
    srv = serve(api, port=0, sessions=SESSIONS)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    signed_in["token"] = SESSIONS.create(seeded[1].people["drew"])
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


signed_in: dict[str, str] = {}


def fetch(url, data=None, headers=None, *, token=None):
    """Requests are signed in as Drew unless `token` says otherwise ("" = signed out)."""
    headers = dict(headers or {})
    token = signed_in.get("token", "") if token is None else token
    if token:
        headers["Cookie"] = f"{COOKIE_NAME}={token}"
    request = urllib.request.Request(url, data=data, headers=headers)
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(request) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers), error.read()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def test_api_over_http_with_safe_headers(server):
    status, headers, body = fetch(f"{server}/api/discover?page=1")
    assert status == 200 and json.loads(body)["page"] == 1
    assert headers["Content-Type"].startswith("application/json")
    assert headers["Cache-Control"] == "no-store"
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert "Python" not in headers.get("Server", "")


def test_search_over_http(server):
    status, _, body = fetch(f"{server}/api/search", json.dumps({"query": "robots"}).encode(),
                            {"Content-Type": "application/json"})
    assert status == 200 and "items" in json.loads(body)


@pytest.mark.parametrize(("data", "headers", "expected"), [
    (b'{"query": "x"}', {"Content-Type": "text/plain"}, 415),
    (b"not json", {"Content-Type": "application/json"}, 400),
    (b"[1, 2]", {"Content-Type": "application/json"}, 400),
    (b"x" * 5000, {"Content-Type": "application/json"}, 413),
])
def test_bad_requests_get_clear_json_errors(server, data, headers, expected):
    status, _, body = fetch(f"{server}/api/search", data, headers)
    assert status == expected and "error" in json.loads(body)


def test_unknown_routes_and_a_viewer_parameter_is_ignored(server):
    assert fetch(f"{server}/api/nope")[0] == 404
    status, _, body = fetch(f"{server}/api/discover?viewer=ghost")  # the session decides
    assert status == 200 and "items" in json.loads(body)


def test_home_redirects_to_sign_in_or_discover(server):
    status, _, body = fetch(f"{server}/", token="")
    assert status == 200 and b'id="signin"' in body  # signed out: the sign-in screen
    status, headers, _ = fetch(f"{server}/")
    assert status == 302 and headers["Location"] == "/discover"


def test_the_real_discover_page_is_served(server):
    status, headers, body = fetch(f"{server}/discover")
    assert status == 200 and headers["Content-Type"].startswith("text/html")
    assert b'id="search-input"' in body
    assert fetch(f"{server}/data/test.db")[0] == 404


def test_server_errors_do_not_leak_details(seeded):
    class Broken(DiscoverApi):
        def tags(self):
            raise RuntimeError("secret internal detail at /Users/x/db")
    @contextmanager
    def factory():
        yield seeded[0]
    sessions = SessionStore()
    token = sessions.create(seeded[1].people["drew"])
    srv = serve(Broken(factory), port=0, sessions=sessions)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        status, _, body = fetch(f"http://127.0.0.1:{srv.server_address[1]}/api/tags", token=token)
    finally:
        srv.shutdown()
        srv.server_close()
    assert status == 500 and json.loads(body) == {"error": "something went wrong"}


def test_the_server_only_listens_on_this_machine(api):
    srv = serve(api, port=0)
    try:
        assert srv.server_address[0] == "127.0.0.1"
    finally:
        srv.server_close()


FRONTEND = Path(__file__).resolve().parents[2] / "src/frontend"


# nav.js builds its own fixed icons with innerHTML; no server text goes there.
@pytest.mark.parametrize("name", sorted(p.name for p in FRONTEND.glob("*.js") if p.name != "nav.js"))
def test_frontend_never_renders_server_text_as_html(name):
    script = (Path(__file__).resolve().parents[2] / "src/frontend" / name).read_text()
    for risky in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval("):
        assert risky not in script


def test_network_map_over_http(server, seeded):
    status, _, body = fetch(f"{server}/api/network")  # signed in as Drew
    assert status == 200 and json.loads(body)["is_self"] is True
    assert fetch(f"{server}/api/network", token="")[0] == 401  # signed out
    assert fetch(f"{server}/api/network?center=nobody")[0] == 404
    status, _, body = fetch(f"{server}/network")
    assert status == 200 and b'id="nw-root"' in body


def test_a_browser_that_stops_waiting_is_not_reported_as_a_failure(seeded, caplog):
    class Gone(DiscoverApi):
        def tags(self):
            raise BrokenPipeError(32, "Broken pipe")  # what a closed connection raises on send
    @contextmanager
    def factory():
        yield seeded[0]
    sessions = SessionStore()
    token = sessions.create(seeded[1].people["drew"])
    srv = serve(Gone(factory), port=0, sessions=sessions)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    signed_in_as_drew = {"Cookie": f"{COOKIE_NAME}={token}"}
    try:
        with caplog.at_level("INFO", logger="backend.server"), pytest.raises(OSError):
            # The server just hangs up (a 500 would be an HTTPError, also an
            # OSError, so the log check below is what tells the two apart).
            urllib.request.urlopen(urllib.request.Request(f"{base}/api/tags", headers=signed_in_as_drew))
        assert fetch(f"{base}/api/discover", token=token)[0] == 200  # and keeps serving
    finally:
        srv.shutdown()
        srv.server_close()
    assert "API request failed" not in caplog.text and "client left" in caplog.text


def test_find_over_http(server, seeded):
    # The unified search (people, orgs and events in one ranked list).
    status, _, body = fetch(f"{server}/api/find?q=al")
    data = json.loads(body)
    assert status == 200 and {"items", "total", "page", "pages", "counts"} <= set(data)
    assert data["page"] == 1 and len(data["items"]) <= data["total"]
    assert fetch(f"{server}/api/find?q=al", token="")[0] == 401  # signed out
    status, _, body = fetch(f"{server}/api/find?q=al&page=zero")
    assert status == 400 and "page" in json.loads(body)["error"]
