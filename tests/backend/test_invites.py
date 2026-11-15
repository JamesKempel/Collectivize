"""Joining by invite: a single-use code from an existing person, a
university email, and the inviter becomes your first connection."""

import json
from datetime import timedelta

import pytest

from backend.graph import CollectivizeGraph, PermissionDeniedError
from backend.graph.codec import encode_record
from backend.graph.invites import MAX_OPEN_INVITES
from backend.objects import Connected, ConnectionOrigin, DomainRuleError, Invite, Person
from backend.objects.person import AVATARS

from .conftest import NOW

EMAIL = "new.student@northeastern.edu"


def invite(world, inviter=None, at=NOW):
    return world.graph.invites.create((inviter or world.alice).id, at)


def redeem(world, code, email=EMAIL, name="Nia", at=NOW):
    return world.graph.invites.redeem(code, email, name, at)


# --- creating ------------------------------------------------------------------


def test_the_code_itself_is_never_stored(world):
    issued = invite(world)
    stored = world.graph.store.nodes(Invite)
    assert len(stored) == 1
    assert issued.code not in json.dumps(encode_record(stored[0]))
    assert stored[0].id != issued.code
    assert len(issued.code) >= 12


def test_codes_are_unique(world):
    codes = {invite(world).code for _ in range(20)}
    assert len(codes) == 20


def test_open_invites_are_limited_per_person(world):
    for _ in range(MAX_OPEN_INVITES):
        invite(world)
    with pytest.raises(DomainRuleError):
        invite(world)


def test_only_people_can_invite(world):
    with pytest.raises(LookupError):
        world.graph.invites.create(world.chapter.id, NOW)


# --- redeeming -----------------------------------------------------------------


def test_redeeming_creates_the_person_connected_to_the_inviter(world):
    issued = invite(world)
    joined = redeem(world, issued.code)
    person = world.graph.store.node(joined.person.id, Person)
    assert person.display_name == "Nia"
    assert person.email == EMAIL
    assert person.avatar in AVATARS
    assert world.graph.connections.are_connected(person.id, world.alice.id)
    assert joined.connection.origin is ConnectionOrigin.INVITE
    assert joined.inviter.id == world.alice.id
    view = world.graph.network.neighborhood(person.id)
    assert world.alice.id in {n.id for n in view.nodes}
    assert world.graph.integrity.audit() == ()


def test_an_invite_works_once(world):
    issued = invite(world)
    redeem(world, issued.code)
    with pytest.raises(DomainRuleError):
        redeem(world, issued.code, email="someone.else@northeastern.edu")


@pytest.mark.parametrize("problem", ["wrong-code", "expired", "revoked"])
def test_unusable_invites_all_fail_the_same_way(world, problem):
    issued = invite(world)
    code, at = issued.code, NOW
    if problem == "wrong-code":
        code = "not-a-real-code-at-all"
    elif problem == "expired":
        at = NOW + timedelta(days=15)
    else:
        world.graph.invites.revoke(issued.invite.id, world.alice.id)
    with pytest.raises(DomainRuleError, match="invalid or expired invite"):
        redeem(world, code, at=at)


def test_spaces_around_a_pasted_code_are_ignored(world):
    issued = invite(world)
    assert redeem(world, f"  {issued.code}\n").person.display_name == "Nia"


@pytest.mark.parametrize("email", [
    "student@gmail.com",
    "student@mail.northeastern.edu",
    "student@northeastern.edu.evil.com",
    "not-an-email",
    "two@@northeastern.edu",
    "@northeastern.edu",
])
def test_only_valid_university_emails_are_accepted(world, email):
    issued = invite(world)
    with pytest.raises(DomainRuleError):
        redeem(world, issued.code, email=email)
    assert world.graph.store.node(issued.invite.id, Invite).used_by is None


def test_emails_are_normalized_and_used_once(world):
    joined = redeem(world, invite(world).code, email="  New.Student@NorthEastern.EDU ")
    assert joined.person.email == EMAIL
    with pytest.raises(DomainRuleError, match="already has an account"):
        redeem(world, invite(world, world.bob).code, email=EMAIL)


def test_a_failed_redemption_leaves_the_invite_unused(world):
    issued = invite(world)
    with pytest.raises(DomainRuleError):
        redeem(world, issued.code, name="   ")
    assert len(world.graph.store.nodes(Person)) == 3
    assert redeem(world, issued.code).person.display_name == "Nia"


def test_allowed_email_domains_are_one_setting(world):
    graph = CollectivizeGraph(world.graph.store, invite_email_domains=("example.edu",))
    issued = graph.invites.create(world.alice.id, NOW)
    assert graph.invites.redeem(issued.code, "a@example.edu", "Ana", NOW).person.email


# --- afterwards ----------------------------------------------------------------


def test_the_new_person_can_remove_the_inviter_connection(world):
    joined = redeem(world, invite(world).code)
    world.graph.connections.remove(joined.connection.id, joined.person.id)
    assert not world.graph.connections.are_connected(joined.person.id, world.alice.id)


def test_inviters_see_and_revoke_only_their_own_invites(world):
    mine = invite(world)
    invite(world, world.bob)
    listed = world.graph.invites.invites_of(world.alice.id, world.alice.id)
    assert [i.id for i in listed] == [mine.invite.id]
    with pytest.raises(PermissionDeniedError):
        world.graph.invites.invites_of(world.alice.id, world.bob.id)
    with pytest.raises(PermissionDeniedError):
        world.graph.invites.revoke(mine.invite.id, world.bob.id)


def test_used_invites_cannot_be_revoked(world):
    issued = invite(world)
    redeem(world, issued.code)
    with pytest.raises(DomainRuleError):
        world.graph.invites.revoke(issued.invite.id, world.alice.id)


def test_erasing_an_account_erases_its_invites(world):
    open_invite = invite(world)
    used = invite(world)
    joined = redeem(world, used.code)
    world.graph.privacy.erase_person(joined.person.id)
    assert not world.graph.store.has_node(used.invite.id)
    world.graph.privacy.erase_person(world.alice.id)
    assert world.graph.store.nodes(Invite) == []
    assert not world.graph.store.has_node(open_invite.invite.id)
    assert world.graph.store.edges(Connected, include_inactive=True) == []
