"""Finding people, organizations and events by name. Search never shows
more than browsing would: the same visibility rules apply to every kind."""

from contextlib import contextmanager
from dataclasses import replace
from http import HTTPStatus

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from backend.config import Environment
from backend.graph import CollectivizeGraph
from backend.graph.directory import MAX_LIMIT, searchable_name
from backend.objects import DomainRuleError, OrgKind, Person, Visibility
from backend.seed import seed_mock_data
from backend.server import ApiError, DiscoverApi

from .conftest import NOW, make_event, make_org, make_person


def find(world, viewer, text, **kwargs):
    return world.graph.directory.find(viewer.id if viewer else None, text, NOW, **kwargs)


def people(found):
    return [f.person.display_name for f in found.people]


def connect(world, a, b):
    request = world.graph.connections.request(a.id, b.id, NOW)
    world.graph.connections.accept(request.id, b.id)


def publish(world, title, **extra):
    ev = world.graph.events
    event = ev.create(replace(make_event(title), **extra), world.chapter.id, world.alice.id)
    return ev.publish(event.id, world.alice.id, NOW)


# --- people --------------------------------------------------------------------------


def test_people_are_found_by_any_part_of_their_name_whatever_the_case(world):
    ben = make_person(world.graph, "Ben Okafor")
    make_person(world.graph, "Reuben Stone")
    assert people(find(world, world.alice, "BEN")) == ["Ben Okafor", "Reuben Stone"]  # starts-with first
    assert people(find(world, world.alice, "okafor ben")) == ["Ben Okafor"]  # every word must match
    assert find(world, world.alice, "ben").people[0].person.id == ben.id
    assert people(find(world, world.alice, "zzz")) == []


def test_your_connections_come_first_and_are_marked(world):
    make_person(world.graph, "Ben Adams")
    friend = make_person(world.graph, "Ben Zed")
    connect(world, world.alice, friend)
    found = find(world, world.alice, "ben")
    assert people(found) == ["Ben Zed", "Ben Adams"]
    assert [f.connected for f in found.people] == [True, False]


def test_you_do_not_find_yourself(world):
    assert people(find(world, world.alice, "alice")) == []


def test_logged_out_visitors_find_no_people(world):
    found = find(world, None, "alice")
    assert found.people == () and found.people_total == 0


def test_hidden_people_are_not_found(world):
    hidden = make_person(world.graph, "Ben Hidden")
    world.graph.store.save_node(hidden.with_visibility(Visibility.PRIVATE))
    friends_only = make_person(world.graph, "Ben Friendsonly")
    world.graph.store.save_node(
        world.graph.store.node(friends_only.id, Person).with_visibility(Visibility.CONNECTIONS)
    )
    assert people(find(world, world.alice, "ben")) == []
    connect(world, world.alice, friends_only)
    assert people(find(world, world.alice, "ben")) == ["Ben Friendsonly"]


def test_people_are_matched_on_their_name_only(world):
    ben = make_person(world.graph, "Casey")
    world.graph.profiles.update(ben.id, ben.id, bio="ben fan", about="I like Ben and Jerry's")
    assert people(find(world, world.alice, "ben")) == []


def test_demo_tags_are_not_searchable(world):
    make_person(world.graph, "Drew (demo student)")
    make_org(world.graph, "[Demo] Chess Club", OrgKind.CLUB)
    assert people(find(world, world.alice, "student")) == []
    assert find(world, world.alice, "demo").orgs == ()
    assert people(find(world, world.alice, "drew")) == ["Drew (demo student)"]
    assert searchable_name("[Demo] Chess Club") == "chess club"


# --- orgs and events -----------------------------------------------------------------


def test_orgs_are_found_by_name_even_when_logged_out(world):
    club = make_org(world.graph, "Benefit Concert Club", OrgKind.CLUB)
    assert [o.id for o in find(world, None, "benefit").orgs] == [club.id]
    assert [o.id for o in find(world, world.carol, "concert club").orgs] == [club.id]


def test_hidden_orgs_are_not_found(world):
    club = make_org(world.graph, "Secret Bench Club", OrgKind.CLUB)
    world.graph.store.save_node(club.with_visibility(Visibility.PRIVATE))
    assert find(world, world.carol, "bench").orgs == ()


