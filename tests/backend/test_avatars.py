"""Profile pictures: a random animal saved when an account is created."""

import pytest

from backend.graph.codec import decode_record, encode_record
from backend.objects import DomainRuleError, Person
from backend.objects.person import AVATARS, random_avatar

from .conftest import staff_provenance


def test_random_avatar_is_an_animal_and_varies():
    picks = {random_avatar() for _ in range(300)}
    assert picks <= set(AVATARS)
    assert len(picks) > 1  # random, not one fixed animal


def test_an_avatar_must_be_one_of_the_animals():
    assert Person(display_name="Nia", avatar="🦊", provenance=staff_provenance()).avatar == "🦊"
    with pytest.raises(DomainRuleError):
        Person(display_name="Nia", avatar="🍕", provenance=staff_provenance())


def test_people_saved_before_avatars_load_with_none():
    data = encode_record(Person(display_name="Old Timer", provenance=staff_provenance()))
    del data["avatar"]
    assert decode_record("Person", data).avatar == ""
