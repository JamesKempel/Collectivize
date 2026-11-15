"use strict";

// Organization page: what it is, who's in it, what it hosts. Member lists
// follow the visibility rules on the server (members see everyone;
// others see the count and the members they're connected to). Org admins
// can edit the page and add or remove members (v1.1 spec 4.9).

(() => {
    const { Api, Ui } = window.Collectivize;
    const { el, cleanName } = Ui;
    const root = document.getElementById("org");
    const DATE = new Intl.DateTimeFormat(undefined, { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
    const KIND = { chapter: "Chapter", national: "National organization", council: "Council", club: "Club", institution: "Institution" };

    const TOP = 3; // members shown at first
    const EXPANDED = 10; // after "Show more"; past that, search
    const VIEWS = ["list", "calendar"];

    const params = new URLSearchParams(location.search);
    const id = params.get("id") || "";
    let org = null;
    let membersOpen = false; // "Show more" pressed
    let memberQuery = ""; // the members search box
    let view = VIEWS.includes(params.get("view")) ? params.get("view") : "list";

    // The events calendar (calendar.js, loaded after this file) shows this
    // org's upcoming events instead of your own plans.
    let orgLoaded;
    const orgReady = new Promise((resolve, reject) => { orgLoaded = { resolve, reject }; });
    window.CalendarSource = async () => ({ entries: (await orgReady).events });

    async function load() {
        try {
            org = await Api.get("/api/org", { id });
            orgLoaded.resolve(org);
            render();
        } catch (error) {
            orgLoaded.reject(error);
            root.replaceChildren(el("p", { className: "status is-error", text: error.message }));
        }
    }

    function render() {
        document.title = `${cleanName(org.name)} · Collectivize`;
        const status = el("p", { className: "status", attrs: { role: "status", "aria-live": "polite" } });
        const meta = [KIND[org.kind] || org.kind, ...org.tags].join(" · ");
        const header = [
            ...[websiteBox()].filter(Boolean),
            el("h1", { className: "page-title", text: cleanName(org.name) }),
            el("p", { className: "page-subtitle", text: meta }),
        ];
        if (org.is_member) header.push(el("p", {}, [el("span", { className: "pill pill-green", text: org.can_manage ? "You're an admin" : "You're a member" })]));
        root.replaceChildren(...header, status, members(status), events(), ...(org.can_manage ? [editor(status)] : []));
    }

    /** An http(s) address we're willing to link to, or null. */
    function safeLink(value) {
        try {
            const url = new URL(String(value || ""));
            return url.protocol === "https:" || url.protocol === "http:" ? url : null;
        } catch {
            return null;
        }
    }

    /** The box at the very top: the org's website, opened in a new tab.
        Admins of an org without one get a box that takes them to the editor. */
    function websiteBox() {
        const url = safeLink(org.website_url);
        if (url) {
            return el("a", { className: "org-site", attrs: {
                href: url.href, target: "_blank", rel: "noopener noreferrer nofollow",
                "aria-label": `Visit the ${cleanName(org.name)} website (opens in a new tab)`,
            } }, [
                el("span", { className: "org-site-icon", text: "🌐", attrs: { "aria-hidden": "true" } }),
                el("span", { className: "org-site-text" }, [
                    el("span", { className: "org-site-label", text: "Website" }),
                    el("span", { className: "org-site-url", text: url.host.replace(/^www\./, "") + url.pathname.replace(/\/$/, "") }),
                ]),
                el("span", { className: "org-site-go", text: "Visit ↗", attrs: { "aria-hidden": "true" } }),
            ]);
        }
        if (!org.can_manage) return null;
        const add = el("button", { className: "org-site is-empty", attrs: { type: "button" } }, [
            el("span", { className: "org-site-icon", text: "🌐", attrs: { "aria-hidden": "true" } }),
            el("span", { className: "org-site-text" }, [
                el("span", { className: "org-site-label", text: "Website" }),
                el("span", { className: "org-site-url", text: "Add a link to your website" }),
            ]),
            el("span", { className: "org-site-go", text: "Add +", attrs: { "aria-hidden": "true" } }),
        ]);
        add.addEventListener("click", () => {
            const input = document.getElementById("org-website");
            input?.scrollIntoView({ behavior: "smooth", block: "center" });
            input?.focus({ preventScroll: true });
        });
        return add;
    }

    /** The top three, "Show more" for up to ten, and a search over everyone
        you can see, so a 200-person chapter never takes over the page. */
    function members(status) {
        const n = org.member_count;
        const note = org.members_complete ? "" : org.members.length
            ? ` · showing the ${org.members.length} you're connected to`
            : " · you aren't connected to any of them yet";
        const many = org.members.length > TOP;
        const list = el("ul", { className: "list" });
        const more = el("button", { className: "link-button org-more", attrs: { type: "button", "aria-controls": "org-members" } });
        const hint = el("p", { className: "muted org-hint", attrs: { "aria-live": "polite" } });
        list.id = "org-members";

        const search = el("input", { className: "input org-search", attrs: {
            type: "search", placeholder: `Search ${org.members.length} members`, maxlength: "100",
            "aria-label": "Search members", autocomplete: "off", value: memberQuery,
        } });
        search.addEventListener("input", () => {
            memberQuery = search.value;
            draw();
        });
        more.addEventListener("click", () => {
            membersOpen = !membersOpen;
            draw();
        });

        function draw() {
            const query = memberQuery.trim().toLowerCase();
            const matches = query
                ? org.members.filter((m) => cleanName(m.name).toLowerCase().includes(query))
                : org.members;
            const limit = query || membersOpen ? EXPANDED : TOP;
            list.replaceChildren(...matches.slice(0, limit).map((m) => memberRow(m, status)));

            more.hidden = Boolean(query) || !many;
            more.textContent = membersOpen ? "Show fewer" : `Show ${Math.min(org.members.length, EXPANDED) - TOP} more`;
            more.setAttribute("aria-expanded", String(membersOpen));

            // Folded, "Show N more" says it all; past ten, point to the search.
            hint.textContent = query && !matches.length ? `No members match “${memberQuery.trim()}”.`
                : query && matches.length > limit ? `Showing ${limit} of ${matches.length} matches. Keep typing to narrow it down.`
                    : !query && membersOpen && matches.length > limit ? `Showing ${limit} of ${matches.length}. Search to find anyone else.`
                        : "";
            hint.hidden = !hint.textContent;
        }
        draw();

        return el("section", { className: "panel", attrs: { "aria-labelledby": "members-title" } }, [
            el("h2", { className: "panel-title", text: `${n} member${n === 1 ? "" : "s"}${note}`, attrs: { id: "members-title" } }),
            ...(many ? [search] : []),
            list,
            more,
            hint,
            ...(org.can_manage ? [addForm(status)] : []),
        ]);
    }

    function memberRow(member, status) {
        const children = [
            Ui.avatar(member),
            el("div", { className: "list-main" }, [
                el("p", { className: "list-title" }, [el("a", { text: cleanName(member.name), attrs: { href: Ui.profileHref(member.id) } })]),
                ...(member.admin ? [el("p", { className: "list-meta", text: "Admin" })] : []),
            ]),
        ];
        if (org.can_manage) {
            const remove = el("button", { className: "button button-danger", text: "Remove", attrs: { type: "button" } });
            remove.addEventListener("click", () => change({ action: "remove", person_id: member.id }, status, remove));
            children.push(remove);
        }
        return el("li", { className: "list-item" }, children);
    }

    function addForm(status) {
        const input = el("input", { className: "input", attrs: { type: "email", placeholder: "Their Northeastern email", maxlength: "254", "aria-label": "Add a member by email" } });
        const button = el("button", { className: "button button-solid", text: "Add member", attrs: { type: "submit" } });
        const form = el("form", { className: "row", attrs: { style: "margin-top:12px" } }, [input, button]);
        form.addEventListener("submit", (event) => {
            event.preventDefault();
            if (input.value.trim()) change({ action: "add", email: input.value.trim() }, status, button);
        });
        return form;
    }

    async function change(body, status, button) {
        button.disabled = true;
        try {
            org = await Api.post("/api/org/members", { org_id: org.id, ...body });
            render();
        } catch (error) {
            status.textContent = error.message;
            status.classList.add("is-error");
            button.disabled = false;
        }
    }

    /** Upcoming events as a list or a calendar, switched like My Events. */
    function events() {
        const list = org.events.length
            ? el("ul", { className: "list" }, org.events.map((e) => el("li", { className: "list-item" }, [
                el("div", { className: "list-main" }, [
                    el("p", { className: "list-title", text: e.title }),
                    el("p", { className: "list-meta", text: [DATE.format(new Date(e.starts_at)), e.location, e.is_cancelled ? "Cancelled" : ""].filter(Boolean).join(" · ") }),
                ]),
            ])))
            : el("p", { className: "muted", text: "Nothing coming up." });
        const calendar = document.getElementById("view-calendar");
        const body = el("div");

        const buttons = VIEWS.map((name) => {
            const button = el("button", { className: "cal-view", text: name === "list" ? "List" : "Calendar",
                                          attrs: { type: "button", "data-view": name } });
            button.addEventListener("click", () => show(name));
            return button;
        });

        function show(name) {
            const changed = name !== view;
            view = name;
            for (const button of buttons) button.setAttribute("aria-pressed", String(button.dataset.view === view));
            body.replaceChildren(view === "calendar" ? calendar : list);
            const url = new URL(location.href);
            url.searchParams.set("view", view);
            history.replaceState(null, "", url);
            if (changed && view === "calendar") window.MyCalendar?.render(); // it was drawn while hidden
        }
        show(view);

        return el("section", { className: "panel" }, [
            el("div", { className: "panel-head" }, [
                el("h2", { className: "panel-title", text: "Upcoming events" }),
                el("div", { className: "cal-views", attrs: { role: "group", "aria-label": "Show as" } }, buttons),
            ]),
            body,
        ]);
    }

    function editor(status) {
        const name = el("input", { className: "input", attrs: { value: org.name, maxlength: "80", "aria-label": "Name" } });
        const site = el("input", { className: "input", attrs: { value: org.website_url || "", type: "url", placeholder: "https://…", "aria-label": "Website" } });
        site.id = "org-website";
        const save = el("button", { className: "button button-solid", text: "Save", attrs: { type: "submit" } });
        const form = el("form", {}, [
            el("label", { className: "row", attrs: { style: "margin-bottom:8px" } }, [el("span", { text: "Name", attrs: { style: "width:70px" } }), name]),
            el("label", { className: "row", attrs: { style: "margin-bottom:8px" } }, [el("span", { text: "Website", attrs: { style: "width:70px" } }), site]),
            save,
        ]);
        form.addEventListener("submit", async (event) => {
            event.preventDefault();
            save.disabled = true;
            try {
                org = await Api.post("/api/org", { id: org.id, name: name.value, website_url: site.value || null });
                render();
            } catch (error) {
                status.textContent = error.message;
                status.classList.add("is-error");
                save.disabled = false;
            }
        });
        return el("section", { className: "panel" }, [el("h2", { className: "panel-title", text: "Edit this page (admins)" }), form]);
    }

    load();
})();
