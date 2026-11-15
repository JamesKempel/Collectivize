"use strict";

// Network page (network_plan.md, "How the network view works").
//
// The network has this page to itself; profiles live on the Profile tab.
// The bubble fills the page, centred on one person or community at a time.
// You start on yourself. Clicking a connection in the bubble puts their
// network in the middle; clicking a community shows its members. Only
// nodes you can open are ever in a bubble (you, your connections, your
// communities); the server leaves the rest out.
//
// A slim header names who is in the middle and links to their profile (or
// the community's page). Someone you aren't connected to, or a community
// you aren't in: their network stays closed, and a short note says so.
//
// Built to keep working when things go wrong: an answer to an old request
// is ignored, broken entries are skipped, a page you may not open falls
// back to your own with a note, and server text is only inserted as text.

(() => {
    const { Session, NetworkData, NetworkBubble, Profile, ProfileEditor, Ui } = window.Collectivize;
    const { el } = Profile;
    const DEFAULT_BACKGROUND = "#F5F4F0"; // a profile nobody has recoloured (network-data.js)
    const OUTLINE_CONTRAST = 2; // how clearly a node's coloured outline must stand out on the map

    const $ = (id) => document.getElementById(id);

    const TOP = 3; // list entries shown before "More"

    const DATE_FORMAT = new Intl.DateTimeFormat(undefined, { weekday: "short", month: "short", day: "numeric" });

    const plural = (count, word, many = `${word}s`) => `${count} ${count === 1 ? word : many}`;

    const possessive = (name) => (name.endsWith("s") ? `${name}'` : `${name}'s`);

    const initials = (name) => name.split(/\s+/).filter(Boolean).slice(0, 2)
        .map((word) => word[0].toUpperCase()).join("");

    class NetworkPage {
        constructor() {
            this.viewer = "";
            this.centerId = NetworkPage.centerFromUrl();
            this.data = null;
            this.request = 0;
            this.colors = new Map(); // id -> outline colour for the map, kept while the page is open
            this.renderer = new Profile.ProfileRenderer(); // the side panel: the same profile as the Profile tab
            // Clicking yourself ("You"): on your own map it opens your Profile
            // tab; on someone else's it brings you back to your own network.
            // Clicking whoever is in the middle of their own network opens
            // their profile (a community: its page), just as clicking yourself
            // in the middle of yours opens your Profile tab.
            // Anyone or anything else is put in the middle of the map.
            this.bubble = new NetworkBubble({
                onOpen: (id) => {
                    const center = this.data?.center;
                    if (id && center && id === center.id && !this.data.isSelf) {
                        window.location.assign(center.isOrg ? Ui.orgHref(id) : Ui.profileHref(id));
                    } else if (id && id !== this.viewer) this.open(id);
                    else if (this.data && !this.data.isSelf) this.open("");
                    else window.location.assign("profile");
                },
            });

            $("nw-home").addEventListener("click", () => this.open(""));
            $("nw-retry").addEventListener("click", () => this.load());
            window.addEventListener("popstate", () => {
                this.centerId = NetworkPage.centerFromUrl();
                this.load();
            });
            this.start();
        }

        static centerFromUrl() {
            const value = new URLSearchParams(window.location.search).get("center") || "";
            return /^[\w-]{1,64}$/.test(value) ? value : "";
        }

        async start() {
            try {
                this.viewer = (await Session.current()).id; // whoever is signed in
                window.ConnectionsPanel?.mount($("nw-connections"), { onChange: () => this.load() });
            } catch (error) {
                this.fail(error);
                return;
            }
            this.load();
        }

        /** Put someone or some community in the middle ("" = you) and remember it in the URL. */
        open(centerId, { replace = false } = {}) {
            this.setCenter(centerId, replace);
            this.load();
        }

        setCenter(centerId, replace) {
            this.centerId = centerId === this.viewer ? "" : centerId;
            const url = new URL(window.location.href);
            if (this.centerId) url.searchParams.set("center", this.centerId);
            else url.searchParams.delete("center");
            window.history[replace ? "replaceState" : "pushState"]({}, "", url);
        }

        async load() {
            const request = ++this.request;
            $("nw-banner").hidden = true;
            this.note("");
            if (!this.viewer) {
                this.showEmpty("Sign in to see your network.");
                return;
            }
            $("nw-root").setAttribute("aria-busy", "true");
            try {
                const data = await this.fetchPage();
                if (request !== this.request) return; // a newer request took over
                this.data = data;
                this.render();
            } catch (error) {
                if (request === this.request) this.fail(error);
            } finally {
                if (request === this.request) $("nw-root").removeAttribute("aria-busy");
            }
        }

        async fetchPage() {
            if (!this.centerId) return NetworkData.fetch(this.viewer, "");
            try {
                return await NetworkData.fetch(this.viewer, this.centerId);
            } catch (error) {
                const own = await NetworkData.fetch(this.viewer, ""); // if this fails too, the banner explains
                this.setCenter("", true);
                const why = error.message.replace(/\.$/, "");
                this.note(`${why[0].toUpperCase()}${why.slice(1)}. Showing your own page instead.`);
                return own;
            }
        }

        fail(error) {
            $("nw-banner-text").textContent = error instanceof Error ? error.message : "The page didn't load.";
            $("nw-banner").hidden = false;
        }

        note(message) {
            $("nw-notice").textContent = message;
            $("nw-notice").hidden = !message;
        }

        showEmpty(message) {
            this.data = null;
            this.bubble.setExpanded(false);
            $("nw-root").replaceChildren();
            $("nw-empty").textContent = message;
            $("nw-empty").hidden = false;
            for (const id of ["nw-lists", "nw-home"]) $(id).hidden = true;
        }

        render() {
            const { data } = this;
            $("nw-empty").hidden = true;
            $("nw-home").hidden = data.isSelf;
            document.title = `${data.isSelf ? "My network" : data.center.name} · Collectivize`;
            if (data.networkOpen) {
                this.bubble.draw(data);
                this.paintNodes(data);
            } else {
                this.bubble.setExpanded(false); // no map to show full screen
            }
            // The map on the left; whoever is in the middle, in full, on the right.
            $("nw-root").replaceChildren(el("div", { className: "nw-split" }, [this.stage(), this.side()]));
            this.drawLists();
            if (data.truncated) this.note("This is a big network, so only part of it is shown.");
        }

        // --- node colours -------------------------------------------------------------

        /** A profile's background colour as a map outline. "" for the default
         *  background (nothing picked: the node keeps the house colour). A
         *  pale colour is darkened, same hue, just enough to show as a line
         *  on the map. */
        static outlineFrom(background) {
            const hex = /^#[0-9a-f]{6}$/i;
            if (!hex.test(background || "") || background.toUpperCase() === DEFAULT_BACKGROUND) return "";
            const css = getComputedStyle(document.body).getPropertyValue("--card").trim();
            const mapBg = hex.test(css) ? css : "#FBFAF7";
            // Lower the lightness only (hue and saturation stay), so a pale
            // mint becomes a clear mint green rather than a grey.
            const [h, s, l] = NetworkPage.toHsl(background);
            let color = background.toUpperCase();
            for (let light = l - 0.04; light > 0.1 && Profile.ProfileTheme.contrast(color, mapBg) < OUTLINE_CONTRAST; light -= 0.04) {
                color = NetworkPage.fromHsl(h, Math.max(s, 0.35), light);
            }
            return color;
        }

        static toHsl(hex) {
            const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
            const max = Math.max(r, g, b);
            const min = Math.min(r, g, b);
            const l = (max + min) / 2;
            if (max === min) return [0, 0, l];
            const d = max - min;
            const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
            const h = max === r ? (g - b) / d + (g < b ? 6 : 0) : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
            return [h / 6, s, l];
        }

        static fromHsl(h, s, l) {
            const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
            const p = 2 * l - q;
            const channel = (t) => {
                const u = (t + 1) % 1;
                if (u < 1 / 6) return p + (q - p) * 6 * u;
                if (u < 1 / 2) return q;
                if (u < 2 / 3) return p + (q - p) * (2 / 3 - u) * 6;
                return p;
            };
            return `#${[h + 1 / 3, h, h - 1 / 3].map((t) => Math.round(channel(t) * 255).toString(16).padStart(2, "0")).join("")}`.toUpperCase();
        }

        /** Each person and community on the map, outlined in the background
         *  colour of their own profile. The middle's colours come with the
         *  page; everyone else's are loaded (once each) from their profile.
         *  Communities have no colour of their own yet, so they keep the
         *  default until one exists. */
        async paintNodes(data) {
            const request = this.request;
            const center = data.profile?.colors?.background;
            if (center && !this.colors.has(data.center.id)) this.colors.set(data.center.id, NetworkPage.outlineFrom(center));
            const missing = data.people.map((p) => p.id)
                .filter((id) => !this.colors.has(id));
            this.bubble.paint(this.colors); // what's known already, straight away
            await Promise.all(missing.map(async (id) => {
                try {
                    const page = await NetworkData.fetch(this.viewer, id === this.viewer ? "" : id);
                    this.colors.set(id, NetworkPage.outlineFrom(page.profile?.colors?.background));
                } catch {
                    this.colors.set(id, ""); // can't read it: keep the default look
                }
            }));
            if (request === this.request) this.bubble.paint(this.colors);
        }

        // --- the network, filling the page --------------------------------------------

        stage() {
            const { center, isSelf, networkOpen } = this.data;
            const title = isSelf ? "My network"
                : center.isOrg ? `${center.name}: members you know` : `${possessive(center.name)} network`;
            // Your own network needs no heading (the page title says it).
            // Someone else's says whose it is; their page is beside the map.
            const head = isSelf ? null : el("div", { className: "nw-stage-head" }, [
                el("h2", { className: "nw-stage-title", text: title }),
            ]);
            const body = networkOpen ? this.bubble.element : el("p", {
                className: "nw-closed",
                text: center.isOrg
                    ? "You aren't a member, so its network of members isn't shown."
                    : `You and ${center.name.split(" ")[0]} aren't connected, so their network isn't shown.`,
            });
            return el("section", { className: "nw-stage", attrs: { "aria-label": title } }, [head, body]);
        }

        // --- the page of whoever is in the middle, beside the map ---------------------

        /** Their profile (a community: its details), so picking someone on
         *  the map shows them straight away, with no extra click. */
        side() {
            const { center, isSelf, profile } = this.data;
            const href = center.isOrg ? Ui.orgHref(center.id) : isSelf ? "profile" : Ui.profileHref(center.id);
            const label = center.isOrg ? "Open community page" : isSelf ? "Open my profile" : "Open full profile";
            const body = center.isOrg
                ? this.orgPanel(profile, center)
                : this.renderer.render(profile, isSelf ? "self" : "visitor", { onConnection: () => this.load() });
            const open = el("a", { className: "page-button nw-side-open", text: label, attrs: { href } });
            let actions = open;
            if (isSelf) {
                // Your own page: edit it right here, same editor as the Profile tab.
                const edit = el("button", { className: "page-button page-button-solid nw-side-open", text: "Edit page",
                                            attrs: { type: "button" } });
                edit.addEventListener("click", () => this.edit());
                actions = el("div", { className: "nw-side-actions" }, [edit, open]);
            }
            return el("aside", { className: "nw-side", attrs: { "aria-label": `About ${center.name}` } }, [body, actions]);
        }

        /** The profile editor (profile-editor.js) in the map's place; saving
            brings the map back with your new colours. */
        edit() {
            const viewer = this.viewer;
            this.bubble.setExpanded(false);
            this.request += 1; // an answer still on its way mustn't replace the editor
            document.title = "Edit profile · Collectivize";
            $("nw-lists").hidden = true;
            $("nw-home").hidden = true;
            new ProfileEditor({
                view: this.data.profile,
                renderer: this.renderer,
                save: (changes) => NetworkData.save(viewer, changes),
                onSaved: (data) => {
                    if (viewer !== this.viewer) return;
                    this.colors.delete(viewer); // repaint your node in its new colour
                    this.data = data;
                    this.render();
                },
                onCancel: () => this.render(),
            }).mount($("nw-root"));
            window.scrollTo({ top: 0 });
        }

        orgPanel(org, center) {
            const events = org.upcoming.slice(0, 5);
            return el("section", { className: "nw-org" }, [
                el("h2", { className: "nw-org-name", text: center.name }),
                el("p", { className: "nw-org-kind", text: org.isMember ? `${org.orgKind} · You're a member` : org.orgKind }),
                org.website ? el("a", { className: "nw-org-site", text: "Website",
                                        attrs: { href: org.website, target: "_blank", rel: "noopener noreferrer nofollow" } }) : null,
                el("h3", { className: "nw-org-heading", text: `Coming up (${org.upcomingCount})` }),
                events.length
                    ? el("ul", { className: "nw-org-events" }, events.map((event) => el("li", { className: "nw-org-event" }, [
                        el("span", { className: "nw-org-date", text: DATE_FORMAT.format(new Date(event.starts_at)) }),
                        el("span", { className: "nw-org-title", text: event.title }),
                        event.location ? el("span", { className: "nw-org-where", text: event.location }) : null,
                    ])))
                    : el("p", { className: "nw-org-empty", text: "Nothing coming up." }),
            ]);
        }

        // --- the lists under the page ------------------------------------------------

        drawLists() {
            const { data } = this;
            const others = data.people.filter((p) => !p.isYou);

            $("nw-shared-title").textContent = data.isSelf ? "My communities" : "Communities you share";
            this.topThree("nw-shared-list", NetworkPage.closestFirst(data.orgs), (org) => this.row(
                "nw-badge", org, "You're a member", `Open the page of ${org.name}`));
            $("nw-shared").hidden = data.orgs.length === 0;

            $("nw-people-title").textContent = data.isSelf ? "My connections"
                : data.center.isOrg ? "Members you're connected to" : "Connections you share";
            this.topThree("nw-people-list", NetworkPage.closestFirst(others), (person) => {
                const linked = data.links.filter((pair) => pair.includes(person.id)).length;
                return this.row("nw-avatar", person,
                    linked ? `Connected to ${plural(linked, "other")} here` : "Your connection",
                    `Open ${possessive(person.name)} page`);
            });
            $("nw-people").hidden = others.length === 0;
            $("nw-lists").hidden = data.orgs.length === 0 && others.length === 0;
        }

        /** The top three, then "More" to show the rest (and "Less" to fold them again). */
        topThree(listId, items, toRow) {
            const list = $(listId);
            const rows = items.map(toRow);
            rows.slice(TOP).forEach((row) => { row.hidden = true; });
            list.replaceChildren(...rows);
            list.parentElement.querySelector(".nw-more")?.remove();
            if (rows.length <= TOP) return;
            const more = el("button", { className: "nw-link-button nw-more", text: "More",
                                        attrs: { type: "button", "aria-expanded": "false", "aria-controls": listId } });
            more.addEventListener("click", () => {
                const open = more.getAttribute("aria-expanded") !== "true";
                rows.slice(TOP).forEach((row) => { row.hidden = !open; });
                more.setAttribute("aria-expanded", String(open));
                more.textContent = open ? "Less" : "More";
            });
            list.after(more);
        }

        /** Closest first (the map's own closeness score), keeping the server's order on ties. */
        static closestFirst(items) {
            return items.map((item, index) => ({ item, index }))
                .sort((a, b) => (b.item.closeness ?? 0) - (a.item.closeness ?? 0) || a.index - b.index)
                .map(({ item }) => item);
        }

        row(markClass, node, about, label) {
            const open = el("button", { className: "nw-open", text: "Open", attrs: { type: "button", "aria-label": label } });
            open.addEventListener("click", () => {
                this.open(node.id);
                window.scrollTo({ top: 0 });
            });
            return el("li", { className: "nw-item nw-row" }, [
                el("span", { className: markClass, text: markClass === "nw-avatar" ? Ui.animal(node) : initials(node.name) }),
                el("span", { className: "nw-row-text" }, [
                    el("span", { className: "nw-item-name", text: node.name }),
                    el("span", { className: "nw-item-sub", text: about }),
                ]),
                open,
            ]);
        }
    }

    new NetworkPage();
})();
