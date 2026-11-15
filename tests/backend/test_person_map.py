"""The network map (network_plan.md, "How the network view works"): one
node at the center with what is directly linked to it, limited to nodes
the viewer could open (themselves, their connections, their orgs).
Everything else is left out. The map also says which people shown are
connected to each other and how close each node is to the center."""

from contextlib import contextmanager
from http import HTTPStatus

import pytest

from backend.config import Environment
from backend.graph import CollectivizeGraph, NotFoundError, PermissionDeniedError
from backend.graph.network import MAX_MAP_PEOPLE, NodeKind
from backend.objects import DomainRuleError, Visibility
from backend.seed import seed_mock_data
from backend.server import ApiError, DiscoverApi

from .conftest import NOW, make_event, make_person


def connect(world, a, b):
    request = world.graph.connections.request(a.id, b.id, NOW)
    world.graph.connections.accept(request.id, b.id)


def join(world, person, org, admin):
    edge = world.graph.membership.request(person.id, org.id, NOW)
    world.graph.membership.confirm(edge.id, admin.id)
    return edge


def by_name(view):
    return {p.name: p for p in view.people}


# --- what the map contains ---------------------------------------------------------


def test_your_own_map_has_your_orgs_and_connections(world):
    connect(world, world.alice, world.bob)
    world.graph.connections.request(world.alice.id, world.carol.id, NOW)  # pending
    view = world.graph.network.person_map(world.alice.id)
    assert view.is_self and view.center.label == "Alice"
    assert [o.name for o in view.orgs] == [world.chapter.name]
    assert list(by_name(view)) == ["Bob"]


def test_a_persons_map_does_not_show_who_else_is_in_their_orgs(world):
    connect(world, world.alice, world.bob)
    join(world, world.carol, world.chapter, world.alice)  # a member, not a connection
    view = world.graph.network.person_map(world.alice.id)
    assert list(by_name(view)) == ["Bob"]


def test_a_connections_map_leaves_out_people_you_are_not_connected_to(world):
    connect(world, world.alice, world.bob)
    connect(world, world.bob, world.carol)  # Carol is only Bob's connection
    dave = make_person(world.graph, "Dave")
    connect(world, world.bob, dave)
    connect(world, world.alice, dave)
    view = world.graph.network.person_map(world.alice.id, world.bob.id)
    assert not view.is_self and view.center.label == "Bob"
    assert [p.name for p in view.people] == ["Alice", "Dave"]  # you first; no Carol
    assert by_name(view)["Alice"].is_viewer


def test_a_connections_map_leaves_out_orgs_you_are_not_in(world):
    connect(world, world.alice, world.bob)
    join(world, world.bob, world.chapter, world.alice)
    view = world.graph.network.person_map(world.alice.id, world.bob.id)
    assert [o.name for o in view.orgs] == [world.chapter.name]  # not Bob's national


# --- links between the people shown --------------------------------------------------


def test_people_on_the_map_who_are_connected_to_each_other_are_linked(world):
    dave = make_person(world.graph, "Dave")
    for friend in (world.bob, world.carol, dave):
        connect(world, world.alice, friend)
    connect(world, world.bob, world.carol)
    view = world.graph.network.person_map(world.alice.id)
    assert view.links == (tuple(sorted((world.bob.id, world.carol.id))),)


def test_links_to_the_center_and_to_people_off_the_map_are_not_listed(world):
    connect(world, world.alice, world.bob)
    connect(world, world.bob, world.carol)  # Carol isn't on Alice's map
    assert world.graph.network.person_map(world.alice.id).links == ()


def test_a_link_is_left_out_when_one_of_the_two_hides_their_connections(world):
    connect(world, world.alice, world.bob)
    connect(world, world.alice, world.carol)
    connect(world, world.bob, world.carol)
    world.graph.connections.set_hide_connections(world.bob.id, world.bob.id, True)
    assert world.graph.network.person_map(world.alice.id).links == ()


def test_on_a_connections_map_you_are_linked_to_your_mutual_connections(world):
    connect(world, world.alice, world.bob)
    connect(world, world.alice, world.carol)
    connect(world, world.bob, world.carol)
    view = world.graph.network.person_map(world.alice.id, world.bob.id)
    assert view.links == (tuple(sorted((world.alice.id, world.carol.id))),)


# --- close but not connected ---------------------------------------------------------


def friends_of_alice(world, *names):
    people = [make_person(world.graph, name) for name in names]
    for person in people:
        connect(world, world.alice, person)
    return people


