"""A person's profile page: what a viewer may read, and the owner's edits.

Reading (`view`):
- A viewer who can't see the person at all gets NotFoundError, like
  everywhere else (hidden looks missing).
- `profile_visibility` decides between the FULL profile and a LOCKED one
  (name, verified badge and colours only): NETWORK = any logged-in user,
  CONNECTIONS = accepted connections, PRIVATE = only the person. You
  always get your own profile in full.
- Orgs and events are filtered one by one with the existing rules, so a
  private membership or RSVP never appears, whatever the profile setting.

Editing (`update`): only the person themselves (or a platform admin
managing the account), only the fields in EDITABLE, and every limit is
checked when the new Person is built.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum
from typing import Any

from backend.objects import (
    DomainRuleError,
    Event,
    EventStatus,
    MemberOf,
    Organization,
    Person,
    Rsvp,
    RsvpStatus,
    Visibility,
)
from backend.objects.person import MAX_ABOUT, MAX_DISPLAY_NAME

from .calendar import CalendarService
from .connections import ConnectionService
from .errors import NotFoundError, PermissionDeniedError
from .privacy import PrivacyService
from .roster import RosterService
from .rsvps import RsvpService, may_manage
from .store import GraphStore

MAX_LISTED = 6  # orgs and events shown per list

# What the owner may change, and the type each value must have.
EDITABLE: dict[str, type | tuple[type, ...]] = {
    "display_name": str,
    "bio": str,
    "about": str,
    "top3_title": str,
    "top3_items": tuple,
    "website": (str, type(None)),
    "color_background": str,
    "color_outline": str,
    "background_picture": str,
    "profile_visibility": Visibility,
    "profile_sections": tuple,
    "rsvp_visibility": Visibility,
    "hide_connections": bool,
}


class ProfileAccess(Enum):
    FULL = "full"
    LOCKED = "locked"


@dataclass(frozen=True)
class ProfileView:
    person: Person
    is_self: bool
    access: ProfileAccess
    connection: str  # "self", "connected", "pending_out", "pending_in" or "none"
    orgs: tuple[Organization, ...]
    hosting: tuple[Event, ...]
    going: tuple[Event, ...]


class ProfileService:
    def __init__(
        self,
        store: GraphStore,
        privacy: PrivacyService,
        connections: ConnectionService,
        roster: RosterService,
        calendar: CalendarService,
        rsvps: RsvpService,
    ) -> None:
        self._store = store
        self._privacy = privacy
        self._connections = connections
        self._roster = roster
        self._calendar = calendar
        self._rsvps = rsvps

    # --- reading -------------------------------------------------------------

    def view(self, person_id: str, viewer_id: str | None, now: datetime) -> ProfileView:
        """A person's profile as this viewer may read it: full or locked,
        with only the orgs and upcoming events the viewer is allowed to see."""
        person = self._visible_person(person_id, viewer_id)
        is_self = viewer_id == person.id
        connection = "self" if is_self else self._connection(viewer_id, person.id)
        access = self._access(person, is_self, connection)
        if access is ProfileAccess.LOCKED:
            return ProfileView(person, is_self, access, connection, (), (), ())
        return ProfileView(
            person=person,
            is_self=is_self,
            access=access,
            connection=connection,
            orgs=self._orgs(person.id, viewer_id),
            hosting=self._hosting(person.id, viewer_id, now),
            going=self._going(person.id, viewer_id, now),
        )

    def _visible_person(self, person_id: str, viewer_id: str | None) -> Person:
        node = self._store.any_node(person_id) if self._store.has_node(person_id) else None
        if not (isinstance(node, Person) and node.is_active and self._privacy.can_view(viewer_id, node)):
            raise NotFoundError(f"{person_id!r} not found")
        return node

    def _connection(self, viewer_id: str | None, person_id: str) -> str:
        edge = self._connections.between(viewer_id, person_id) if viewer_id else None
        if edge is None or not edge.is_active:
            return "none"
        if edge.is_established:
            return "connected"
        return "pending_out" if edge.source_id == viewer_id else "pending_in"

    @staticmethod
    def _access(person: Person, is_self: bool, connection: str) -> ProfileAccess:
        level = person.profile_visibility
        allowed = is_self or level is Visibility.NETWORK or (
            level is Visibility.CONNECTIONS and connection == "connected"
        )
        return ProfileAccess.FULL if allowed else ProfileAccess.LOCKED

    def _orgs(self, person_id: str, viewer_id: str | None) -> tuple[Organization, ...]:
        orgs = []
        for edge in self._store.edges(MemberOf, source_id=person_id):
            if not edge.is_confirmed_current:
                continue
            org = self._store.node(edge.target_id, Organization)
            if not (org.is_active and self._privacy.can_view(viewer_id, org)):
                continue
            if viewer_id == person_id or self._roster.shows(viewer_id, edge):
                orgs.append(org)
        return tuple(sorted(orgs, key=lambda o: (o.name, o.id))[:MAX_LISTED])

    def _hosting(self, person_id: str, viewer_id: str | None, now: datetime) -> tuple[Event, ...]:
        listing = self._calendar.host_events(person_id, viewer_id, starts_after=now)
        events = [e for e in (*listing.public, *listing.private) if e.was_published]
        return tuple(sorted(events, key=lambda e: (e.starts_at, e.id))[:MAX_LISTED])

    def _going(self, person_id: str, viewer_id: str | None, now: datetime) -> tuple[Event, ...]:
        events = []
        for rsvp in self._store.edges(Rsvp, source_id=person_id):
            if rsvp.status is not RsvpStatus.GOING or not self._privacy.can_view(viewer_id, rsvp):
                continue
            event = self._store.node(rsvp.target_id, Event)
            listed = event.status in (EventStatus.PUBLISHED, EventStatus.CANCELLED)
            if listed and event.ends_at > now and self._privacy.can_view_listing(viewer_id, event):
                events.append(event)
        return tuple(sorted(events, key=lambda e: (e.starts_at, e.id))[:MAX_LISTED])

    # --- editing -------------------------------------------------------------

    def update(self, person_id: str, by_person_id: str, **changes: Any) -> Person:
        """Change your own profile and its settings (a platform admin may
        change anyone's). Returns the saved person."""
        if not may_manage(self._store, person_id, by_person_id):
            raise PermissionDeniedError("only you can edit your profile")
        person = self._store.node(person_id, Person)
        unknown = sorted(set(changes) - set(EDITABLE))
        if unknown:
            raise DomainRuleError(f"cannot edit fields: {unknown}")
        for name, value in changes.items():
            if not isinstance(value, EDITABLE[name]) or (
                isinstance(value, tuple) and not all(isinstance(item, str) for item in value)
            ):
                raise DomainRuleError(f"{name} has the wrong kind of value")
        fields = dict(changes)
        rsvp_level = fields.pop("rsvp_visibility", None)
        if "about" in fields:
            fields["profile"] = fields.pop("about")
            if len(fields["profile"]) > MAX_ABOUT:
                raise DomainRuleError(f"about can be at most {MAX_ABOUT} characters")
        if len(fields.get("display_name", "")) > MAX_DISPLAY_NAME:
            raise DomainRuleError(f"display name can be at most {MAX_DISPLAY_NAME} characters")
        with self._store.transaction():
            saved = self._store.save_node(replace(person, **fields))  # checks every limit
            if rsvp_level is not None and rsvp_level is not saved.rsvp_visibility:
                saved = self._rsvps.set_rsvp_visibility(person_id, by_person_id, rsvp_level)
        return saved
