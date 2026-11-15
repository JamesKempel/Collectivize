"""The demo API's behaviour, independent of HTTP (server.py wraps it).

`DiscoverApi` answers the Discover, Calendar and Network pages: personas,
topics, the ranked Discover list, AI search, RSVPs, stars, the personal
calendar and the network map.
Every input is validated here; problems raise `ApiError` with a status code
and a message that is safe to show.

Demo only: `demo_graph_factory` refuses the production database, because
sign-in has no email verification yet. The server passes the signed-in
viewer in `viewer`; it never comes from the browser.
"""

from __future__ import annotations

import logging
import threading
from collections import OrderedDict
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import datetime
from http import HTTPStatus
from typing import Any

from backend.config import DatabaseConfig, Environment
from backend.graph import (
    CollectivizeGraph,
    DiscoveryQuery,
)
from backend.graph.ai_search import InterpreterError
from backend.graph.discovery import DiscoveryItem
from backend.graph.my_calendar import CalendarEntry
from backend.graph.search_agent import AgentStep
from backend.graph.sqlite_store import SqliteGraphStore
from backend.network_api import clean_name, find_json, network_json, profile_changes
from backend.objects import (
    DomainRuleError,
    EventStatus,
    MemberOf,
    Organization,
    Person,
    RsvpStatus,
    Tag,
    Visibility,
)
from backend.objects.base import utc_now
from backend.seed import CAMPUS

log = logging.getLogger(__name__)

PER_PAGE = 10  # collectivize_plan.md: numbered pages of 10, no infinite scroll
CACHE_SIZE = 64
MAX_ID_LENGTH = 64
MAX_DATETIME_LENGTH = 40
RSVP_STATUS = {"going": RsvpStatus.GOING, "maybe": RsvpStatus.INTERESTED, None: None}
FEATURED = ("drew", "avery", "casey", "kai")  # suggested personas, by first name

GraphFactory = Callable[[], AbstractContextManager[CollectivizeGraph]]