def test_two_people_who_share_a_mutual_connection_are_near(world):
    dave, erin, finn = friends_of_alice(world, "Dave", "Erin", "Finn")
    connect(world, dave, erin)
    connect(world, erin, finn)  # Dave and Finn both know Erin, but not each other
    view = world.graph.network.person_map(world.alice.id)
    assert view.near == (tuple(sorted((dave.id, finn.id))),)
    assert set(view.near).isdisjoint(view.links)


def test_two_people_in_the_same_org_are_near(world):
    dave, erin = friends_of_alice(world, "Dave", "Erin")
    join(world, dave, world.national, world.bob)
    join(world, erin, world.national, world.bob)
    view = world.graph.network.person_map(world.alice.id)
    assert view.near == (tuple(sorted((dave.id, erin.id))),)


def test_sharing_only_the_center_does_not_make_people_near(world):
    friends_of_alice(world, "Dave", "Erin")
    view = world.graph.network.person_map(world.alice.id)
    assert view.near == () and view.links == ()


def test_connected_people_are_linked_not_near(world):
    dave, erin = friends_of_alice(world, "Dave", "Erin")
    connect(world, dave, erin)
    join(world, dave, world.national, world.bob)
    join(world, erin, world.national, world.bob)
    view = world.graph.network.person_map(world.alice.id)
    assert view.links == (tuple(sorted((dave.id, erin.id))),) and view.near == ()


def test_a_private_membership_does_not_make_people_near(world):
    dave, erin = friends_of_alice(world, "Dave", "Erin")
    edge = join(world, dave, world.national, world.bob)
    join(world, erin, world.national, world.bob)
    world.graph.membership.set_visibility(edge.id, dave.id, Visibility.PRIVATE)
    assert world.graph.network.person_map(world.alice.id).near == ()


def test_on_an_orgs_map_the_org_itself_does_not_make_members_near(world):
    dave, erin = friends_of_alice(world, "Dave", "Erin")
    join(world, dave, world.chapter, world.alice)
    join(world, erin, world.chapter, world.alice)
    view = world.graph.network.org_map(world.alice.id, world.chapter.id)
    # Dave and Erin share Alice (also on the map), so they are near through her.
    assert tuple(sorted((dave.id, erin.id))) in view.near
    assert all(world.alice.id not in pair for pair in view.near)  # she's connected to both


# --- closeness -----------------------------------------------------------------------


def test_closeness_counts_what_a_node_shares_with_the_center(world):
    dave = make_person(world.graph, "Dave")
    for friend in (world.bob, world.carol, dave):
        connect(world, world.alice, friend)
    connect(world, world.bob, world.carol)
    join(world, world.bob, world.chapter, world.alice)
    view = world.graph.network.person_map(world.alice.id)
    people = by_name(view)
    assert people["Bob"].closeness == 2  # Carol and the chapter
    assert people["Carol"].closeness == 1  # Bob
    assert people["Dave"].closeness == 0
    assert [p.name for p in view.people] == ["Bob", "Carol", "Dave"]  # closest first
    assert view.orgs[0].closeness == 1  # Bob is in it


# --- an org at the center ------------------------------------------------------------


def test_an_org_you_belong_to_shows_only_members_who_are_your_connections(world):
    join(world, world.bob, world.chapter, world.alice)
    join(world, world.carol, world.chapter, world.alice)
    connect(world, world.alice, world.carol)
    view = world.graph.network.org_map(world.alice.id, world.chapter.id)
    assert view.center.label == world.chapter.name and view.center.kind is NodeKind.ORG
    assert view.orgs == () and not view.is_self
    assert [p.name for p in view.people] == ["Alice", "Carol"]  # Bob isn't your connection
    assert view.links == (tuple(sorted((world.alice.id, world.carol.id))),)


def test_you_cannot_open_an_org_you_do_not_belong_to(world):
    connect(world, world.alice, world.bob)
    with pytest.raises(PermissionDeniedError):
        world.graph.network.org_map(world.alice.id, world.national.id)
    world.graph.membership.request(world.alice.id, world.national.id, NOW)  # pending
    with pytest.raises(PermissionDeniedError):
        world.graph.network.org_map(world.alice.id, world.national.id)


def test_private_members_are_left_off_an_orgs_map(world):
    connect(world, world.alice, world.bob)
    edge = join(world, world.bob, world.chapter, world.alice)
    world.graph.membership.set_visibility(edge.id, world.bob.id, Visibility.PRIVATE)
    view = world.graph.network.org_map(world.alice.id, world.chapter.id)
    assert list(by_name(view)) == ["Alice"]


def test_a_member_of_your_org_cannot_be_opened_unless_connected(world):
    join(world, world.bob, world.chapter, world.alice)
    with pytest.raises(PermissionDeniedError):
        world.graph.network.person_map(world.alice.id, world.bob.id)


