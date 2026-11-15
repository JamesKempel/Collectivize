"use strict";

// Loading a profile and its network for the Profile and Network pages
// (load after shared.js):
//   Collectivize.NetworkData.fetch(viewer, center)   GET /api/network, checked
//   Collectivize.NetworkData.save(viewer, changes)   POST /api/profile, checked
//   Collectivize.NetworkData.read(raw)               check and normalize an answer
//
// Nothing from the server is trusted: every field is checked and given a
// safe default, colors must be #RRGGBB, links must be http(s), and entries
// that can't be shown are skipped. Returns null if the answer is unusable.

(() => {
    const { Api } = window.Collectivize;

    const HEX = /^#[0-9a-f]{6}$/i;
    const DEFAULT_COLORS = { background: "#F5F4F0", outline: "#202B29" };
    const SECTIONS = ["about", "top3", "network", "orgs", "events"];
    const AUDIENCES = ["network", "connections", "private"];
    const CONNECTIONS = ["self", "connected", "pending_out", "pending_in", "none"];
    const ORG_KINDS = {
        chapter: "Chapter", national: "National organization", council: "Council",
        club: "Club", institution: "Institution",
    };

    const text = (value) => (typeof value === "string" ? value.trim() : "");

    const list = (value) => (Array.isArray(value) ? value : []);

    const named = (item) => item && typeof item === "object"
        && typeof item.id === "string" && typeof item.name === "string" && item.name.trim();

    /** A web address we're willing to link to, or null. */
    function link(value, { httpsOnly = false } = {}) {
        try {
            const url = new URL(text(value));
            const ok = url.protocol === "https:" || (!httpsOnly && url.protocol === "http:");
            return ok ? url.href : null;
        } catch {
            return null;
        }
    }

    function readEvent(raw) {
        if (!raw || typeof raw !== "object" || !text(raw.title)) return null;
        if (Number.isNaN(new Date(raw.starts_at).getTime())) return null;
        return {
            id: text(raw.id),
            title: text(raw.title),
            starts_at: raw.starts_at,
            location: text(raw.location),
            host: { name: text(raw.host?.name), kind: raw.host?.kind === "person" ? "person" : "org",
                    id: typeof raw.host?.id === "string" ? raw.host.id : null },
            is_cancelled: raw.is_cancelled === true,
        };
    }

    function readPerson(raw, name, id) {
        const colors = raw.colors && typeof raw.colors === "object" ? raw.colors : {};
        const top3 = raw.top3 && typeof raw.top3 === "object" && text(raw.top3.title)
            && list(raw.top3.items).length === 3 && raw.top3.items.every((item) => text(item))
            ? { title: text(raw.top3.title), items: raw.top3.items.map(text) } : null;
        const settings = raw.settings && typeof raw.settings === "object" ? {
            profile_visibility: AUDIENCES.includes(raw.settings.profile_visibility) ? raw.settings.profile_visibility : "network",
            rsvp_visibility: AUDIENCES.includes(raw.settings.rsvp_visibility) ? raw.settings.rsvp_visibility : "connections",
            hide_connections: raw.settings.hide_connections === true,
        } : null;
        return {
            kind: "person",
            id, // needed to send them a connection request
            name,
            avatar: text(raw.avatar) || null,
            role: text(raw.role),
            verified: raw.verified === true,
            colors: {
                background: HEX.test(colors.background) ? colors.background : DEFAULT_COLORS.background,
                outline: HEX.test(colors.outline) ? colors.outline : DEFAULT_COLORS.outline,
            },
            // A preset key (profile-render.js BACKGROUND_PICTURES); unknown ones are ignored there.
            background_picture: typeof raw.background_picture === "string" && /^[a-z]{1,20}$/.test(raw.background_picture)
                ? raw.background_picture : null,
            access: raw.access === "locked" ? "locked" : "full",
            connection: CONNECTIONS.includes(raw.connection) ? raw.connection : "none",
            is_self: raw.is_self === true,
            in_common: text(raw.in_common) || null,
            bio: text(raw.bio),
            about: text(raw.about),
            top3,
            website: link(raw.website, { httpsOnly: true }),
            sections: Array.isArray(raw.sections)
                ? [...new Set(raw.sections.filter((key) => SECTIONS.includes(key)))] : SECTIONS,
            orgs: list(raw.orgs).filter(named).map((org) => ({ id: org.id, name: org.name })),
            hosting: list(raw.hosting).map(readEvent).filter(Boolean),
            going: list(raw.going).map(readEvent).filter(Boolean),
            settings,
        };
    }

    function readOrg(raw, name) {
        const upcoming = list(raw.upcoming).map(readEvent).filter(Boolean);
        return {
            kind: "org",
            name,
            isMember: raw.is_member === true,
            orgKind: ORG_KINDS[raw.org_kind] || "Community",
            website: link(raw.website),
            upcoming,
            upcomingCount: Number.isInteger(raw.upcoming_count) ? raw.upcoming_count : upcoming.length,
        };
    }

    /** The server's answer, checked and normalized; null if it can't be shown. */
    function read(raw) {
        if (!raw || !named(raw.center) || !Array.isArray(raw.orgs) || !Array.isArray(raw.people)) return null;
        const closeness = (item) => (Number.isInteger(item.closeness) && item.closeness > 0 ? item.closeness : 0);
        const people = raw.people.filter(named).map((person) => ({
            id: person.id, name: person.name, avatar: text(person.avatar) || null, isYou: person.is_you === true, closeness: closeness(person),
        }));
        const ids = new Set(people.map((person) => person.id));
        const pairs = (value) => list(value).filter((pair) => Array.isArray(pair)
            && pair.length === 2 && pair[0] !== pair[1] && ids.has(pair[0]) && ids.has(pair[1]));
        const orgs = raw.orgs.filter(named).map((org) => ({ id: org.id, name: org.name, closeness: closeness(org) }));
        const orgIds = new Set(orgs.map((org) => org.id));
        const isOrg = raw.center.kind === "org";
        const profile = raw.profile && typeof raw.profile === "object" ? raw.profile : {};
        return {
            center: { id: raw.center.id, name: raw.center.name, avatar: text(raw.center.avatar) || null, isOrg },
            isSelf: raw.is_self === true,
            orgs,
            people,
            links: pairs(raw.links), // accepted connections between people shown
            near: pairs(raw.near), // not connected, but close in the network
            // [person, org]: which people shown belong to which communities shown
            memberships: list(raw.memberships).filter((pair) => Array.isArray(pair)
                && pair.length === 2 && ids.has(pair[0]) && orgIds.has(pair[1])),
            truncated: raw.truncated === true,
            // False for someone you aren't connected to, or an org you aren't in:
            // you can read their page, but their network stays closed.
            networkOpen: raw.network_open !== false,
            profile: isOrg ? readOrg(profile, raw.center.name) : readPerson(profile, raw.center.name, raw.center.id),
        };
    }

    function checked(raw) {
        const data = read(raw);
        if (!data) throw new Error("The page didn't load properly.");
        return data;
    }

    const NetworkData = Object.freeze({
        read,
        fetch: async (viewer, center) => checked(await Api.get("/api/network", { viewer, center })),
        save: async (viewer, changes) => checked(await Api.post("/api/profile", { viewer, ...changes })),
    });

    window.Collectivize = Object.freeze({ ...window.Collectivize, NetworkData });
})();