class ApiError(Exception):
    def __init__(self, status: HTTPStatus, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


class _NoAiInterpreter:
    """Used with --no-ai: always 'unavailable', so search uses keywords."""

    name = "none"

    def interpret(self, request: Any) -> Any:
        raise InterpreterError("AI search is turned off on this server")


class _NoAiClient:
    """Used with --no-ai: the agent can't reach the API and falls back."""

    @property
    def beta(self) -> Any:
        import anthropic

        raise anthropic.AnthropicError("AI search is turned off on this server")


def demo_graph_factory(config: DatabaseConfig, *, use_ai: bool) -> GraphFactory:
    """Each request opens its own connection (SQLite connections can't be
    shared across the server's threads)."""
    if config.environment is not Environment.TEST:
        raise PermissionError(
            "the demo server only runs on the test database: sign-in isn't verified yet"
        )

    @contextmanager
    def factory() -> Iterator[CollectivizeGraph]:
        # One store per request, so it may remember its own reads.
        store = SqliteGraphStore(config.path, config.environment, read_cache=True)
        try:
            if use_ai:
                yield CollectivizeGraph(store)
            else:
                yield CollectivizeGraph(
                    store, search_interpreter=_NoAiInterpreter(), agent_client=_NoAiClient()
                )
        finally:
            store.close()

    return factory


class DiscoverApi:
    """The API's behaviour, independent of HTTP (so it can be tested directly)."""

    def __init__(
        self, graphs: GraphFactory, *, clock: Callable[[], datetime] = utc_now
    ) -> None:
        self._graphs = graphs
        self._clock = clock
        self._search_lock = threading.Lock()
        self._cache: OrderedDict[tuple[str | None, str, bool], dict[str, Any]] = OrderedDict()

    @property
    def graphs(self) -> GraphFactory:
        return self._graphs

    # --- endpoints ---------------------------------------------------------------

    def personas(self) -> dict[str, Any]:
        """Every demo person you can view Discover as, suggested ones first."""
        with self._graphs() as graph:
            people = []
            for person in graph.store.nodes(Person):
                orgs = [
                    (graph.store.node(m.target_id, Organization).name, m.is_admin)
                    for m in graph.store.edges(MemberOf, source_id=person.id)
                    if m.is_confirmed_current
                ]
                first = person.display_name.split(" ")[0]
                people.append({
                    "id": person.id,
                    "name": first,
                    "description": _describe(person.display_name, orgs),
                    "friends": len(graph.connections.connections_of(person.id)),
                    "featured": first.lower() in FEATURED,
                })
        rank = {name: i for i, name in enumerate(FEATURED)}
        people.sort(key=lambda p: (rank.get(p["name"].lower(), len(FEATURED)), p["name"]))
        return {"personas": people}

    def tags(self) -> dict[str, Any]:
        """All topic tags, by label (for the topic filter)."""
        with self._graphs() as graph:
            tags = sorted(graph.store.nodes(Tag), key=lambda t: t.label)
        return {"tags": [{"slug": t.slug, "label": t.label} for t in tags]}

    def discover(self, params: dict[str, str]) -> dict[str, Any]:
        """One page of Discover for a viewer: `viewer`, `page`, `near=1`, `tag`."""
        page = _int_param(params.get("page", "1"), "page", 1, 1000)
        near = params.get("near", "0") == "1"
        with self._graphs() as graph:
            viewer = self._viewer(graph, params.get("viewer"))
            tag_ids = self._tag_ids(graph, params.get("tag"))
            query = DiscoveryQuery(
                viewer_id=viewer, tag_ids=tag_ids, origin=CAMPUS if near else None,
                limit=PER_PAGE, offset=(page - 1) * PER_PAGE,
            )
            result = graph.discovery.search(query, self._clock())
            starred = graph.stars.starred_event_ids(viewer)
            items = [_item_json(i, starred) for i in result.items]
        return {"items": items, "total": result.total, "page": page, "per_page": PER_PAGE,
                "pages": max(1, -(-result.total // PER_PAGE))}

    def search(self, body: dict[str, Any]) -> dict[str, Any]:
        """AI search via the search agent: `query`, `viewer`, `near`. Repeat
        searches come from the cache; one runs at a time."""
        text = body.get("query")
        if not isinstance(text, str):
            raise ApiError(HTTPStatus.BAD_REQUEST, "say what you're looking for")
        near = body.get("near") is True
        viewer_param = body.get("viewer")
        if viewer_param is not None and not isinstance(viewer_param, str):
            raise ApiError(HTTPStatus.BAD_REQUEST, "unknown person")
        key = (viewer_param or None, " ".join(text.split()).casefold(), near)
        with self._search_lock:  # one AI search at a time
            if key in self._cache:
                self._cache.move_to_end(key)
                cached = self._cache[key]
                with self._graphs() as graph:  # RSVPs/stars may have changed since
                    items = self._refresh(graph, key[0], cached["items"])
                return {**cached, "items": items, "cached": True}
            with self._graphs() as graph:
                viewer = self._viewer(graph, viewer_param)
                result = graph.search_agent.search(
                    viewer, text, self._clock(), origin=CAMPUS if near else None
                )
                answer = {
                    "goal": result.goal,
                    "used_ai": result.used_agent,
                    "note": result.note,
                    "steps": [_step_json(s) for s in result.steps],
                    "items": [
                        _item_json(i, graph.stars.starred_event_ids(viewer))
                        for i in result.page.items
                    ],
                }
            self._cache[key] = answer
            if len(self._cache) > CACHE_SIZE:
                self._cache.popitem(last=False)
        return {**answer, "cached": False}

    def rsvp(self, body: dict[str, Any]) -> dict[str, Any]:
        """Set or clear an RSVP: `viewer`, `event_id`, `status` ("going",
        "maybe", or null to clear), `near` (records the trip distance)."""
        status = body.get("status")
        if not (status is None or isinstance(status, str)) or status not in RSVP_STATUS:
            raise ApiError(HTTPStatus.BAD_REQUEST, "status must be going, maybe or null")
        with self._graphs() as graph:
            viewer = self._required_viewer(graph, body.get("viewer"))
            event_id = _event_id(body.get("event_id"))
            graph.rsvps.respond(
                event_id, viewer, RSVP_STATUS[status], self._clock(),
                origin=CAMPUS if body.get("near") is True else None,
            )
            return self._state(graph, viewer, event_id)

    def star(self, body: dict[str, Any]) -> dict[str, Any]:
        """Star or unstar an event: `viewer`, `event_id`, `starred` (true/false)."""
        starred = body.get("starred")
        if not isinstance(starred, bool):
            raise ApiError(HTTPStatus.BAD_REQUEST, "starred must be true or false")
        with self._graphs() as graph:
            viewer = self._required_viewer(graph, body.get("viewer"))
            event_id = _event_id(body.get("event_id"))
            if starred:
                graph.stars.star(event_id, viewer, self._clock())
            else:
                graph.stars.unstar(event_id, viewer)
            return self._state(graph, viewer, event_id)

    def calendar(self, params: dict[str, str]) -> dict[str, Any]:
        """A person's calendar for a window: `viewer`, `start`, `end`
        (ISO 8601 with a time zone, at most 62 days apart)."""
        start = _datetime_param(params.get("start"), "start")
        end = _datetime_param(params.get("end"), "end")
        with self._graphs() as graph:
            viewer = self._viewer(graph, params.get("viewer"))
            cal = graph.my_calendar.for_viewer(viewer, start, end)
            return {
                "start": cal.start.isoformat(),
                "end": cal.end.isoformat(),
                "mine": [_entry_json(e) for e in cal.mine],
                "community": [_entry_json(e) for e in cal.community],
                "community_truncated": cal.community_truncated,
            }

    def network(self, params: dict[str, str]) -> dict[str, Any]:
        """The network map and the profile of whoever is in the middle:
        `viewer` (required) and `center` (the viewer, one of their
        connections, or an org they belong to; default the viewer)."""
        center = params.get("center") or None
        if center is not None and len(center) > MAX_ID_LENGTH:
            raise ApiError(HTTPStatus.BAD_REQUEST, "unknown person or org")
        with self._graphs() as graph:
            viewer = self._required_viewer(graph, params.get("viewer"))
            return network_json(graph, viewer, center, self._clock())

    def find(self, params: dict[str, str]) -> dict[str, Any]:
        """Find people, orgs and events by name: `q` (2-100 characters) and
        `viewer` (optional; logged-out visitors find no people)."""
        text = params.get("q", "")
        with self._graphs() as graph:
            viewer = self._viewer(graph, params.get("viewer"))
            try:
                return find_json(graph, viewer, text, self._clock())
            except DomainRuleError as error:
                raise ApiError(HTTPStatus.BAD_REQUEST, str(error)) from None

    def profile(self, body: dict[str, Any]) -> dict[str, Any]:
        """Save your own profile and settings: `viewer` plus any of
        `display_name`, `bio`, `about`, `top3`, `website`, `colors`,
        `sections`, `profile_visibility`, `rsvp_visibility`,
        `hide_connections`. Returns your page again (as GET /api/network)."""
        try:
            changes = profile_changes(body)
        except ValueError as error:
            raise ApiError(HTTPStatus.BAD_REQUEST, str(error)) from None
        with self._graphs() as graph:
            viewer = self._required_viewer(graph, body.get("viewer"))
            # The page shows demo names without their "(demo role)" tag, so a
            # name sent back unchanged must not overwrite the stored one.
            stored = graph.store.node(viewer, Person).display_name
            if changes.get("display_name") == clean_name(stored):
                del changes["display_name"]
            graph.profiles.update(viewer, viewer, **changes)
            return network_json(graph, viewer, None, self._clock())

    # --- helpers -------------------------------------------------------------------

    def _required_viewer(self, graph: CollectivizeGraph, viewer_id: Any) -> str:
        if not isinstance(viewer_id, str) or not viewer_id:
            raise ApiError(HTTPStatus.BAD_REQUEST, "choose who you are first")
        return self._viewer(graph, viewer_id)  # type: ignore[return-value]

    @staticmethod
    def _state(graph: CollectivizeGraph, viewer: str, event_id: str) -> dict[str, Any]:
        """The parts of an event that change when someone RSVPs or stars."""
        mine = graph.rsvps.mine(event_id, viewer)
        return {
            "event_id": event_id,
            "my_rsvp": mine.status.value if mine else None,
            "starred": graph.stars.star_of(event_id, viewer) is not None,
            "going_count": graph.rsvps.going_count(event_id),
            "is_full": graph.rsvps.is_full(event_id),
        }

    def _refresh(
        self, graph: CollectivizeGraph, viewer: str | None, items: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        if viewer is None or not graph.store.has_node(viewer):
            return items
        fresh = []
        for item in items:
            if not graph.store.has_node(item["id"]):
                continue  # deleted since the search ran
            state = self._state(graph, viewer, item["id"])
            fresh.append({**item, **{k: v for k, v in state.items() if k != "event_id"}})
        return fresh

    @staticmethod
    def _viewer(graph: CollectivizeGraph, viewer_id: str | None) -> str | None:
        if not viewer_id:
            return None
        if not graph.store.has_node(viewer_id) or not isinstance(
            graph.store.any_node(viewer_id), Person
        ):
            raise ApiError(HTTPStatus.BAD_REQUEST, "unknown person")
        return viewer_id

    @staticmethod
    def _tag_ids(graph: CollectivizeGraph, slug: str | None) -> tuple[str, ...]:
        if not slug:
            return ()
        found = [t.id for t in graph.store.nodes(Tag) if t.slug == slug]
        if not found:
            raise ApiError(HTTPStatus.BAD_REQUEST, "unknown topic")
        return tuple(found)


# --- JSON shapes -------------------------------------------------------------------


def _item_json(item: DiscoveryItem, starred: set[str] = frozenset()) -> dict[str, Any]:
    event = item.event
    host_is_org = isinstance(item.host, Organization)
    return {
        "id": event.id,
        "title": event.title,
        "description": event.description,
        "starts_at": event.starts_at.isoformat(),
        "ends_at": event.ends_at.isoformat(),
        "location": event.location,
        "host": {
            "id": item.host.id,
            "name": item.host.name if host_is_org else item.host.display_name,
            "kind": "org" if host_is_org else "person",
        },
        "score": round(item.score, 3),
        "reasons": list(item.reasons),
        "friends_going": [p.display_name for p in item.friends_going],
        "going_count": item.going_count,
        "my_rsvp": item.my_rsvp.value if item.my_rsvp else None,
        "distance_km": None if item.distance_km is None else round(item.distance_km, 2),
        "is_cancelled": item.is_cancelled,
        "starred": event.id in starred,
    }


STEP_TEXT = {
    "get_person_overview": "Looked at your interests and the kinds of events you go to",
    "get_active_orgs": "Checked the orgs you're most active in",
    "get_recent_events": "Looked at events you've been to lately",
    "list_tags": "Checked which topics events can have",
    "submit_picks": "Picked the best matches",
}


def _step_json(step: AgentStep) -> dict[str, Any]:
    text = STEP_TEXT.get(step.tool, step.tool.replace("_", " "))
    if step.tool == "search_events":
        parts = []
        if step.input.get("keywords"):
            parts.append(f"“{step.input['keywords']}”")
        if step.input.get("tags"):
            parts.append("topics: " + ", ".join(step.input["tags"]))
        if step.input.get("org_name"):
            parts.append(f"from {step.input['org_name']}")
        if step.input.get("within_days"):
            parts.append(f"in the next {step.input['within_days']} days")
        if step.input.get("max_distance_km"):
            parts.append(f"within {step.input['max_distance_km']} km")
        text = "Searched events" + (": " + ", ".join(parts) if parts else "")
    return {"tool": step.tool, "text": text, "error": step.is_error}


def _describe(display_name: str, orgs: list[tuple[str, bool]]) -> str:
    role = display_name.split("(", 1)[1].rstrip(")") if "(" in display_name else ""
    names = [name.removeprefix("[Demo] ") for name, _ in orgs]
    where = ", ".join(names[:2]) + (f" +{len(names) - 2}" if len(names) > 2 else "")
    return " · ".join(part for part in (role.removeprefix("demo "), where) if part)


def _int_param(value: str, name: str, low: int, high: int) -> int:
    if not value.isdigit():
        raise ApiError(HTTPStatus.BAD_REQUEST, f"{name} must be a whole number")
    number = int(value)
    if not low <= number <= high:
        raise ApiError(HTTPStatus.BAD_REQUEST, f"{name} must be between {low} and {high}")
    return number


def _entry_json(entry: CalendarEntry) -> dict[str, Any]:
    event = entry.event
    host = entry.host
    return {
        "id": event.id,
        "title": event.title,
        "starts_at": event.starts_at.isoformat(),
        "ends_at": event.ends_at.isoformat(),
        "location": event.location,
        "host": None if host is None else (
            host.name if isinstance(host, Organization) else host.display_name
        ),
        "host_id": None if host is None else host.id,  # with host_kind: "Hosted by …" links to their page
        "host_kind": None if host is None else ("org" if isinstance(host, Organization) else "person"),
        "relations": sorted(r.value for r in entry.relations),
        "is_cancelled": event.status is EventStatus.CANCELLED,
        "is_draft": not event.was_published,
        "is_private": event.visibility is not Visibility.PUBLIC,
    }


def _event_id(value: Any) -> str:
    if not isinstance(value, str) or not 0 < len(value) <= MAX_ID_LENGTH:
        raise ApiError(HTTPStatus.BAD_REQUEST, "unknown event")
    return value


def _datetime_param(value: str | None, name: str) -> datetime:
    if not value or len(value) > MAX_DATETIME_LENGTH:
        raise ApiError(HTTPStatus.BAD_REQUEST, f"{name} is required (ISO 8601 date and time)")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise ApiError(HTTPStatus.BAD_REQUEST, f"{name} isn't a valid date and time") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ApiError(HTTPStatus.BAD_REQUEST, f"{name} needs a time zone")
    return parsed

