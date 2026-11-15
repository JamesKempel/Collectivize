"""Profile pages: what a viewer may read, the owner's edits and settings,
every limit, and the API that serves and saves them."""

import json
import threading
import urllib.error
import urllib.request
from contextlib import contextmanager
from dataclasses import replace
from http import HTTPStatus

import pytest
from hypothesis import given
from hypothesis import strategies as st

from backend.graph import NotFoundError, PermissionDeniedError, ProfileAccess
from backend.network_api import profile_changes
from backend.objects import (
    PROFILE_SECTIONS,
    DomainRuleError,
    Person,
    RsvpStatus,
    Visibility,
)
from backend.server import ApiError, DiscoverApi, serve
from backend.sessions import COOKIE_NAME, SessionStore

from .conftest import NOW, make_event, make_person


def connect(world, a, b):
    request = world.graph.connections.request(a.id, b.id, NOW)
    world.graph.connections.accept(request.id, b.id)


def update(world, person, **changes):
    return world.graph.profiles.update(person.id, person.id, **changes)


def view(world, person, viewer):
    return world.graph.profiles.view(person.id, viewer.id if viewer else None, NOW)


def published(world, title, days=3):
    ev = world.graph.events
    event = ev.create(make_event(title, days_ahead=days), world.chapter.id, world.alice.id)
    return ev.publish(event.id, world.alice.id, NOW)


# --- editing -------------------------------------------------------------------------


def test_you_can_edit_your_own_profile(world):
    saved = update(
        world, world.alice, display_name="Alice A.", bio="Hello", about="Longer text.",
        top3_title="Top 3 snacks", top3_items=("a", "b", "c"), website="https://alice.example/x",
        color_background="#19A88A", color_outline="#000000",
        profile_sections=("network", "about"), profile_visibility=Visibility.CONNECTIONS,
    )
    stored = world.graph.store.node(world.alice.id, Person)
    assert stored == saved and stored.profile == "Longer text." and stored.bio == "Hello"
    assert stored.profile_sections == ("network", "about")
    assert stored.profile_visibility is Visibility.CONNECTIONS


def test_only_you_can_edit_your_profile(world):
    with pytest.raises(PermissionDeniedError):
        world.graph.profiles.update(world.alice.id, world.bob.id, bio="hacked")


@pytest.mark.parametrize("changes", [
    {"email": "x@example.com"}, {"visibility": Visibility.PUBLIC}, {"verification_level": "other"},
    {"analytics_consent": True}, {"nope": 1},
])
def test_other_fields_cannot_be_edited_this_way(world, changes):
    with pytest.raises(DomainRuleError, match="cannot edit"):
        update(world, world.alice, **changes)


@pytest.mark.parametrize("changes", [
    {"display_name": ""}, {"display_name": "x" * 51}, {"bio": "x" * 121}, {"bio": "two\nlines"},
    {"about": "x" * 1001}, {"top3_title": "x" * 31, "top3_items": ("a", "b", "c")},
    {"top3_title": "Title", "top3_items": ("a", "b")}, {"top3_title": "Title", "top3_items": ("a", "b", " ")},
    {"top3_title": "", "top3_items": ("a", "b", "c")}, {"top3_title": "T", "top3_items": ("a", "b", "x" * 41)},
    {"website": "http://plain.example"}, {"website": "https://nodot"}, {"website": "javascript:alert(1)"},
    {"color_background": "red"}, {"color_outline": "#12345"}, {"color_outline": "#GGGGGG"},
    {"profile_visibility": Visibility.PUBLIC}, {"profile_visibility": Visibility.MEMBERS},
    {"profile_sections": ("about", "about")}, {"profile_sections": ("about", "secrets")},
    {"rsvp_visibility": Visibility.PUBLIC},
    {"bio": 5}, {"hide_connections": "yes"}, {"top3_items": ["a", "b", "c"]}, {"profile_sections": (1, 2)},
])
def test_values_outside_the_limits_are_refused_and_nothing_is_saved(world, changes):
    before = world.graph.store.node(world.alice.id, Person)
    with pytest.raises(DomainRuleError):
        update(world, world.alice, **changes)
    assert world.graph.store.node(world.alice.id, Person) == before


@pytest.mark.parametrize("changes", [
    {"display_name": "x" * 50}, {"bio": "x" * 120}, {"about": "x" * 1000},
    {"top3_title": "x" * 30, "top3_items": ("x" * 40, "b", "c")}, {"website": None},
    {"profile_sections": ()}, {"profile_sections": tuple(reversed(PROFILE_SECTIONS))},
])
def test_values_right_at_the_limits_are_accepted(world, changes):
    assert update(world, world.alice, **changes)


