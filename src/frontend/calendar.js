"use strict";

// My Events' calendar view (v1.1 spec 4.7): your personal calendar, not a
// master calendar. A month grid, or a week or day of hours, with a day
// panel, showing only what you host, are going to, said maybe to or saved,
// plus your organizations' events, colour-coded by status. Discovery
// happens on Discover: the day panel links there with that day already set
// ("Find events on …"). The day panel has the same "I'm going" / "Maybe" /
// save buttons as Discover (events you host get only "Add to calendar");
// changing them updates the calendar straight away.
// The view and day live in the URL (?cal=month|week|day&date=YYYY-MM-DD).
//
// Built to keep working when things go wrong: if events can't load, the
// grid still works and a banner offers Retry; an answer to an old request
// is ignored; events with broken dates are skipped; long event lists are
// trimmed with "+N more"; server text is only ever inserted as text.

(() => {
    const { Api, EventActions } = window.Collectivize;

    const MONTH_FORMAT = new Intl.DateTimeFormat("en-US", { month: "long", year: "numeric" });
    const DAY_FORMAT = new Intl.DateTimeFormat("en-US", { month: "long", day: "numeric" });
    const WEEKDAY_FORMAT = new Intl.DateTimeFormat("en-US", { weekday: "long" });
    const FULL_FORMAT = new Intl.DateTimeFormat("en-US", { dateStyle: "full" });
    const SHORT_FORMAT = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" });
    const HOUR_FORMAT = new Intl.DateTimeFormat("en-US", { hour: "numeric" });
    const TIME_FORMAT = new Intl.DateTimeFormat("en-US", { hour: "numeric", minute: "2-digit" });

    const GRID_DAYS = 42; // six weeks, so the grid keeps its height
    const CHIPS_PER_CELL = 3;
    const MAX_SPAN_DAYS = 14; // a multi-day event is shown on at most this many days
    const HOUR_PX = 48; // height of one hour in the week and day views
    const MIN_BLOCK_PX = 22; // short events stay tall enough to read
    const FIRST_HOUR_SHOWN = 8; // the week and day views open scrolled to 8 AM
    const MODES = ["month", "week", "day"];
    // One status per chip, strongest first (the legend's colours). Hosting
    // comes first: you're going to your own event.
    const STATUS_ORDER = ["hosting", "going", "maybe", "starred", "my_org"];
    const STATUS_CLASS = { going: "is-going", maybe: "is-maybe", starred: "is-saved", hosting: "is-hosting", my_org: "is-my_org" };
    const STATUS_TEXT = { going: "going", maybe: "maybe", starred: "saved", hosting: "hosting", my_org: "your org" };
    const FIND_FORMAT = new Intl.DateTimeFormat("en-US", { weekday: "long", month: "short", day: "numeric" });

    const $ = (id) => document.getElementById(id);

    const sameDay = (a, b) => a.getFullYear() === b.getFullYear()
        && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();

    const dayKey = (date) => `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`;

    const startOfDay = (date) => new Date(date.getFullYear(), date.getMonth(), date.getDate());

    const addDays = (date, days) => new Date(date.getFullYear(), date.getMonth(), date.getDate() + days);

    const cleanName = (name) => String(name || "")
        .replace(/^\[Demo\]\s*/, "").replace(/\s*\(demo[^)]*\)$/, "");

    /** A server entry, checked and normalized; null if it can't be shown. */
    function readEntry(raw) {
        if (!raw || typeof raw !== "object" || typeof raw.id !== "string") return null;
        const start = new Date(raw.starts_at);
        const end = new Date(raw.ends_at);
        if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return null;
        const relations = Array.isArray(raw.relations) ? raw.relations.filter((r) => typeof r === "string") : [];
        return {
            id: raw.id,
            title: typeof raw.title === "string" && raw.title.trim() ? raw.title : "Untitled event",
            start,
            end: end > start ? end : start,
            location: typeof raw.location === "string" ? raw.location : "",
            host: cleanName(raw.host),
            hostId: typeof raw.host_id === "string" ? raw.host_id : null,
            hostKind: raw.host_kind === "person" ? "person" : "org",
            relations,
            cancelled: raw.is_cancelled === true,
            draft: raw.is_draft === true,
            status: STATUS_ORDER.find((r) => relations.includes(r)) || "my_org",
            hosting: relations.includes("hosting"),
            myRsvp: relations.includes("going") ? "going" : relations.includes("maybe") ? "interested" : null,
            starred: relations.includes("starred"),
        };
    }

    class PlanCalendar {
        constructor() {
            this.grid = $("cal-grid");
            this.title = $("cal-title");
            this.dayEyebrow = $("day-eyebrow");
            this.dayTitle = $("day-title");

            const params = new URLSearchParams(location.search);
            const start = PlanCalendar.dateFromUrl() || new Date();
            this.mode = MODES.includes(params.get("cal")) ? params.get("cal") : "month";
            this.selected = startOfDay(start);
            this.shown = new Date(start.getFullYear(), start.getMonth(), 1);
            this.byDay = new Map(); // day key -> entries
            this.loaded = ""; // the range the events in byDay cover
            this.request = 0;
            this.scrolled = false; // the hours open at 8 AM once, then stay put

            $("cal-prev").addEventListener("click", () => this.step(-1));
            $("cal-next").addEventListener("click", () => this.step(1));
            $("cal-today").addEventListener("click", () => this.select(new Date()));
            $("cal-retry").addEventListener("click", () => this.load());
            // Only Month / Week / Day: My Events' Calendar / List buttons share the look.
            for (const button of document.querySelectorAll(".cal-view[data-mode]")) {
                button.addEventListener("click", () => this.setMode(button.dataset.mode));
            }
        }

        async start() {
            this.render();
            this.load();
        }

        setMode(mode) {
            if (!MODES.includes(mode) || mode === this.mode) return;
            this.mode = mode;
            this.scrolled = false;
            this.shown = new Date(this.selected.getFullYear(), this.selected.getMonth(), 1);
            this.changed();
        }

        /** Back or forward one month, week or day. */
        step(by) {
            if (this.mode === "month") {
                this.shown = new Date(this.shown.getFullYear(), this.shown.getMonth() + by, 1);
                // Keep the selected day in the month shown (the 31st becomes the 30th, and so on).
                const last = new Date(this.shown.getFullYear(), this.shown.getMonth() + 1, 0).getDate();
                this.selected = new Date(this.shown.getFullYear(), this.shown.getMonth(),
                                         Math.min(this.selected.getDate(), last));
            } else {
                const days = this.mode === "week" ? 7 * by : by;
                this.selected = addDays(this.selected, days);
                this.shown = new Date(this.selected.getFullYear(), this.selected.getMonth(), 1);
            }
            this.changed();
        }

        select(date) {
            this.selected = startOfDay(date);
            this.shown = new Date(date.getFullYear(), date.getMonth(), 1);
            this.changed();
        }

        /** Redraw, keep the URL in step, and load if the range moved. */
        changed() {
            this.writeUrl();
            this.render();
            if (this.rangeKey() !== this.loaded) this.load();
        }

        writeUrl() {
            const url = new URL(location.href);
            url.searchParams.set("cal", this.mode);
            url.searchParams.set("date", PlanCalendar.isoDate(this.selected));
            history.replaceState(null, "", url);
        }

        gridStart() {
            const first = new Date(this.shown);
            first.setDate(1 - first.getDay());
            return startOfDay(first);
        }

        /** The days on screen: [start, end) for the month grid, week or day. */
        range() {
            if (this.mode === "week") {
                const start = addDays(this.selected, -this.selected.getDay());
                return [start, addDays(start, 7)];
            }
            if (this.mode === "day") return [this.selected, addDays(this.selected, 1)];
            const start = this.gridStart();
            return [start, addDays(start, GRID_DAYS)];
        }

        rangeKey() {
            return this.range().map(dayKey).join("/");
        }

        // --- loading -----------------------------------------------------------

        async load() {
            const id = ++this.request;
            const [start, end] = this.range();
            const key = this.rangeKey();
            this.setDayStatus("Loading events…");
            try {
                // A page can show other events (an org page shows that org's)
                // by setting window.CalendarSource before this script runs:
                // (start, end) => Promise of {entries: [...]}, same shape as /api/my-calendar.
                const data = window.CalendarSource
                    ? await window.CalendarSource(start, end)
                    : await Api.get("/api/my-calendar", { start: PlanCalendar.iso(start), end: PlanCalendar.iso(end) });
                if (id !== this.request) return; // a newer request has started
                this.byDay = PlanCalendar.index(data, start, end);
                this.loaded = key;
                this.hideBanner();
                this.setDayStatus("");
            } catch (error) {
                if (id !== this.request) return;
                this.byDay = new Map();
                this.loaded = "";
                this.showBanner(error);
                this.setDayStatus("");
            }
            this.render();
        }

        /** ?date=YYYY-MM-DD opens that day; anything malformed is ignored. */
        static dateFromUrl() {
            const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(new URLSearchParams(location.search).get("date") || "");
            if (!match) return null;
            const [year, month, day] = match.slice(1).map(Number);
            const date = new Date(year, month - 1, day);
            const valid = date.getFullYear() === year && date.getMonth() === month - 1 && date.getDate() === day;
            return valid && year >= 2000 && year <= 2100 ? date : null;
        }

        /** YYYY-MM-DD of a local date (for Discover's date filter). */
        static isoDate(date) {
            const pad = (n) => String(n).padStart(2, "0");
            return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
        }

        /** Local time with its offset, e.g. 2026-11-01T00:00:00-04:00. */
        static iso(date) {
            const pad = (n) => String(Math.abs(Math.trunc(n))).padStart(2, "0");
            const offset = -date.getTimezoneOffset();
            const sign = offset >= 0 ? "+" : "-";
            return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
                + `T${pad(date.getHours())}:${pad(date.getMinutes())}:00`
                + `${sign}${pad(offset / 60)}:${pad(offset % 60)}`;
        }

        /** Put every event on each day it covers (within the grid, max MAX_SPAN_DAYS). */
        static index(data, gridStart, gridEnd) {
            const byDay = new Map();
            const add = (entry) => {
                let day = startOfDay(entry.start < gridStart ? gridStart : entry.start);
                for (let i = 0; i < MAX_SPAN_DAYS && day < gridEnd && day < entry.end; i += 1) {
                    const key = dayKey(day);
                    if (!byDay.has(key)) byDay.set(key, []);
                    byDay.get(key).push(entry);
                    day = new Date(day.getFullYear(), day.getMonth(), day.getDate() + 1);
                }
            };
            const entries = (Array.isArray(data?.entries) ? data.entries : []).map(readEntry).filter(Boolean);
            for (const entry of entries) add(entry);
            for (const list of byDay.values()) list.sort((a, b) => a.start - b.start);
            return byDay;
        }

        // --- drawing -------------------------------------------------------------

        render() {
            this.title.textContent = this.heading();
            const unit = { month: "month", week: "week", day: "day" }[this.mode];
            $("cal-prev").setAttribute("aria-label", `Previous ${unit}`);
            $("cal-next").setAttribute("aria-label", `Next ${unit}`);
            for (const button of document.querySelectorAll(".cal-view[data-mode]")) {
                button.setAttribute("aria-pressed", String(button.dataset.mode === this.mode));
            }
            $("cal-month").hidden = this.mode !== "month";
            $("cal-hours").hidden = this.mode === "month";
            if (this.mode === "month") this.renderGrid();
            else this.renderHours();
            this.renderDay();
        }

        /** "November 2026", "Nov 15 – 21, 2026" or "Saturday, November 14, 2026". */
        heading() {
            if (this.mode === "day") return FULL_FORMAT.format(this.selected);
            if (this.mode === "month") return MONTH_FORMAT.format(this.shown);
            const [start, end] = this.range();
            const last = addDays(end, -1);
            const year = last.getFullYear();
            if (start.getMonth() === last.getMonth()) {
                return `${SHORT_FORMAT.format(start)} – ${last.getDate()}, ${year}`;
            }
            const startYear = start.getFullYear() !== year ? `, ${start.getFullYear()}` : "";
            return `${SHORT_FORMAT.format(start)}${startYear} – ${SHORT_FORMAT.format(last)}, ${year}`;
        }

        // --- week and day: a column of hours per day ------------------------------

        renderHours() {
            const [start, end] = this.range();
            const days = [];
            for (let day = start; day < end; day = addDays(day, 1)) days.push(day);
            const today = new Date();

            const head = $("hours-head");
            head.style.setProperty("--days", String(days.length));
            head.replaceChildren(document.createElement("span"), ...days.map((day) => {
                const button = document.createElement("button");
                button.type = "button";
                button.className = "hours-day";
                if (sameDay(day, today)) button.classList.add("is-today");
                button.setAttribute("aria-pressed", String(sameDay(day, this.selected)));
                button.setAttribute("aria-label", FULL_FORMAT.format(day));
                const name = document.createElement("span");
                name.className = "hours-day-name";
                name.textContent = WEEKDAY_FORMAT.format(day).slice(0, 3);
                const number = document.createElement("span");
                number.className = "hours-day-number";
                number.textContent = String(day.getDate());
                button.append(name, number);
                button.addEventListener("click", () => this.select(day));
                return button;
            }));

            const gutter = document.createElement("div");
            gutter.className = "hours-gutter";
            gutter.setAttribute("aria-hidden", "true");
            for (let hour = 1; hour < 24; hour += 1) {
                const label = document.createElement("span");
                label.style.top = `${hour * HOUR_PX}px`;
                label.textContent = HOUR_FORMAT.format(new Date(2000, 0, 1, hour));
                gutter.append(label);
            }
            const body = $("hours-body");
            body.style.setProperty("--days", String(days.length));
            body.style.setProperty("--hour", `${HOUR_PX}px`);
            body.replaceChildren(gutter, ...days.map((day) => this.hoursColumn(day, today)));

            if (!this.scrolled) {
                this.scrolled = true;
                $("hours-scroll").scrollTop = FIRST_HOUR_SHOWN * HOUR_PX - 10; // a little above, so its label shows
            }
        }

        hoursColumn(day, today) {
            const column = document.createElement("div");
            column.className = "hours-column";
            if (sameDay(day, this.selected)) column.classList.add("is-selected");
            column.setAttribute("role", "list");
            column.setAttribute("aria-label", FULL_FORMAT.format(day));
            if (sameDay(day, today)) {
                const now = document.createElement("span");
                now.className = "hours-now";
                now.style.top = `${(today.getHours() + today.getMinutes() / 60) * HOUR_PX}px`;
                now.setAttribute("aria-hidden", "true");
                column.append(now);
            }
            const dayEnd = addDays(day, 1);
            const pieces = (this.byDay.get(dayKey(day)) || []).map((entry) => {
                // The part of the event on this day (a late event can run past midnight).
                const from = entry.start < day ? day : entry.start;
                const to = entry.end > dayEnd ? dayEnd : entry.end;
                const top = ((from - day) / 3600000) * HOUR_PX;
                const height = Math.max(MIN_BLOCK_PX, ((to - from) / 3600000) * HOUR_PX);
                return { entry, top, bottom: top + height };
            });
            for (const piece of PlanCalendar.lanes(pieces)) column.append(this.block(piece, day));
            column.addEventListener("click", (event) => {
                if (event.target === column) this.select(day);
            });
            return column;
        }

        /** Side-by-side lanes for events that overlap, like any calendar app. */
        static lanes(pieces) {
            pieces.sort((a, b) => a.top - b.top || b.bottom - a.bottom);
            let group = [];
            let groupEnd = -1;
            const finish = () => {
                const count = Math.max(...group.map((p) => p.lane)) + 1;
                for (const piece of group) piece.lanes = count;
            };
            for (const piece of pieces) {
                if (group.length && piece.top >= groupEnd) {
                    finish();
                    group = [];
                }
                const used = new Set(group.filter((p) => p.bottom > piece.top).map((p) => p.lane));
                let lane = 0;
                while (used.has(lane)) lane += 1;
                piece.lane = lane;
                group.push(piece);
                groupEnd = Math.max(groupEnd, piece.bottom);
            }
            if (group.length) finish();
            return pieces;
        }

        block({ entry, top, bottom, lane, lanes }, day) {
            const block = document.createElement("button");
            block.type = "button";
            block.className = `hours-event ${STATUS_CLASS[entry.status]}`;
            if (entry.cancelled) block.classList.add("is-cancelled");
            block.setAttribute("role", "listitem");
            block.style.top = `${top}px`;
            block.style.height = `${bottom - top}px`;
            block.style.left = `calc(${(100 / lanes) * lane}% + 2px)`;
            block.style.width = `calc(${100 / lanes}% - 4px)`;
            const title = document.createElement("span");
            title.className = "hours-event-title";
            title.textContent = entry.title;
            const time = document.createElement("span");
            time.className = "hours-event-time";
            time.textContent = `${TIME_FORMAT.format(entry.start)}–${TIME_FORMAT.format(entry.end)}`;
            block.append(title, time);
            block.setAttribute("aria-label", `${entry.title}, ${time.textContent}, ${STATUS_TEXT[entry.status]}`
                + (entry.cancelled ? ", cancelled" : ""));
            block.addEventListener("click", () => this.select(day));
            return block;
        }

        renderGrid() {
            const today = new Date();
            const first = this.gridStart();
            const cells = [];
            for (let i = 0; i < GRID_DAYS; i += 1) {
                const date = new Date(first.getFullYear(), first.getMonth(), first.getDate() + i);
                cells.push(this.cell(date, today));
            }
            this.grid.replaceChildren(...cells);
        }

        cell(date, today) {
            const cell = document.createElement("button");
            cell.type = "button";
            cell.className = "cal-cell";
            if (date.getMonth() !== this.shown.getMonth()) cell.classList.add("is-outside");
            if (sameDay(date, today)) {
                cell.classList.add("is-today");
                cell.setAttribute("aria-current", "date");
            }
            cell.setAttribute("aria-pressed", String(sameDay(date, this.selected)));
            const number = document.createElement("span");
            number.className = "cal-date";
            number.textContent = String(date.getDate());
            cell.append(number);

            const entries = this.byDay.get(dayKey(date)) || [];
            const label = [FULL_FORMAT.format(date)];
            if (entries.length) {
                label.push(entries.map((e) => `${e.title}, ${STATUS_TEXT[e.status]}`).join("; "));
            }
            cell.setAttribute("aria-label", label.join(": "));

            if (entries.length) {
                const chips = document.createElement("span");
                chips.className = "cal-chips";
                chips.setAttribute("aria-hidden", "true");
                for (const entry of entries.slice(0, CHIPS_PER_CELL)) chips.append(PlanCalendar.chip(entry));
                const hidden = Math.max(0, entries.length - CHIPS_PER_CELL);
                if (hidden) {
                    const more = document.createElement("span");
                    more.className = "cal-more";
                    more.textContent = `+${hidden} more`;
                    chips.append(more);
                }
                cell.append(chips);
            }
            cell.addEventListener("click", () => this.select(date));
            return cell;
        }

        static chip(entry) {
            const chip = document.createElement("span");
            chip.className = `cal-chip ${STATUS_CLASS[entry.status]}`;
            if (entry.cancelled) chip.classList.add("is-cancelled");
            chip.textContent = entry.title;
            return chip;
        }

        renderDay() {
            const isToday = sameDay(this.selected, new Date());
            this.dayEyebrow.textContent = isToday ? "Today" : WEEKDAY_FORMAT.format(this.selected);
            this.dayTitle.textContent = DAY_FORMAT.format(this.selected);
            const entries = this.byDay.get(dayKey(this.selected)) || [];
            this.fillList($("day-list"), $("day-empty"), entries);
            // Discovery lives on Discover: open it with this day already set.
            const find = $("day-find");
            find.textContent = `Find events on ${FIND_FORMAT.format(this.selected)}`;
            find.href = `discover?${new URLSearchParams({ date: PlanCalendar.isoDate(this.selected) })}`;
        }

        fillList(list, empty, entries) {
            list.replaceChildren(...entries.map((entry) => this.dayEvent(entry)));
            empty.hidden = entries.length > 0;
        }

        dayEvent(entry) {
            const item = document.createElement("li");
            item.className = "day-event";
            const time = document.createElement("div");
            time.className = "day-event-time";
            time.textContent = `${TIME_FORMAT.format(entry.start)}–${TIME_FORMAT.format(entry.end)}`
                + (entry.location ? ` · ${entry.location}` : "");
            const title = document.createElement("p");
            title.className = "day-event-title";
            title.textContent = entry.title;
            item.append(time, title);
            if (entry.host) {
                item.append(window.Collectivize.Ui.hostedBy(entry.host, entry.hostId, entry.hostKind, "day-event-host"));
            }
            const tags = PlanCalendar.tags(entry);
            if (tags.childElementCount) item.append(tags);
            if (entry.draft) return item;
            if (entry.hosting) {
                // You're going to your own event: no going / maybe / save.
                if (window.AddToCalendar && !entry.cancelled) item.append(PlanCalendar.addToCalendar(entry));
                return item;
            }
            const controls = new EventActions({
                eventId: entry.id,
                myRsvp: entry.myRsvp,
                starred: entry.starred,
                cancelled: entry.cancelled,
                onChange: () => this.load(), // moves it in or out of "My events"
                onError: (message) => this.setDayStatus(message, { error: true }),
            });
            item.append(controls.element);
            if (window.AddToCalendar && !entry.cancelled) item.append(PlanCalendar.addToCalendar(entry));
            return item;
        }

        static addToCalendar(entry) {
            return window.AddToCalendar.menu({
                id: entry.id, title: entry.title, location: entry.location, description: "",
                starts_at: entry.start.toISOString(), ends_at: entry.end.toISOString(),
            });
        }

        static tags(entry) {
            const tags = document.createElement("div");
            tags.className = "day-event-tags";
            const add = (text, muted = false, kind = "") => {
                const tag = document.createElement("span");
                tag.className = `day-tag${muted ? " is-muted" : ""}${kind ? ` ${kind}` : ""}`;
                tag.textContent = text;
                tags.append(tag);
            };
            if (entry.relations.includes("going")) add("Going");
            else if (entry.relations.includes("maybe")) add("Maybe");
            if (entry.relations.includes("starred")) add("Saved");
            if (entry.relations.includes("hosting")) add("Hosting", false, "is-hosting");
            if (entry.relations.includes("my_org")) add("Your org");
            if (entry.cancelled) add("Cancelled", true);
            if (entry.draft) add("Draft", true);
            return tags;
        }

        // --- messages ------------------------------------------------------------

        showBanner(error) {
            $("cal-banner-text").textContent = `Couldn't load events: ${error instanceof Error ? error.message : "unknown problem"}`;
            $("cal-banner").hidden = false;
        }

        hideBanner() {
            $("cal-banner").hidden = true;
        }

        setDayStatus(text, { error = false } = {}) {
            const status = $("day-status");
            status.textContent = text;
            status.classList.toggle("is-error", error);
        }
    }

    // My Events (my-events.js) and the org page (org.js) reload it when the calendar view is shown.
    const calendar = new PlanCalendar();
    window.MyCalendar = calendar;
    calendar.start();
})();