def test_events_are_found_by_title_description_or_place(world):
    by_title = publish(world, "Bench press night")
    publish(world, "Bonfire")
    found = find(world, world.carol, "bench")
    assert [i.event.id for i in found.events] == [by_title.id] and found.events_total == 1


def test_drafts_and_members_only_events_are_not_found_by_outsiders(world):
    world.graph.events.create(make_event("Bench draft"), world.chapter.id, world.alice.id)
    publish(world, "Bench members night", visibility=Visibility.MEMBERS)
    assert find(world, world.carol, "bench").events == ()
    assert [i.event.title for i in find(world, world.alice, "bench").events] == ["Bench members night"]


def test_one_search_returns_all_three_kinds(world):
    make_person(world.graph, "Ben Okafor")
    make_org(world.graph, "Bengal Club", OrgKind.CLUB)
    publish(world, "Bento workshop")
    found = find(world, world.alice, "ben")
    assert (found.people_total, found.orgs_total, found.events_total) == (1, 1, 1)


# --- limits --------------------------------------------------------------------------


def test_results_are_capped_but_the_total_is_reported(world):
    for i in range(12):
        make_person(world.graph, f"Ben {i:02}")
    found = find(world, world.alice, "ben")
    assert len(found.people) == 8 and found.people_total == 12
    assert len(find(world, world.alice, "ben", limit=3).people) == 3


@pytest.mark.parametrize("text", ["", " ", "b", " b ", "x" * 101])
def test_a_search_needs_between_two_and_a_hundred_characters(world, text):
    with pytest.raises(DomainRuleError):
        find(world, world.alice, text)


@pytest.mark.parametrize("limit", [0, -1, MAX_LIMIT + 1])
def test_the_limit_is_bounded(world, limit):
    with pytest.raises(DomainRuleError):
        find(world, world.alice, "ben", limit=limit)


@settings(max_examples=60, deadline=None)
@given(st.text(max_size=120))
def test_any_text_either_searches_or_is_refused_cleanly(text):
    graph = CollectivizeGraph()
    viewer = make_person(graph, "Viewer")
    make_person(graph, "Ben Okafor")
    try:
        found = graph.directory.find(viewer.id, text, NOW)
    except DomainRuleError:
        return
    assert found.people_total == len(found.people) <= 1


# --- the API -------------------------------------------------------------------------


@pytest.fixture(scope="module")
def seeded():
    graph = CollectivizeGraph()
    return graph, seed_mock_data(graph, Environment.TEST, NOW)


@pytest.fixture(scope="module")
def api(seeded):
    @contextmanager
    def factory():
        yield seeded[0]
    return DiscoverApi(factory, clock=lambda: NOW)


def test_api_finds_people_orgs_and_events_with_clean_names(api, seeded):
    drew = seeded[1].people["drew"]
    data = api.find({"viewer": drew, "q": "al"})
    assert set(data) == {"query", "people", "orgs", "events"} and data["query"] == "al"
    for kind in ("people", "orgs", "events"):
        assert data[kind]["total"] >= len(data[kind]["items"])
    assert data["orgs"]["items"], "the demo data has orgs with 'al' in the name"
    assert all(set(o) == {"id", "name", "kind", "is_member"} for o in data["orgs"]["items"])
    assert "[Demo]" not in str(data) and "(demo" not in str(data) and "@" not in str(data)


def test_api_marks_connections_and_what_you_share(api, seeded):
    drew = seeded[1].people["drew"]
    friend = api.network({"viewer": drew})["people"][0]
    hit = next(p for p in api.find({"viewer": drew, "q": friend["name"]})["people"]["items"]
               if p["id"] == friend["id"])
    assert hit["connected"] is True and set(hit) == {"id", "name", "avatar", "role", "connected", "in_common"}


def test_api_logged_out_finds_orgs_but_no_people(api):
    data = api.find({"q": "drew"})
    assert data["people"] == {"total": 0, "items": []}


@pytest.mark.parametrize("params", [{}, {"q": ""}, {"q": "a"}, {"q": "x" * 101}, {"q": "ab", "viewer": "ghost"}])
def test_api_rejects_bad_searches(api, params):
    with pytest.raises(ApiError) as error:
        api.find(params)
    assert error.value.status is HTTPStatus.BAD_REQUEST