def test_changing_who_sees_your_events_updates_existing_rsvps(world):
    event = published(world, "Bonfire")
    world.graph.rsvps.respond(event.id, world.carol.id, RsvpStatus.GOING, NOW)
    update(world, world.carol, rsvp_visibility=Visibility.PRIVATE, hide_connections=True)
    carol = world.graph.store.node(world.carol.id, Person)
    assert carol.rsvp_visibility is Visibility.PRIVATE and carol.hide_connections
    assert world.graph.rsvps.mine(event.id, world.carol.id).visibility is Visibility.PRIVATE


def test_a_failed_edit_changes_nothing_at_all(world):
    with pytest.raises(DomainRuleError):
        update(world, world.alice, bio="fine", rsvp_visibility=Visibility.PUBLIC)
    assert world.graph.store.node(world.alice.id, Person).bio == ""


@given(st.text(max_size=140), st.text(max_size=8))
def test_any_text_is_either_saved_exactly_or_refused(bio, color):
    person = Person(display_name="Fuzz", provenance=make_person.__globals__["staff_provenance"]())
    try:
        changed = replace(person, bio=bio, color_background=color)
    except DomainRuleError:
        return
    assert changed.bio == bio and len(bio) <= 120 and "\n" not in bio and len(color) == 7


# --- reading -------------------------------------------------------------------------


def test_your_own_profile_is_always_full(world):
    update(world, world.alice, profile_visibility=Visibility.PRIVATE, bio="Mine")
    mine = view(world, world.alice, world.alice)
    assert mine.is_self and mine.access is ProfileAccess.FULL and mine.connection == "self"
    assert [o.id for o in mine.orgs] == [world.chapter.id]


@pytest.mark.parametrize(("level", "stranger", "friend"), [
    (Visibility.NETWORK, ProfileAccess.FULL, ProfileAccess.FULL),
    (Visibility.CONNECTIONS, ProfileAccess.LOCKED, ProfileAccess.FULL),
    (Visibility.PRIVATE, ProfileAccess.LOCKED, ProfileAccess.LOCKED),
])
def test_profile_visibility_decides_full_or_locked(world, level, stranger, friend):
    update(world, world.alice, profile_visibility=level)
    connect(world, world.alice, world.bob)
    assert view(world, world.alice, world.carol).access is stranger
    assert view(world, world.alice, world.bob).access is friend


def test_a_locked_profile_lists_nothing(world):
    published(world, "Bonfire")
    update(world, world.alice, profile_visibility=Visibility.PRIVATE)
    locked = view(world, world.alice, world.bob)
    assert locked.orgs == () and locked.hosting == () and locked.going == ()


def test_connection_state_is_reported_from_the_viewers_side(world):
    request = world.graph.connections.request(world.alice.id, world.bob.id, NOW)
    assert view(world, world.bob, world.alice).connection == "pending_out"
    assert view(world, world.alice, world.bob).connection == "pending_in"
    assert view(world, world.carol, world.alice).connection == "none"
    world.graph.connections.accept(request.id, world.bob.id)
    assert view(world, world.bob, world.alice).connection == "connected"


def test_hidden_and_missing_people_and_orgs_look_the_same(world):
    hidden = make_person(world.graph, "Hidden")
    world.graph.store.save_node(hidden.with_visibility(Visibility.PRIVATE))
    for target in (hidden.id, "nobody", world.chapter.id):
        with pytest.raises(NotFoundError):
            world.graph.profiles.view(target, world.alice.id, NOW)
    with pytest.raises(NotFoundError):
        world.graph.profiles.view(world.alice.id, None, NOW)  # logged out


def test_a_private_membership_never_shows_on_a_profile(world):
    membership = world.graph.membership
    edge = membership.request(world.carol.id, world.chapter.id, NOW)
    membership.confirm(edge.id, world.alice.id)
    assert [o.id for o in view(world, world.carol, world.bob).orgs] == [world.chapter.id]
    membership.set_visibility(edge.id, world.carol.id, Visibility.PRIVATE)
    assert view(world, world.carol, world.bob).orgs == ()
    assert [o.id for o in view(world, world.carol, world.carol).orgs] == [world.chapter.id]


def test_going_follows_who_the_person_lets_see_their_events(world):
    event = published(world, "Bonfire")
    world.graph.rsvps.respond(event.id, world.carol.id, RsvpStatus.GOING, NOW)
    connect(world, world.carol, world.bob)
    dave = make_person(world.graph, "Dave")
    assert [e.id for e in view(world, world.carol, world.bob).going] == [event.id]  # connection
    assert view(world, world.carol, dave).going == ()  # default: connections only
    update(world, world.carol, rsvp_visibility=Visibility.NETWORK)
    assert [e.id for e in view(world, world.carol, dave).going] == [event.id]
    update(world, world.carol, rsvp_visibility=Visibility.PRIVATE)
    assert view(world, world.carol, world.bob).going == ()
    assert [e.id for e in view(world, world.carol, world.carol).going] == [event.id]