def test_missing_and_hidden_orgs_look_the_same(world):
    for target in ("nobody", world.alice.id):
        with pytest.raises(NotFoundError):
            world.graph.network.org_map(world.alice.id, target)


def test_node_map_picks_the_right_kind_of_map(world):
    net = world.graph.network
    assert net.node_map(world.alice.id).is_self
    assert net.node_map(world.alice.id, world.chapter.id).center.kind is NodeKind.ORG
    connect(world, world.alice, world.bob)
    assert net.node_map(world.alice.id, world.bob.id).center.label == "Bob"
    with pytest.raises(NotFoundError):
        net.node_map(world.alice.id, "nobody")


# --- who may open a map ------------------------------------------------------------


def test_you_cannot_open_the_map_of_someone_you_are_not_connected_to(world):
    connect(world, world.alice, world.bob)
    connect(world, world.bob, world.carol)
    with pytest.raises(PermissionDeniedError):
        world.graph.network.person_map(world.alice.id, world.carol.id)  # friend of a friend


def test_a_pending_connection_does_not_open_a_map(world):
    world.graph.connections.request(world.alice.id, world.bob.id, NOW)
    with pytest.raises(PermissionDeniedError):
        world.graph.network.person_map(world.alice.id, world.bob.id)


def test_logged_out_visitors_get_no_map(world):
    with pytest.raises(PermissionDeniedError):
        world.graph.network.person_map(None, world.alice.id)


def test_orgs_and_missing_or_hidden_people_look_the_same(world):
    hidden = make_person(world.graph, "Hidden")
    world.graph.store.save_node(hidden.with_visibility(Visibility.PRIVATE))
    for target in (world.chapter.id, "nobody", hidden.id):
        with pytest.raises(NotFoundError):
            world.graph.network.person_map(world.alice.id, target)


# --- only what the viewer may see ----------------------------------------------------


def test_a_private_membership_keeps_an_org_off_the_map(world):
    connect(world, world.alice, world.bob)
    edge = join(world, world.bob, world.chapter, world.alice)
    world.graph.membership.set_visibility(edge.id, world.bob.id, Visibility.PRIVATE)
    view = world.graph.network.person_map(world.alice.id, world.bob.id)
    assert view.orgs == ()


def test_everything_on_a_map_can_be_opened_by_the_viewer(world):
    dave = make_person(world.graph, "Dave")
    connect(world, world.alice, world.bob)
    connect(world, world.bob, world.carol)
    connect(world, world.bob, dave)
    connect(world, world.alice, dave)
    join(world, world.bob, world.chapter, world.alice)
    net = world.graph.network
    view = net.person_map(world.alice.id, world.bob.id)
    for node in view.orgs + view.people:
        assert net.node_map(world.alice.id, node.id)  # none of them raise


def test_a_very_large_map_is_cut_short_and_says_so(world):
    for i in range(MAX_MAP_PEOPLE + 3):
        connect(world, world.alice, make_person(world.graph, f"Friend {i:03}"))
    view = world.graph.network.person_map(world.alice.id)
    assert len(view.people) == MAX_MAP_PEOPLE and view.truncated


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


def test_api_returns_the_viewers_own_map_with_clean_names(api, seeded):
    drew = seeded[1].people["drew"]
    data = api.network({"viewer": drew})
    assert data["center"] == {"id": drew, "name": "Drew", "kind": "person", "avatar": None}
    assert data["is_self"] is True and data["orgs"] and data["people"]
    ids = {p["id"] for p in data["people"]}
    assert data["links"] and all(len(pair) == 2 and set(pair) <= ids for pair in data["links"])
    assert all(isinstance(n["closeness"], int) for n in data["orgs"] + data["people"])
    assert all(len(pair) == 2 and set(pair) <= ids for pair in data["near"])
    assert not {tuple(p) for p in data["near"]} & {tuple(p) for p in data["links"]}
    assert "[Demo]" not in str(data) and "(demo" not in str(data) and "@" not in str(data)


def test_api_only_ever_returns_nodes_the_viewer_can_open(api, seeded):
    drew = seeded[1].people["drew"]
    own = api.network({"viewer": drew})
    mine = {n["id"] for n in own["orgs"] + own["people"]} | {drew}
    for node in own["orgs"] + own["people"]:
        theirs = api.network({"viewer": drew, "center": node["id"]})
        assert {n["id"] for n in theirs["orgs"] + theirs["people"]} <= mine
        assert [p["name"] for p in theirs["people"] if p["is_you"]] == ["Drew"]


