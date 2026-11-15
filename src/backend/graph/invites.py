"""Joining Collectivize by invite.

- Any person can create an invite. They get a random code to share; only
  a SHA-256 fingerprint of it is stored (it is the Invite node's id).
- Invites are single-use, expire after INVITE_LIFETIME, can be revoked by
  the inviter while unused, and each person may have at most
  MAX_OPEN_INVITES open at once.
- Redeeming takes the code, a university email and a display name. It
  creates the person and connects them to the inviter, all or nothing.
  The inviter agreed by inviting and the new person by joining; either
  can remove the connection later.
- Every reason an invite can't be used (unknown, used, expired, revoked)
  gives the same error, so codes can't be probed.

Email is checked for shape and domain only. Proving the person controls
the address (a magic link) belongs to the future login layer.
"""

from __future__ import annotations

import hashlib
import re
import secrets
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta

from backend.config import ALLOWED_EMAIL_DOMAINS
from backend.objects import (
    Connected,
    DomainRuleError,
    Invite,
    Person,
    Provenance,
    ProvenanceMethod,
)
from backend.objects.person import random_avatar

from .connections import ConnectionService
from .errors import NotFoundError, PermissionDeniedError
from .store import GraphStore

DEFAULT_EMAIL_DOMAINS = ALLOWED_EMAIL_DOMAINS
INVITE_LIFETIME = timedelta(days=14)
MAX_OPEN_INVITES = 20
CODE_BYTES = 12  # 16 url-safe characters
MIN_CUSTOM_CODE_LENGTH = 12
INVALID_INVITE = "invalid or expired invite"
EMAIL_SHAPE = re.compile(r"^[a-z0-9._%+-]+@([a-z0-9-]+(?:\.[a-z0-9-]+)+)$")
CODE_SHAPE = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class IssuedInvite:
    """`code` is shown to the inviter once; it can't be recovered later."""

    code: str
    invite: Invite


@dataclass(frozen=True)
class Redemption:
    person: Person
    inviter: Person
    connection: Connected


class InviteService:
    def __init__(
        self,
        store: GraphStore,
        connections: ConnectionService,
        allowed_email_domains: Iterable[str] = DEFAULT_EMAIL_DOMAINS,
    ) -> None:
        self._store = store
        self._connections = connections
        self.allowed_email_domains = frozenset(d.lower() for d in allowed_email_domains)

    # --- inviter -------------------------------------------------------------

    def create(
        self, inviter_id: str, now: datetime, *, code: str | None = None
    ) -> IssuedInvite:
        """`code` may be fixed only for demo data; real invites use a random one."""
        self._store.node(inviter_id, Person)
        if len(self._open_invites(inviter_id, now)) >= MAX_OPEN_INVITES:
            raise DomainRuleError(f"you can have at most {MAX_OPEN_INVITES} open invites")
        code = code if code is not None else secrets.token_urlsafe(CODE_BYTES)
        if len(code) < MIN_CUSTOM_CODE_LENGTH or not CODE_SHAPE.match(code):
            raise DomainRuleError("invite codes need 12+ letters, digits, - or _")
        if self._store.has_node(fingerprint(code)):
            raise DomainRuleError("that invite code is already taken")
        invite = Invite(
            id=fingerprint(code),
            inviter_id=inviter_id,
            expires_at=now + INVITE_LIFETIME,
            provenance=Provenance(
                created_by=inviter_id, method=ProvenanceMethod.SELF_CLAIM, created_at=now
            ),
        )
        return IssuedInvite(code=code, invite=self._store.save_node(invite))

    def revoke(self, invite_id: str, by_person_id: str) -> Invite:
        invite = self._own_invite(invite_id, by_person_id)
        if invite.used_by is not None:
            raise DomainRuleError("this invite has already been used")
        return self._store.save_node(invite.revoked_now())

    def invites_of(self, person_id: str, by_person_id: str) -> list[Invite]:
        if person_id != by_person_id:
            raise PermissionDeniedError("you can only see your own invites")
        return [i for i in self._store.nodes(Invite) if i.inviter_id == person_id]

    # --- the person invited --------------------------------------------------

    def inviter_of(self, code: str, now: datetime) -> Person:
        """Who sent a usable invite (for the invite landing page's preview
        card). Every unusable code gives the same error."""
        invite = self._usable_invite(code, now)
        return self._store.node(invite.inviter_id, Person)

    def accept_as_existing(self, code: str, person_id: str, now: datetime) -> Connected | None:
        """Someone who already has an account opens an invite: they connect
        with the inviter (both agreed: one by inviting, one by accepting).
        A request either way is completed; an existing connection leaves
        the invite unused."""
        invite = self._usable_invite(code, now)
        if invite.inviter_id == person_id:
            raise DomainRuleError("that's your own invite")
        existing = self._connections.between(invite.inviter_id, person_id)
        if existing is not None and existing.is_established:
            return None
        with self._store.transaction():
            if existing is not None:
                self._store.delete_edge(existing.id)
            connection = self._connections.connect_via_invite(invite.inviter_id, person_id, now)
            self._store.save_node(invite.used(person_id, now))
        return connection

    # --- new person ----------------------------------------------------------

    def redeem(
        self, code: str, email: str, display_name: str, now: datetime
    ) -> Redemption:
        invite = self._usable_invite(code, now)
        address = self.validate_email(email)
        with self._store.transaction():
            person = self._store.save_node(
                Person(
                    display_name=display_name,
                    email=address,
                    avatar=random_avatar(),
                    provenance=Provenance(
                        created_by=None, method=ProvenanceMethod.SELF_CLAIM, created_at=now
                    ),
                )
            )
            connection = self._connections.connect_via_invite(
                invite.inviter_id, person.id, now
            )
            self._store.save_node(invite.used(person.id, now))
        return Redemption(
            person=person,
            inviter=self._store.node(invite.inviter_id, Person),
            connection=connection,
        )

    def validate_email(self, email: str) -> str:
        """Normalized address, or DomainRuleError if it isn't an allowed,
        unused university email."""
        address = email.strip().lower()
        match = EMAIL_SHAPE.match(address)
        if match is None:
            raise DomainRuleError("enter a valid email address")
        if match.group(1) not in self.allowed_email_domains:
            allowed = ", ".join(sorted(self.allowed_email_domains))
            raise DomainRuleError(f"use your university email ({allowed})")
        if any(p.email == address for p in self._store.nodes(Person)):
            raise DomainRuleError("that email already has an account")
        return address

    # --- internals -----------------------------------------------------------

    def _usable_invite(self, code: str, now: datetime) -> Invite:
        try:
            invite = self._store.node(fingerprint(code.strip()), Invite)
        except NotFoundError:
            raise DomainRuleError(INVALID_INVITE) from None
        if not invite.is_open(now) or not self._store.has_node(invite.inviter_id):
            raise DomainRuleError(INVALID_INVITE)
        return invite

    def _own_invite(self, invite_id: str, by_person_id: str) -> Invite:
        invite = self._store.node(invite_id, Invite)
        if invite.inviter_id != by_person_id:
            raise PermissionDeniedError("only the person who sent this invite can do that")
        return invite

    def _open_invites(self, inviter_id: str, now: datetime) -> list[Invite]:
        return [
            i for i in self._store.nodes(Invite)
            if i.inviter_id == inviter_id and i.is_open(now)
        ]


def fingerprint(code: str) -> str:
    """The stored id for a code: its SHA-256 hex digest."""
    return hashlib.sha256(code.encode()).hexdigest()