def test_only_upcoming_going_events_and_not_maybes(world):
    past = published(world, "Soon over", days=1)
    maybe = published(world, "Maybe", days=2)
    world.graph.rsvps.respond(past.id, world.carol.id, RsvpStatus.GOING, NOW)
    world.graph.rsvps.respond(maybe.id, world.carol.id, RsvpStatus.INTERESTED, NOW)
    later = past.ends_at
    assert world.graph.profiles.view(world.carol.id, world.carol.id, later).going == ()


def test_hosting_lists_a_persons_own_upcoming_events(world):
    ev = world.graph.events
    event = ev.create(make_event("Study jam", days_ahead=2), world.carol.id, world.carol.id)
    ev.create(make_event("Draft", days_ahead=3), world.carol.id, world.carol.id)
    ev.publish(event.id, world.carol.id, NOW)
    assert [e.title for e in view(world, world.carol, world.bob).hosting] == ["Study jam"]


# --- the API -------------------------------------------------------------------------


def api_for(world):
    @contextmanager
    def factory():
        yield world.graph
    return DiscoverApi(factory, clock=lambda: NOW)


FULL_EDIT = {
    "display_name": " Alice A. ", "bio": "Hi", "about": "About me",
    "top3": {"title": "Top 3", "items": ["a", "b", "c"]}, "website": "https://alice.example/x",
    "colors": {"background": "#19a88a", "outline": "#000000"},
    "sections": ["network", "events"], "profile_visibility": "connections",
    "rsvp_visibility": "private", "hide_connections": True,
}


def test_api_saves_a_full_edit_and_returns_the_page(world):
    api = api_for(world)
    profile = api.profile({"viewer": world.alice.id, **FULL_EDIT})["profile"]
    assert profile["name"] == "Alice A." and profile["bio"] == "Hi" and profile["about"] == "About me"
    assert profile["top3"] == {"title": "Top 3", "items": ["a", "b", "c"]}
    assert profile["colors"] == {"background": "#19A88A", "outline": "#000000"}
    assert profile["sections"] == ["network", "events"] and profile["website"] == "https://alice.example/x"
    assert profile["settings"] == {
        "profile_visibility": "connections", "rsvp_visibility": "private", "hide_connections": True,
    }
    assert api.network({"viewer": world.alice.id})["profile"] == profile


def test_api_changes_only_what_is_sent_and_can_clear_things(world):
    api = api_for(world)
    api.profile({"viewer": world.alice.id, **FULL_EDIT})
    profile = api.profile({"viewer": world.alice.id, "top3": None, "website": ""})["profile"]
    assert profile["top3"] is None and profile["website"] is None and profile["bio"] == "Hi"


def test_api_shows_a_locked_profile_without_its_contents(world):
    connect(world, world.alice, world.bob)
    api = api_for(world)
    api.profile({"viewer": world.alice.id, **FULL_EDIT, "profile_visibility": "private"})
    profile = api.network({"viewer": world.bob.id, "center": world.alice.id})["profile"]
    assert profile["access"] == "locked" and profile["name"] == "Alice A."
    assert profile["bio"] == "" and profile["about"] == "" and profile["top3"] is None
    assert profile["website"] is None and profile["orgs"] == [] and "settings" not in profile


@pytest.mark.parametrize("body", [
    {"bio": 5}, {"top3": "x"}, {"top3": {"title": "T", "items": "abc"}}, {"top3": {"title": "T", "items": [1, 2, 3]}},
    {"colors": "red"}, {"colors": {"background": "#000000"}}, {"sections": "about"}, {"sections": [1]},
    {"profile_visibility": "public"}, {"rsvp_visibility": 3}, {"hide_connections": "true"}, {"website": 7},
])
def test_api_rejects_malformed_edits(world, body):
    with pytest.raises(ApiError) as error:
        api_for(world).profile({"viewer": world.alice.id, **body})
    assert error.value.status is HTTPStatus.BAD_REQUEST


def test_api_needs_a_viewer_and_ignores_attempts_to_edit_someone_else(world):
    api = api_for(world)
    with pytest.raises(ApiError):
        api.profile({"bio": "x"})
    api.profile({"viewer": world.bob.id, "person_id": world.alice.id, "bio": "x"})
    assert world.graph.store.node(world.alice.id, Person).bio == ""  # Bob edited Bob