def test_api_shows_a_strangers_page_without_their_network(api, seeded):
    drew = seeded[1].people["drew"]
    own = api.network({"viewer": drew})
    known = {n["id"] for n in own["orgs"] + own["people"]} | {drew}
    stranger = next(p for p in seeded[1].people.values() if p not in known)
    other_org = next(o for o in seeded[1].orgs.values() if o not in known)
    for center, kind in ((stranger, "person"), (other_org, "org")):
        page = api.network({"viewer": drew, "center": center})
        assert page["network_open"] is False and page["center"]["kind"] == kind
        assert page["orgs"] == page["people"] == page["links"] == page["near"] == []
        assert page["profile"]["kind"] == kind and not page["is_self"]
    assert api.network({"viewer": drew, "center": stranger})["profile"]["connection"] == "none"
    assert api.network({"viewer": drew, "center": other_org})["profile"]["is_member"] is False
    assert own["network_open"] is True


@pytest.mark.parametrize("params", [{}, {"viewer": ""}, {"viewer": "nobody"}])
def test_api_needs_a_known_viewer(api, params):
    with pytest.raises(ApiError) as error:
        api.network(params)
    assert error.value.status is HTTPStatus.BAD_REQUEST


def test_api_rejects_bad_centers(api, seeded):
    drew = seeded[1].people["drew"]
    with pytest.raises(ApiError):
        api.network({"viewer": drew, "center": "x" * 65})
    with pytest.raises(NotFoundError):
        api.network({"viewer": drew, "center": "nobody"})


# --- the profile above the map -------------------------------------------------------


def test_your_own_profile_has_no_in_common_and_nothing_private(api, seeded):
    drew = seeded[1].people["drew"]
    profile = api.network({"viewer": drew})["profile"]
    assert profile["kind"] == "person" and profile["name"] == "Drew"
    assert profile["role"] == "student" and profile["in_common"] is None
    assert profile["is_self"] and profile["access"] == "full" and "settings" in profile
    assert "email" not in profile and "@" not in str(profile)


def test_a_connections_profile_says_what_you_have_in_common(api, seeded):
    drew = seeded[1].people["drew"]
    own = api.network({"viewer": drew})
    friend = max(own["people"], key=lambda p: p["closeness"])
    data = api.network({"viewer": drew, "center": friend["id"]})
    profile = data["profile"]
    assert profile["kind"] == "person" and profile["name"] == friend["name"]
    assert profile["connection"] == "connected" and "settings" not in profile
    shown = len([p for p in data["people"] if not p["is_you"]])
    assert (f"{shown} mutual connection" in profile["in_common"]) == (shown > 0)
    assert all(o["name"] in profile["in_common"] for o in data["orgs"])
    assert "[Demo]" not in str(profile) and "@" not in str(profile)


def test_an_orgs_profile_has_its_kind_and_upcoming_events(api, seeded):
    drew = seeded[1].people["drew"]
    org = api.network({"viewer": drew})["orgs"][0]
    profile = api.network({"viewer": drew, "center": org["id"]})["profile"]
    assert profile["kind"] == "org" and profile["name"] == org["name"]
    assert profile["org_kind"] in {"chapter", "national", "council", "club", "institution"}
    assert profile["upcoming_count"] >= len(profile["upcoming"]) and len(profile["upcoming"]) <= 3
    starts = [e["starts_at"] for e in profile["upcoming"]]
    assert starts == sorted(starts) and all(s >= NOW.isoformat() for s in starts)
    assert all(set(e) == {"id", "title", "starts_at", "location"} for e in profile["upcoming"])


def test_an_org_website_is_only_sent_when_it_is_a_web_link(world):
    from dataclasses import replace

    from backend.network_api import network_json

    def website(url):
        world.graph.store.save_node(replace(world.chapter, website_url=url))
        return network_json(world.graph, world.alice.id, world.chapter.id, NOW)["profile"]["website"]

    assert website("https://chapter.example/") == "https://chapter.example/"
    assert website(None) is None
    with pytest.raises(DomainRuleError):  # the org itself refuses anything else
        website("javascript:alert(1)")


def test_an_orgs_profile_leaves_out_cancelled_and_draft_events(world):
    from backend.network_api import network_json

    ev = world.graph.events
    kept = ev.create(make_event("Kept", days_ahead=2), world.chapter.id, world.alice.id)
    ev.publish(kept.id, world.alice.id, NOW)
    gone = ev.create(make_event("Cancelled", days_ahead=3), world.chapter.id, world.alice.id)
    ev.publish(gone.id, world.alice.id, NOW)
    ev.cancel(gone.id, world.alice.id)
    ev.create(make_event("Draft", days_ahead=4), world.chapter.id, world.alice.id)
    profile = network_json(world.graph, world.alice.id, world.chapter.id, NOW)["profile"]
    assert [e["title"] for e in profile["upcoming"]] == ["Kept"] and profile["upcoming_count"] == 1
