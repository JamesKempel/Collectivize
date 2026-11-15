"use strict";

// Shared by the Profile and Network pages (load after shared.js):
//   Collectivize.Profile.el              builds elements; text only ever goes in as text
//   Collectivize.Profile.ProfileRules    field limits and validation (same as the backend)
//   Collectivize.Profile.ProfileTheme    applies a person's colors, keeping text readable
//   Collectivize.Profile.ProfileRenderer draws a profile from the server's `profile` JSON
//
// A profile is a card (name, badge, bio, site) beside a column of sections.
// The person chooses which sections show and in what order (`sections`):
// about, top3, orgs, events. The network is not part of a profile: it has
// the Network page to itself (a "network" entry in `sections` is ignored).

(() => {
    // --- small DOM helper ------------------------------------------------------

    // Builds an element. Text always goes in through textContent, so profile
    // content can never inject markup.
    function el(tag, options = {}, children = []) {
        const node = document.createElement(tag);
        if (options.className) node.className = options.className;
        if (options.text != null) node.textContent = options.text;
        for (const [name, value] of Object.entries(options.attrs || {})) {
            if (value === true) node.setAttribute(name, "");
            else if (value !== false && value != null) node.setAttribute(name, value);
        }
        for (const child of children) if (child) node.append(child);
        return node;
    }

    // --- rules -----------------------------------------------------------------------

    // Field limits and validation, matching the backend proposal.
    class ProfileRules {
        static LIMITS = { display_name: 50, bio: 120, about: 1000, top3_title: 30, top3_item: 40 };
        static HEX = /^#[0-9a-f]{6}$/i;

        // Characters as people count them (an emoji is one).
        static length(text) {
            return Array.from(text).length;
        }

        // Errors by field key; empty when the draft is valid.
        static validate(draft) {
            const errors = {};
            const tooLong = (key, value, max) => {
                if (ProfileRules.length(value) > max) errors[key] = `Keep it to ${max} characters.`;
            };
            tooLong("display_name", draft.display_name, ProfileRules.LIMITS.display_name);
            if (!draft.display_name.trim()) errors.display_name = "Your name can't be empty.";
            tooLong("bio", draft.bio, ProfileRules.LIMITS.bio);
            tooLong("about", draft.about, ProfileRules.LIMITS.about);

            const items = draft.top3_items;
            const usingTop3 = draft.top3_title.trim() || items.some((item) => item.trim());
            tooLong("top3_title", draft.top3_title, ProfileRules.LIMITS.top3_title);
            if (usingTop3 && !draft.top3_title.trim()) errors.top3_title = "Give your Top 3 a title.";
            items.forEach((item, i) => {
                const key = `top3_${i}`;
                tooLong(key, item, ProfileRules.LIMITS.top3_item);
                if (usingTop3 && !item.trim()) errors[key] = "Fill in all three, or clear the Top 3.";
            });

            if (draft.website.trim() && !ProfileRules.domain(draft.website.trim())) {
                errors.website = "Use a full https:// address, like https://example.com.";
            }
            for (const key of ["background", "outline"]) {
                if (!ProfileRules.HEX.test(draft[key])) errors[key] = "Pick a color.";
            }
            return errors;
        }

        // The site's domain for display, or null unless it's a valid https URL.
        static domain(url) {
            try {
                const parsed = new URL(url);
                if (parsed.protocol !== "https:" || !parsed.hostname.includes(".")) return null;
                return parsed.hostname.replace(/^www\./, "");
            } catch {
                return null;
            }
        }

        // A valid draft as profile changes (trimmed, Top 3 null when empty).
        static toChanges(draft) {
            const title = draft.top3_title.trim();
            const items = draft.top3_items.map((item) => item.trim());
            return {
                display_name: draft.display_name.trim(),
                bio: draft.bio.trim(),
                about: draft.about.trim(),
                top3: title ? { title, items } : null,
                website: draft.website.trim() || null,
                colors: { background: draft.background.toUpperCase(), outline: draft.outline.toUpperCase() },
                background_picture: draft.background_picture || null,
                sections: draft.sections.filter((section) => section.shown).map((section) => section.key),
                profile_visibility: draft.profile_visibility,
                rsvp_visibility: draft.rsvp_visibility,
                hide_connections: draft.hide_connections,
            };
        }
    }

    // --- theme -------------------------------------------------------------------------

    // Applies a profile's colors to its area, picking dark or light text
    // (whichever contrasts more) so it stays readable on any background.
    class ProfileTheme {
        static DARK = "#202B29";
        static LIGHT = "#FDFDFB";

        static apply(element, colors) {
            element.style.setProperty("--p-bg", colors.background);
            element.style.setProperty("--p-line", colors.outline);
            element.style.setProperty("--p-ink", ProfileTheme.readableOn(colors.background));
            element.style.setProperty("--p-on-line", ProfileTheme.readableOn(colors.outline));
        }

        static readableOn(hex) {
            const dark = ProfileTheme.contrast(hex, ProfileTheme.DARK);
            const light = ProfileTheme.contrast(hex, ProfileTheme.LIGHT);
            return dark >= light ? ProfileTheme.DARK : ProfileTheme.LIGHT;
        }

        // True when the outline would be hard to see against the background.
        static outlineIsFaint(colors) {
            return ProfileTheme.contrast(colors.background, colors.outline) < 1.5;
        }

        // WCAG contrast ratio between two #RRGGBB colors (1 to 21).
        static contrast(a, b) {
            const [high, low] = [ProfileTheme.luminance(a), ProfileTheme.luminance(b)].sort((x, y) => y - x);
            return (high + 0.05) / (low + 0.05);
        }

        static luminance(hex) {
            const channels = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
            const [r, g, b] = channels.map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
            return 0.2126 * r + 0.7152 * g + 0.0722 * b;
        }
    }

    // --- rendering ---------------------------------------------------------------------

    const DATE_FORMAT = new Intl.DateTimeFormat("en-US", {
        weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
    });
    const SVG = "http://www.w3.org/2000/svg";
    // The profile's own sections. The network lives on the Network page only.
    const SECTION_LABELS = { about: "About", top3: "Top 3", orgs: "Orgs", events: "Events" };
    // Background pictures (key -> name). Same keys as BACKGROUND_PICTURES in
    // backend/objects/person.py; each is drawn by .p-cover-<key> in profile.css.
    const BACKGROUND_PICTURES = {
        sunset: "Sunset", ocean: "Ocean", forest: "Forest", lavender: "Lavender", sand: "Sand", night: "Night sky",
    };

    // Draws a profile. Used for the pages and for the editor's live preview.
    // mode: "self" (your own page), "visitor", or "preview" (inert visitor view).
    // slots.onConnection: called after Connect / Accept succeeds, to redraw.

    class ProfileRenderer {
        render(view, mode, slots = {}) {
            const surface = el("section", { className: "profile-surface", attrs: { "aria-label": "Profile" } });
            ProfileTheme.apply(surface, view.colors);
            // Their background picture: a banner across the top (profile.css .p-cover-*).
            if (BACKGROUND_PICTURES[view.background_picture]) {
                surface.classList.add("has-cover");
                surface.append(el("div", { className: `p-cover p-cover-${view.background_picture}`, attrs: { "aria-hidden": "true" } }));
            }
            if (view.access === "locked") {
                surface.classList.add("is-locked");
                surface.append(el("div", { className: "profile-grid" }, [
                    this.card(view, mode, true, slots),
                ]));
                return surface;
            }
            surface.append(el("div", { className: "profile-grid" }, [
                this.card(view, mode, false, slots),
                this.sections(view, mode, slots),
            ]));
            return surface;
        }

        static shownName(view) {
            return view.name || "Unnamed";
        }

        static initials(view) {
            return window.Collectivize.Ui.animal({ name: ProfileRenderer.shownName(view), avatar: view.avatar });
        }

        static textInitials(view) {
            const words = ProfileRenderer.shownName(view).trim().split(/\s+/);
            const letters = words.length > 1 ? words[0][0] + words[words.length - 1][0] : Array.from(words[0])[0];
            return (letters || "?").toUpperCase();
        }

        card(view, mode, locked, slots = {}) {
            const card = el("div", { className: "p-box p-card" }, [
                el("div", { className: "p-ring", attrs: { "aria-hidden": "true" } }, [
                    el("span", { text: ProfileRenderer.initials(view) }),
                ]),
                el("h1", { className: "p-name", text: ProfileRenderer.shownName(view) }),
                view.role ? el("p", { className: "p-username", text: `${view.role[0].toUpperCase()}${view.role.slice(1)}` }) : null,
                view.verified ? this.badge() : null,
            ]);
            if (locked) {
                card.append(el("p", { className: "p-locked-note", text: "This profile is visible to connections only." }));
            } else {
                if (view.bio) card.append(el("p", { className: "p-bio", text: view.bio }));
                const domain = view.website && ProfileRules.domain(view.website);
                if (domain) {
                    card.append(el("a", {
                        className: "p-button p-button-outline p-site",
                        attrs: { href: view.website, target: "_blank", rel: "noopener noreferrer nofollow" },
                    }, [el("span", { text: "Visit my site" }), el("span", { className: "p-site-domain", text: domain })]));
                }
            }
            if (mode !== "self") card.append(this.connectButton(view, mode, slots));
            if (mode !== "self" && view.in_common && !locked) {
                card.append(el("p", { className: "p-share" }, [
                    el("span", { className: "p-share-label", text: "You share" }),
                    el("span", { text: view.in_common }),
                ]));
            }
            return card;
        }

        badge() {
            const check = document.createElementNS(SVG, "svg");
            check.setAttribute("viewBox", "0 0 16 16");
            const stroke = document.createElementNS(SVG, "path");
            stroke.setAttribute("d", "m4 8.5 2.5 2.5L12 5.5");
            check.append(stroke);
            const icon = el("span", { className: "p-badge-icon", attrs: { "aria-hidden": "true" } }, [check]);
            return el("p", { className: "p-badge" }, [icon, el("span", { text: "Verified Northeastern" })]);
        }

        connectButton(view, mode, slots = {}) {
            const states = {
                none: ["Connect", true],
                pending_out: ["Request sent", false],
                pending_in: ["Accept connection", true],
                connected: ["Connected", false],
            };
            // Shows where you stand with this person; "Connect" sends a request
            // and "Accept connection" accepts theirs (POST /api/connect does both).
            const [label, active] = states[view.connection] || states.none;
            const live = active && mode !== "preview" && view.id;
            const button = el("button", {
                className: "p-button p-button-solid p-connect",
                text: label,
                attrs: { type: "button", disabled: !live, tabindex: mode === "preview" ? "-1" : null },
            });
            if (!live) return button;
            const problem = el("p", { className: "p-connect-error", attrs: { role: "alert", hidden: true } });
            button.addEventListener("click", async () => {
                button.disabled = true;
                problem.hidden = true;
                button.textContent = view.connection === "pending_in" ? "Accepting…" : "Sending…";
                try {
                    await window.Collectivize.Api.post("/api/connect", { person_id: view.id });
                    // The page redraws with the new state ("Request sent" or "Connected").
                    if (slots.onConnection) slots.onConnection();
                    else window.location.reload();
                } catch (error) {
                    // Put the button back so they can try again, and say why.
                    button.textContent = label;
                    button.disabled = false;
                    problem.textContent = error instanceof Error ? error.message : "That didn't send.";
                    problem.hidden = false;
                }
            });
            return el("div", { className: "p-connect-box" }, [button, problem]);
        }

        sections(view, mode, slots) {
            const own = mode === "self";
            const builders = {
                about: () => (view.about || own
                    ? this.section("About", view.about
                        ? el("p", { className: "p-about", text: view.about })
                        : this.empty("Add a few lines about yourself in Edit page."))
                    : null),
                top3: () => (view.top3
                    ? this.section(view.top3.title, el("ol", { className: "p-top3" },
                        view.top3.items.map((item) => el("li", { text: item }))))
                    : null),
                orgs: () => this.section("Orgs", view.orgs.length
                    ? el("ul", { className: "p-orgs" }, view.orgs.map((org) => el("li", { text: org.name })))
                    : this.empty(own ? "Orgs you join will show up here." : "No orgs to show.")),
                events: () => this.section("Events", el("div", { className: "p-events" }, [
                    this.eventList("Hosting", view.hosting),
                    this.eventList("Going", view.going),
                ])),
            };
            const order = Array.isArray(view.sections) ? view.sections : Object.keys(builders);
            const column = el("div", { className: "p-sections" });
            for (const key of order) {
                const built = builders[key]?.();
                if (built) column.append(built);
            }
            if (!column.children.length && own) {
                column.append(this.section("Your page is empty", this.empty("Turn sections on in Edit page.")));
            }
            return column;
        }

        section(title, body) {
            return el("section", { className: "p-box p-section" }, [el("h2", { className: "p-section-title", text: title }), body]);
        }

        eventList(title, events) {
            const group = el("div", { className: "p-event-group" }, [el("h3", { className: "p-event-heading", text: title })]);
            if (!events.length) {
                group.append(this.empty("Nothing coming up."));
                return group;
            }
            group.append(el("ul", { className: "p-event-list" }, events.map((event) => el("li", {
                className: event.is_cancelled ? "p-event is-cancelled" : "p-event",
            }, [
                el("span", { className: "p-event-date", text: DATE_FORMAT.format(new Date(event.starts_at)) }),
                el("span", { className: "p-event-title", text: event.title }),
                el("span", { className: "p-event-meta" }, [
                    event.host.name ? window.Collectivize.Ui.hostedBy(event.host.name, event.host.id, event.host.kind, "p-event-host") : null,
                    event.location ? el("span", { text: event.location }) : null,
                ]),
                event.is_cancelled ? el("span", { className: "p-event-tag", text: "Cancelled" }) : null,
            ]))));
            return group;
        }

        empty(text) {
            return el("p", { className: "p-empty", text });
        }
    }

    window.Collectivize = Object.freeze({
        ...window.Collectivize,
        Profile: Object.freeze({ el, ProfileRules, ProfileTheme, ProfileRenderer, SECTION_LABELS, BACKGROUND_PICTURES }),
    });
})();
