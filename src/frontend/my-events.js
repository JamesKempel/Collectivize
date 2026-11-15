"use strict";

// My Events (v1.1 spec 4.6 and 4.7): everything you've planned, as a
// calendar (calendar.js) or a list. The list has Going, Maybe, Saved and
// Hosting tabs, upcoming first, past events folded away, and a search bar
// that works like Discover's (GET /api/find with scope=mine), so typing
// "robotics this week" reads the same way it does there. Events you host
// get only "Add to calendar": you're going to your own event.
// Changing a plan here updates it everywhere, calendar included, because
// it all comes from the same server state.
// The view, tab and search live in the URL (?view=&tab=&q=).

(() => {
    const { Api, EventActions, Ui } = window.Collectivize;
    const { el, cleanName } = Ui;
    const $ = (id) => document.getElementById(id);
    const DATE = new Intl.DateTimeFormat(undefined, { weekday: "short", month: "short", day: "numeric" });
    const TIME = new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" });
    const DAY = new Intl.DateTimeFormat(undefined, { weekday: "short", month: "short", day: "numeric" });
    const VIEWS = ["calendar", "list"];
    // An event you host is listed only under Hosting.
    const TABS = {
        going: { match: (e) => !e.hosting && e.rsvp === "going", empty: "You're not going to anything yet. Find something on Discover." },
        maybe: { match: (e) => !e.hosting && e.rsvp === "maybe", empty: "Nothing marked maybe." },
        saved: { match: (e) => !e.hosting && e.saved, empty: "Nothing saved. Tap the bookmark on any event to save it." },
        hosting: { match: (e) => e.hosting, empty: "You're not hosting anything." },
    };
    const MAX_SEARCH_PAGES = 20; // 200 results is more than anyone plans

    const params = new URLSearchParams(location.search);
    let view = VIEWS.includes(params.get("view")) ? params.get("view") : "calendar";
    let tab = params.get("tab") in TABS ? params.get("tab") : "going";
    let query = (params.get("q") || "").trim();
    let data = { upcoming: [], past: [] };
    let found = null; // ids in search order while searching, else null
    let request = 0;

    // --- view switch -----------------------------------------------------------------

    for (const button of document.querySelectorAll(".me-view")) {
        button.addEventListener("click", () => showView(button.dataset.view));
    }

    function showView(name) {
        const changed = name !== view;
        view = name;
        writeUrl();
        for (const button of document.querySelectorAll(".me-view")) {
            button.setAttribute("aria-pressed", String(button.dataset.view === view));
        }
        $("page").dataset.view = view;
        $("view-calendar").hidden = view !== "calendar";
        $("view-list").hidden = view !== "list";
        // Plans may have changed in the other view.
        if (changed && view === "calendar") window.MyCalendar?.load();
        if (changed && view === "list") load();
    }

    function writeUrl() {
        const url = new URL(location.href);
        url.searchParams.set("view", view);
        url.searchParams.set("tab", tab);
        if (query) url.searchParams.set("q", query);
        else url.searchParams.delete("q");
        history.replaceState(null, "", url);
    }

    // --- tabs ------------------------------------------------------------------------

    for (const button of document.querySelectorAll(".tab")) {
        button.addEventListener("click", () => select(button.dataset.tab));
        button.addEventListener("keydown", (event) => {
            const order = Object.keys(TABS);
            const step = { ArrowRight: 1, ArrowLeft: -1 }[event.key];
            if (!step) return;
            const next = order[(order.indexOf(tab) + step + order.length) % order.length];
            select(next);
            $(`tab-${next}`).focus();
        });
    }

    function select(name) {
        tab = name;
        writeUrl();
        render();
    }

    // --- search ----------------------------------------------------------------------

    $("me-search").addEventListener("submit", (event) => {
        event.preventDefault();
        query = $("me-search-input").value.trim();
        writeUrl();
        search();
    });

    // Clearing the box (its × button, or deleting the text) shows everything again.
    $("me-search-input").addEventListener("input", () => {
        if ($("me-search-input").value.trim() || !query) return;
        query = "";
        writeUrl();
        search();
    });

    /** Discover's search over your own events: every page, in its order. */
    async function search() {
        const id = ++request;
        if (!query) {
            found = null;
            $("me-understood").hidden = true;
            setStatus("");
            render();
            return;
        }
        setStatus("Searching…");
        try {
            const ids = [];
            let first = null;
            for (let page = 1; page <= MAX_SEARCH_PAGES; page += 1) {
                const result = await Api.get("/api/find", { q: query, scope: "mine", page });
                if (id !== request) return; // a newer search has started
                first ??= result;
                ids.push(...result.items.filter((item) => item.type === "event").map((item) => item.id));
                if (page >= result.pages) break;
            }
            found = ids;
            showUnderstood(first);
            setStatus("");
        } catch (error) {
            if (id !== request) return;
            found = null;
            $("me-understood").hidden = true;
            setStatus(error.message, { error: true });
        }
        render();
    }

    /** "Searching for: robotics · Sat, Nov 21", from what the server read. */
    function showUnderstood(result) {
        const line = $("me-understood");
        const parts = [...(result?.understood?.keywords || [])];
        if (result?.filters?.date) {
            const days = [result.filters.date, result.filters.date_end].filter(Boolean);
            parts.push(days.map((day) => DAY.format(new Date(`${day}T12:00:00`))).join(" – "));
        }
        const children = [el("span", { className: "me-understood-label", text: "Searching for: " }),
                          document.createTextNode(parts.join(" · ") || query)];
        if (result?.understood?.note) {
            children.push(el("span", { className: "me-understood-note", text: ` ${result.understood.note}` }));
        }
        children.push(el("span", { className: "me-understood-note", text: " Past events aren't searched." }));
        line.replaceChildren(...children);
        line.hidden = false;
    }

    // --- loading and drawing -----------------------------------------------------------

    async function load() {
        try {
            data = await Api.get("/api/my-events");
            render();
        } catch (error) {
            setStatus(error.message, { error: true });
        }
    }

    /** What the list shows: everything, or only search matches in search order. */
    function shown(events) {
        if (found === null) return events;
        const byId = new Map(events.map((e) => [e.id, e]));
        return found.map((id) => byId.get(id)).filter(Boolean);
    }

    function render() {
        const upcomingAll = shown(data.upcoming);
        for (const button of document.querySelectorAll(".tab")) {
            const name = button.dataset.tab;
            const selected = name === tab;
            button.setAttribute("aria-selected", String(selected));
            button.tabIndex = selected ? 0 : -1;
            button.querySelector(".tab-count").textContent = String(upcomingAll.filter(TABS[name].match).length);
        }
        $("panel").setAttribute("aria-labelledby", `tab-${tab}`);
        const upcoming = upcomingAll.filter(TABS[tab].match);
        const past = found === null ? data.past.filter(TABS[tab].match) : [];
        $("upcoming").replaceChildren(...upcoming.map((e) => row(e, false)));
        $("upcoming-empty").hidden = upcoming.length > 0;
        $("upcoming-empty").textContent = found === null ? TABS[tab].empty : "None of these match your search.";
        $("past-box").hidden = past.length === 0;
        $("past-summary").textContent = `Past events (${past.length})`;
        $("past").replaceChildren(...past.map((e) => row(e, true)));
    }

    function row(event, isPast) {
        const start = new Date(event.starts_at);
        const notes = [];
        if (event.is_cancelled) notes.push("Cancelled");
        else if (event.is_full) notes.push("Full");
        const meta = [...notes, `${DATE.format(start)}, ${TIME.format(start)}`, event.location]
            .filter(Boolean).join(" · ");
        const parts = [
            el("div", { className: "me-date", attrs: { "aria-hidden": "true" } }, [
                el("span", { text: start.toLocaleDateString(undefined, { month: "short" }) }),
                el("strong", { text: String(start.getDate()) }),
            ]),
            el("div", { className: "list-main" }, [
                el("p", { className: "list-title", text: event.title }),
                el("p", { className: "list-meta", text: meta }),
                event.host ? Ui.hostedBy(event.host, event.host_id, event.host_kind, "me-host") : null,
            ]),
        ];
        if (!isPast) {
            const actions = el("div", { className: "me-actions" });
            if (!event.hosting) {
                const controls = new EventActions({
                    eventId: event.id,
                    myRsvp: event.rsvp === "going" ? "going" : event.rsvp === "maybe" ? "interested" : null,
                    starred: event.saved,
                    cancelled: event.is_cancelled,
                    onChange: () => load(), // it may leave this tab
                    onError: (message) => setStatus(message, { error: true }),
                });
                actions.append(controls.element);
            }
            if (window.AddToCalendar && !event.is_cancelled) actions.append(window.AddToCalendar.menu(event));
            if (actions.childElementCount) parts.push(actions);
        }
        return el("li", { className: `list-item me-item${event.is_cancelled ? " is-cancelled" : ""}` }, parts);
    }

    function setStatus(text, { error = false } = {}) {
        $("status").textContent = text;
        $("status").classList.toggle("is-error", error);
    }

    $("me-search-input").value = query;
    showView(view);
    select(tab);
    load().then(() => { if (query) search(); });
})();