def test_a_background_picture_is_saved_shown_and_cleared(world):
    api = api_for(world)
    profile = api.profile({"viewer": world.alice.id, "background_picture": "ocean"})["profile"]
    assert profile["background_picture"] == "ocean"
    assert world.graph.store.node(world.alice.id, Person).background_picture == "ocean"
    assert api.profile({"viewer": world.alice.id, "bio": "x"})["profile"]["background_picture"] == "ocean"  # kept
    assert api.profile({"viewer": world.alice.id, "background_picture": None})["profile"]["background_picture"] is None


@pytest.mark.parametrize("picture", ["beach", "OCEAN", "../x", 5])
def test_only_the_preset_background_pictures_are_accepted(world, picture):
    api = api_for(world)
    with pytest.raises((ApiError, DomainRuleError)):  # not text: 400 here; not a preset: the record refuses (400 over HTTP)
        api.profile({"viewer": world.alice.id, "background_picture": picture})
    assert world.graph.store.node(world.alice.id, Person).background_picture == ""


def test_people_saved_before_background_pictures_existed_still_load():
    from backend.graph.codec import decode_record, encode_record

    person = Person(display_name="Old", provenance=make_person.__globals__["staff_provenance"]())
    data = encode_record(person)
    del data["background_picture"]
    assert decode_record("Person", data).background_picture == ""


def test_unknown_keys_in_the_body_are_ignored_not_saved(world):
    assert profile_changes({"viewer": "v", "email": "x@example.com", "visibility": "public"}) == {}


def post(url, body, limit=None, token=None):
    data = json.dumps(body, ensure_ascii=False).encode()  # as a browser sends it
    headers = {"Content-Type": "application/json"}
    if token:  # the signed-in session (the server ignores any "viewer" sent)
        headers["Cookie"] = f"{COOKIE_NAME}={token}"
    request = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def test_profile_over_http_with_its_own_size_limit(world):
    if type(world.graph.store).__name__ != "InMemoryGraphStore":
        pytest.skip("one store is enough for the HTTP layer")
    sessions = SessionStore()
    token = sessions.create(world.alice.id)  # signed in as Alice
    srv = serve(api_for(world), port=0, sessions=sessions)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/api/profile"
    try:
        status, data = post(url, {"about": "é" * 1000}, token=token)  # ~2 KB of text
        assert status == 200 and len(data["profile"]["about"]) == 1000
        big = {"about": "😀" * 1000}  # ~4 KB: over the usual limit
        assert post(url, big, token=token)[0] == 200
        assert post(url, {"about": "x" * 9000}, token=token)[0] == 413
        assert post(url, {"about": "hi"})[0] == 401  # signed out
        status, data = post(url, {"bio": "x" * 121}, token=token)
        assert status == 400 and "bio" in data["error"]
    finally:
        srv.shutdown()
        srv.server_close()


def test_saving_an_unchanged_demo_name_keeps_its_role_tag(world):
    world.graph.store.save_node(replace(world.alice, display_name="Alice (demo student)"))
    api = api_for(world)
    profile = api.profile({"viewer": world.alice.id, "display_name": "Alice", "bio": "Hi"})["profile"]
    assert profile["name"] == "Alice" and profile["role"] == "student" and profile["bio"] == "Hi"
    assert world.graph.store.node(world.alice.id, Person).display_name == "Alice (demo student)"
    renamed = api.profile({"viewer": world.alice.id, "display_name": "Ali"})["profile"]
    assert renamed["name"] == "Ali" and renamed["role"] == ""


# --- the Connect button --------------------------------------------------------------


def test_connect_sends_a_request_that_shows_on_both_profiles(world):
    from backend.app_api import AppApi

    @contextmanager
    def factory():
        yield world.graph

    app, api = AppApi(factory, clock=lambda: NOW), api_for(world)

    def page(viewer, other):
        return api.network({"viewer": viewer.id, "center": other.id})["profile"]

    before = page(world.carol, world.bob)
    assert before["id"] == world.bob.id and before["connection"] == "none"  # the button needs the id
    sent = app.connect(world.carol.id, {"person_id": before["id"]})
    assert sent == {"person_id": world.bob.id, "connection": "pending_out"}
    assert page(world.carol, world.bob)["connection"] == "pending_out"  # "Request sent"
    assert page(world.bob, world.carol)["connection"] == "pending_in"  # "Accept connection"
    assert app.connect(world.carol.id, {"person_id": world.bob.id})["connection"] == "pending_out"  # no duplicate
    assert app.connect(world.bob.id, {"person_id": world.carol.id})["connection"] == "connected"  # asking back accepts
    assert page(world.carol, world.bob)["connection"] == "connected"


def test_the_page_script_keeps_the_persons_id_for_the_connect_button():
    from pathlib import Path

    script = (Path(__file__).resolve().parents[2] / "src/frontend/network-data.js").read_text()
    assert "readPerson(profile, raw.center.name, raw.center.id)" in script
