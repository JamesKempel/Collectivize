# Changes

This is a running log of changes made to Collectivize, newest first. Each entry says what changed, why, and any decisions made along the way.

---

## 2026-11-15 — Merged James's main (admin security) into the fork

- Brought in `JamesKempel/Collectivize` main ("merge situation": TOTP, account rules, admin setup, hidden admins).
- Conflicts: the fork's newer home page (no wordmark) and network map (full screen, org mutual lines) kept; `accounts.py` keeps both `hidden` and `avatar` in the admin JSON; both changelogs kept.
- `api/index.py`: demo session tokens now also carry the admin login name (sessions gained `login`).

---

## 2026-11-15 — Random animal profile pictures; home screen opens Discover on click

- `src/backend/objects/person.py`: `Person.avatar`, one of `AVATARS` (16 animal emoji), picked at random by `random_avatar()` when an account is created (email sign-in, invite, admin create) and kept. People saved before this have `""` and keep the animal picked from their name, so nobody's picture changes or goes blank. No reseed needed.
- The API sends `avatar` with each person (me, profiles, search, org members, admin lists, network map). `Ui.animal` / `Ui.avatar` in `src/frontend/shared.js` is now the one place that picks what to draw: the saved animal, else the name-based one. Profile cards, the network map and its lists, Discover, org pages and admin lists all use it (they used letters before, except profile cards and the map).
- Home screen when signed in (`index.html`, `landing.js`, `landing.css`): the "Go to Discover" link is gone; a click (or Enter / Space) anywhere except the logo opens Discover. Clicking the logo still just spins it.
- Tests: `tests/backend/test_avatars.py`, plus sign-up checks in `test_access.py`, `test_invites.py`, `test_accounts.py`.

---

## 2026-11-15 — Vercel demo: admin login "Billy Joe"

- `api/index.py`: `/admin` on the live demo accepts username "Billy Joe", password "collectivize-demo", signing in as the seeded platform admin Pat (owner). Public on purpose: fake data only (noted in `VERCEL.md`).
- Sessions on the demo are now signed tokens (`_SignedSessionStore`), so a sign-in works on every Vercel instance instead of falling back to Drew when a request lands on another one. `src/backend/` unchanged.

---

## 2026-11-15 — Sigma Chi Pi Chapter, and a website box on org pages

- `src/backend/seed.py`: the demo chapter "Alpha Beta, Gamma Chapter" is now "Sigma Chi Pi Chapter", and it links to a website (`WEBSITES`, the reserved example address https://example.org/ so the demo never points at a real site). `demo/collectivize-demo.db` reseeded; `src/frontend/main.js` and `tests/backend/test_server.py` updated to the new name.
- `src/frontend/org.js` / `app.css`: the website is now a box at the very top of the org page (globe, address, "Visit ↗") that opens the site in a new tab; only http(s) addresses are linked. Admins of an org without a website see a dashed "Add a link to your website" box that jumps to the Website field in the editor. The old plain link under the title is gone.

---

## 2026-11-15 — Demo calendar: mostly your orgs, fewer "going", two you host

- `DemoCalendar` (`src/backend/seed.py`) now joins Drew to up to 4 busy orgs (blue), hosts 2 events as Drew (red), then tops days up with maybe / saved and only a few going, about 2 events a day. Demo DB reseeded.

---

## 2026-11-15 — Demo calendar filled out (every color shows)

- `src/backend/seed.py`: new `DemoCalendar` gives Drew going / maybe / saved plans on up to 3 events a day for the next 6 weeks (bulk seed only), so the calendar looks full and shows every color.
- `demo/collectivize-demo.db` reseeded.

---

## 2026-11-15 — Profiles: background pictures

- **What.** A profile can pick a background picture, shown as a banner across the top of the page (Profile tab, the Network tab's side panel, and the editor's live preview). The editor (both tabs) has a "Background picture" group: None, Sunset, Ocean, Forest, Lavender, Sand, Night sky.
- **Presets, not uploads.** The pictures are drawn in CSS (`.p-cover-<key>` in `profile.css`), so there's nothing to upload, store, moderate or host, and they survive the Vercel demo's data resets like any other setting. Uploaded photos would need file storage the demo doesn't have.
- **Backend.** `Person.background_picture` (`objects/person.py`): "" (none) or one of `BACKGROUND_PICTURES`; anything else is refused. Editable through `ProfileService.update` (`graph/profiles.py`), saved with `background_picture` in `POST /api/profile` (`null` clears it), and returned as `background_picture` on profile pages (`network_api.py`) and the connection preview card (`app_api.py`). People saved before this load with no picture (the field has a default), so the demo database needs no reseed.
- **Keep in step.** The keys live in three places: `BACKGROUND_PICTURES` in `objects/person.py`, `BACKGROUND_PICTURES` in `profile-render.js`, and the `.p-cover-*` rules in `profile.css`.
- **Heads-up for local databases.** A local DB saved by this version stores the new field; an older checkout reading it refuses the unknown field. Pull before running against a shared DB.
- **Tests.** `tests/backend/test_profiles.py`: saved, shown, kept and cleared; non-presets refused; old records still load. Not run in this session (dependencies weren't installed); the model's rule was checked by hand.

---

## 2026-11-15 — Network map: names never overlap again; edit your page from the Network tab

- **Overlapping names (`network-layout.js`).** The last layout step, which pushes every node and the name under it clear of the others (`clearLabels`, from "names are never covered by another node or name"), was dropped when `main` was merged in `0dcc30f`: the function was still there but never called. The call is back. Checked with a script: a 30-person map went from up to 42 overlapping name boxes to 0.
- **Edit page on the Network tab (`network.js`, `network.html`, `network.css`).** On your own network, the side panel has "Edit page" next to "Open my profile". It opens the same editor as the Profile tab (`profile-editor.js`: name, text, Top 3, website, colours, layout, privacy) in the map's place; saving brings the map back with your node in its new colour, Cancel goes straight back.
- Profiles have no background pictures yet (nothing stores an image), so the editor has none either; that needs a backend change.

---

## 2026-11-15 — Discover: friends going as 1, 2 or 3+ icons; "Friends are attending"

- The friends row shows 1, 2 or 3 blank icons, and a "+" after three when more are going (no exact count). The text beside it is always "Friends are attending" (`discover.js`, `discover.css`).

---

## 2026-11-15 — Discover: friends going anonymous again (with a count); "Like your orgs" hidden

- **Friends going (`discover.js`, `discover.css`).** Profile pictures removed again: friends stay anonymous. The row now shows one blank icon per friend going (1, 2 or 3), then "+N" past three, and the text keeps the count ("A friend is attending" / "4 friends are attending"). `Ui.photo` (added in the entry below) is removed from `shared.js`.
- **"Like your orgs: …" reason (`discover.js`).** No longer shown on event cards. The backend still produces it (`graph/explain.py`) for ranking and the admin scores view; only the card filter changed. Backend untouched.

---

## 2026-11-15 — Discover: friends going show their profile pictures

- An event card's "Friends are attending" row used three blank person icons whatever happened. It now shows the profile picture of each friend actually going (the demo's animal emoji, the same one as on their profile and the network map), up to three, then "+N". Still no names or initials (Cody's rule). The text says how many: "A friend is attending" / "4 friends are attending" (`discover.js`, `discover.css`).
- The emoji picker is now also `Ui.photo(name)` in `shared.js`, for pages that don't load the profile or network scripts. It must stay in step with `avatar()` in `profile-render.js` and `network-view.js`.

---

## 2026-11-15 — Org page: short members list with search; events as list or calendar

- **Members (`org.js`, `app.css`).** The members panel shows the top 3, "Show 7 more" opens it to 10, and a search box (shown once there are more than 3) finds anyone you can see in the org, 10 matches at a time. A 200-person chapter no longer runs down the whole page. Admins still get Remove on each row and the add-by-email form.
- **Upcoming events (`org.js`, `org.html`, `calendar.js`).** A List / Calendar switch, styled like My Events'. The calendar is My Events' own (`calendar.js`): a page can now set `window.CalendarSource` to feed it other events, and the org page feeds it the org's. The view is kept in the URL (`?view=calendar`).
- **API (`app_api.py`).** `/api/org` events now include `ends_at` and `relations` (`going` / `maybe` from your RSVP, `my_org` if you're a member), the same words as `/api/my-calendar`, so the calendar colours them and shows the right Going / Maybe state.

---

## 2026-11-15 — Network: no more bounces to Discover; full-screen map

- **Bounce fix (Vercel only, `api/index.py`).** Sign-ins live in one function instance's memory, and Vercel spreads requests across instances. An open page checks `/api/session` every 8 seconds; when that check landed on another instance it heard "signed out", sent the visitor to the sign-in screen, and auto-sign-in dropped them on Discover. On the demo, `/api/session` now auto-signs in like every other call (everyone is the demo account, so there's no account switching to protect). `src/backend/` is unchanged, so local and Railway behaviour stay the same.
- **Full screen (`network-view.js`, `network.css`, `network.js`).** A button at the top right of the map grows it to fill the window, above the nav, with the "Mutual connections" switch still underneath. The whole page goes browser-full-screen where allowed (not the map element, so clicking someone and redrawing keeps you in full screen); on iPhone it fills the window instead. Esc or the same button shrinks it. A closed network (nothing to show) leaves full screen.

---

## 2026-11-15 — "Hosted by …" opens the host's page

- Wherever an event says "Hosted by X" (Discover cards, the calendar, My Events, event lists on profiles and the Network side panel), X is now a link to the org's page (or the person's profile). One helper: `Ui.hostedBy` in `shared.js`; style `.host-link` in `nav.css`.
- The API now sends who the host is, not only their name: `host_id` and `host_kind` on calendar and My Events entries (`demo_api.py`, `app_api.py`), and `host.id` on profile events (`network_api.py`).
- Discover's small host icon is gone: the name itself is the link.

---

## 2026-11-15 — "Mutual connections" also links people to their communities

- With the switch on, the map now also draws a line from each person to the communities shown that they belong to (e.g. a chapter), not only lines between people (`network-layout.js`).
- The switch shows whenever there's something for it to draw: people who know each other, or people in a community shown (`network-view.js`).

---

## 2026-11-15 — Team on the fork: collaborators and push rules

- `jameszupa` and `caumartin-maker` invited to `CodyGrodsky/Collectivize` with write access.
- `CLAUDE.md` gained "Pushing": pull with rebase before every push, never force-push `main`, PRs for bigger changes, the live site is shared, and don't hand-edit the demo database.

---

## 2026-11-15 — Mock profile pictures (emoji)

- Demo stand-in for profile photos: each person gets an animal emoji picked from their name (same on the network map and their profile). Communities keep their initials. `avatar()` in `network-view.js` and `profile-render.js`.

---

## 2026-11-15 — Network page: the map on the left, the selected page on the right

**Request:** picking someone on the network map took an extra click to see their page.

### What changed
- The Network page is now two columns: the map on the left, and on the right the page of whoever is in the middle (their full profile, drawn by the same `ProfileRenderer` as the Profile tab, or a community's details and upcoming events). One click on the map now updates both (`network.js`, `network.css`).
- The right column stays in view while scrolling; under 960px wide it goes under the map.
- "Open full profile" / "Open community page" under the panel for the full page. The old profile button in the map's header is gone (the panel replaces it).

---

## 2026-11-15 — Network map: "Mutual connections" switch

### What changed
- The network layout now also returns the ties between the people shown on the map (`kind: "mutual"`), not only the middle's own lines (`network-layout.js`).
- A "Mutual connections" switch under the map draws those lines, lighter and underneath the middle's own lines (`network-view.js`, `network.css`).

### Decisions
- Off by default, to keep the map quiet. The choice is remembered per browser (`localStorage`); if storage is blocked the switch still works for the visit.
- The switch is hidden when nobody on the map knows each other.

---

## 2026-11-15 — Live public demo on Vercel (branch `vercel-demo`)

**Request:** get a public URL up tonight on Vercel, with fake data only, so the team can ship UI and feature changes fast; Railway later.

### What changed
- **The whole app runs as one Vercel Python function** (`api/index.py`), using the existing `RequestHandler` from `src/backend/server.py`. No backend code was changed.
- **`vercel.json`** sends every address to the function and bundles `src/`, `public/`, `app/` and `demo/` with it. **`.vercelignore`** keeps `.venv`, `data/`, tests and local secrets out of the upload.
- **`demo/collectivize-demo.db`**: a freshly seeded, fully fictional database (110 orgs, 954 people, 995 events), committed so every deploy has the same data.
- **`VERCEL.md`, `CLAUDE.md`, `AGENTS.md`**: how the deploy works and where to work, for people and their coding agents.

### Decisions
- Public demo settings: everyone is signed in automatically as Drew (demo), no email codes, AI search off, no admin logins, no secrets.
- Each function instance works on its own copy of the demo DB in `/tmp`, so changes are short-lived and reset to the demo data. Fine for a demo.
- The demo DB was seeded fresh, not copied from anyone's local `data/test.db`, which can hold real sign-ins.
- Vercel passes `/api/index` as the request path after a rewrite, so the rewrite carries the original address as `__path` and the function puts it back before routing.

---

## 2026-11-14 — Connection requests are limited; remembered sign-ins renew with use; Secure cookie over https

**Request:** "fix 12 and 13" (from the run-through of how the app differs from a normal application).

### What changed
- **12. Connection requests.** Two limits, so one account can't send requests to everyone:
  - At most 25 requests waiting for an answer at once (`MAX_OPEN_REQUESTS` in `src/backend/graph/connections.py`). An answer or a cancel frees a place; accepted connections don't count.
  - At most 20 new requests an hour per person (`CONNECT_REQUESTS_PER_HOUR` in `app_api.py`, using the new `src/backend/rate_limit.py`). Accepting someone else's request is never limited.
  - Both show a plain message on the Connect button.
- **13. Remembered sign-ins renew with use.** A sign-in now lasts 30 days after the person's *last* visit: each day they use the site, the 30 days start again and the browser's cookie is given the new lifetime. Someone who stops coming is signed out 30 days later. Admin sign-ins still end 8 hours after sign-in, used or not.
- **13. The cookie is marked `Secure` over https.** When the site is reached through an https proxy (`X-Forwarded-Proto: https`), the session cookie gets `Secure`. On plain `http://127.0.0.1` it can't: the browser would drop the cookie.

### Decisions
- The waiting cap lives with the data (it survives restarts); the hourly brake is in memory and resets on restart.
- A session is extended at most once a day, so the sessions file isn't rewritten on every click.
- There is no upper limit on how long a sign-in can keep renewing.
- Sign-ins made before this change don't renew; they do from the next sign-in.

### Tests
- `tests/backend/test_limits_and_renewal.py` (9 tests).

---

## 2026-11-14 — Short addresses, admin scripts for admins only, a Content-Security-Policy, and the other HTTP methods

**Request:** "fix 7, 8, 14 and 15" (from the run-through of how the app differs from a normal application).

### What changed
- **8. Short addresses.** Pages are now `/discover`, `/my-events`, `/network`, `/profile`, `/account`, `/org`, `/admin`, with the sign-in screen at `/` (and `/home`). Scripts and stylesheets are at the top level (`/shared.js`). Nothing in an address shows where a file lives. Old addresses (`/src/frontend/discover.html`, `/discover.html`) redirect to the new ones with their query string; `/calendar` redirects to `/my-events?view=calendar`. The table is the new `src/backend/server_routes.py`; a file is only served through it.
- **7. Admin scripts for admins only.** `/admin.js` and `/admin-team.js` answer "not found" to anyone who isn't a platform admin. `/admin` sends everyone else to the sign-in screen.
- **14. Content-Security-Policy** on every answer, redirects included: only this site's own scripts run (no inline scripts, no other sites). Also `Permissions-Policy` (no camera, microphone or location) and `Cross-Origin-Opener-Policy`.
- **15. HTTP methods.** HEAD answers like GET without the body; OPTIONS lists what is allowed; PUT, DELETE and PATCH get a plain 405 with an `Allow` header instead of Python's default error page.
- Front end: every page link and image path uses the new addresses; `calendar.html` lost its inline script; a comment naming the repository folder was removed from `nav.js`.

### Decisions
- Styles may still be inline (`style-src 'unsafe-inline'`): a few pages set small inline styles from scripts. Scripts may not.
- The policy allows Google Fonts because the older `main` page's stylesheet imports them.
- `/` shows the sign-in screen directly when signed out and goes to `/discover` when signed in; `/home` always shows the landing page (the nav's wordmark link and the admin entrance `/home?admin=1`).
- Old addresses redirect with 302, not 301, so browsers don't cache them permanently while addresses may still change.
- After sign-in, "go back to where you were" only accepts this site's own page addresses.

### Tests
- `tests/backend/test_addresses.py` (47 tests). Existing tests that used the old addresses were updated. Every page, the sign-in and admin sign-in flows and the invite link were also loaded in headless Chrome: no policy violations, script errors or broken links.

---

## 2026-11-14 — Error pages, no dropped connections, and internal fields kept from users

**Request:** "fix 1 through 6" (from the run-through of how the app differs from a normal application).

### What changed
1. **The browser always gets an answer.** A failure anywhere in a request (for example the database being briefly locked while the session is looked up) used to drop the connection. Now a person's browser gets a "Something went wrong" or "Collectivize is busy" page and the app's own requests get `{"error": ...}`, never the details (`AnswerMixin` in the new `src/backend/server_pages.py`).
2. **Unknown addresses show a "Page not found" page** with a link home, instead of raw JSON. The app's own requests still get JSON. `/favicon.ico` now answers with the app icon.
3. **Developer wording removed from what users see.** "Is scripts/serve.py running?" is now "Can't reach Collectivize right now. Check your connection and try again."; the fallback error is "Something went wrong. Please try again."; the sign-in screen no longer mentions the server's terminal.
4. **The sign-in screen no longer lists demo accounts.** It says "Campus-only for now. We'll email you a code to sign in."
5. **Ranking scores and distances are sent to platform admins only.** Any API answer containing `score` or `distance_km` has them removed for everyone else, whichever route produced it.
6. **Going counts are no longer sent** to anyone but platform admins (`going_count`). My Events now gets `is_full` and uses that for its "Full" note.

### Decisions
- The filter is applied in one place at the HTTP layer, so the Python APIs and their tests are unchanged and a new route can't leak these fields by accident.
- A platform admin viewing as someone still receives the fields.
- Whether a request gets a page or JSON is decided by what it asks for (`Accept: text/html`), so pages opened in a browser get the page.
- The error page is built into the server, not a file, so it still shows when something is broken.

### Tests
- `tests/backend/test_error_answers.py` (14 tests), including a check that no page text mentions `serve.py`, the terminal or demo account addresses.

---

## 2026-11-14 — Admin sign-in: saved passwords no longer break the password step

**Request:** "for some reason the admin sign in isn't working and producing red error message on the front end beneath northeastern.edu"

### What was wrong
- Once a browser had saved the admin password, it filled in the name and the password together. The form took that as "a different name was typed", hid the password box again and showed only the prompt "This is an admin account. Enter its password." under the email field, in red, so it looked like an error and signing in went round in a circle. Reproduced on the running site; the server side was fine.

### What changed
- `src/frontend/signin-form.js` only starts over when the typed name really changes, and clears the old prompt when it does.
- Prompts for the next step ("enter its password", "we emailed a code") are now dark grey; only real errors are red (`.signin-message.is-info` in `landing.css`).
- `AdminAuth.check` (`src/backend/admin_auth.py`): when several logins share one account email and the email is typed, a correct password for one login no longer counts as a wrong guess against the others (which could lock them for 15 minutes). One test added.

---

## 2026-11-14 — Sign-in verifies the Northeastern address with an emailed code; one mailbox, one account

**Request:** "can you make it so it verifies the .edu and then you can only use the same northeastern account once"

### What changed
- **A code proves the address.** Typing a Northeastern email no longer signs you in. The server sends a six-digit code to that address, and typing it back is what signs you in (`src/backend/email_verification.py`; `POST /api/signin` then `POST /api/signin/verify`). A new account is only created once its code has been entered.
- **One mailbox, one account.** Capital letters and a "+tag" no longer make a second account: `Name+club@northeastern.edu` is `name@northeastern.edu`, on sign-in and when an admin creates or edits an account (`canonical_email` in `app_api.py`).
- **Mail** (`src/backend/mailer.py`, `scripts/set_mail.py`). With a mail server set up, codes are emailed. Without one, the code is printed in the server's terminal and the sign-in screen says so. The fictional demo accounts (`name.demo@northeastern.edu`) have no mailbox, so their codes always go to the terminal.
- **Sign-in form** is now one shared file, `src/frontend/signin-form.js`, used by the landing page and the invite page, with the code step and "Send a new code".
- `EMAIL_VERIFICATION = True` in `src/backend/config.py` turns it off or on.

### Rules built in
- A code works once, for 10 minutes; a newer code replaces it; five wrong guesses throw it away.
- One address can ask again after 30 seconds, at most 5 times an hour; the server sends at most 60 a minute.
- Only a hash of the code is kept, in memory. The email holds the code and nothing about the person.
- The answer is the same whether or not the address already has an account.
- Admin accounts are never opened by an emailed code (password, plus Duo when set up).

### Decisions
- I read "only use the same northeastern account once" as one Collectivize account per Northeastern mailbox. It does not limit someone to one signed-in browser.
- The code is asked for at each sign-in, not only the first; a sign-in is still remembered for 30 days, so it is rarely needed.
- Tests and callers that pass no verifier keep the old behaviour (the email signs in at once), like the other optional sign-in pieces.

### Tests
- `tests/backend/test_email_verification.py` (22 tests). The landing and invite pages were also driven in headless Chrome against a throwaway server. No real email was sent (no mail server is set up).

---

## 2026-11-14 — One sign-in screen, remembered sign-ins, and Duo for admins

**Request:** "make it so all users start at the login screen for first time login when they load into the website url, and then make it so if an admin account is typed into the login it makes it so you can be admin. Also add rememberance, and add dual authentication using duo only if it is an admin login. Users should only have to login once unless they logged out last session (this makes them log back in again)."

### What changed
- **Sign-in is on again.** `LOGIN_REQUIRED = True` in `src/backend/config.py`: the site opens on the sign-in screen for anyone not signed in.
- **Remembered.** A sign-in lasts 30 days across browser and server restarts (8 hours for an admin). Signing out ends it, so the next visit starts at the sign-in screen. Sessions are kept in `data/sessions.json` (git-ignored, readable only by you) as SHA-256 hashes of the tokens, never the tokens.
- **Admins sign in on the same screen.** Typing an admin username, or an admin account's email, reveals an "Admin password" field. `/admin` now shows this same screen (the separate `admin-login.html` page is gone).
- **Duo for admins only** (`src/backend/duo.py`, `scripts/set_duo.py`). After the password, Duo must approve: a push to the admin's phone, or a passcode typed on the sign-in screen. Ordinary sign-ins never touch Duo.
- Sign-in and session code moved out of `server.py` into `src/backend/server_auth.py` (`server.py` is back under 500 lines).
- New dependency: `duo-client`.

### Decisions
- **Duo's Auth API, not its browser prompt.** The browser prompt needs a public `https://` address, which a local `http://127.0.0.1` server can't give. The Auth API is called by the server, so it works locally.
- **Duo is off until set up.** Without `config/duo.local.json`, admin sign-in is password only and the server warns at start-up. Once set up it fails closed: if Duo is unreachable or says no, the admin is kept out.
- **The sign-in screen now tells an admin name from an ordinary one** (it asks for a password). That is what was asked for; it does mean someone can learn which names are admin logins. The password, lock-out and Duo still stand in the way.
- An admin username that looks like a Northeastern email is treated as the admin login, not as a new student account.
- Admin sign-ins are remembered for 8 hours, not 30 days.
- Development auto-login sessions (`serve.py --no-login`) are not written to the file.

### Tests
- `tests/backend/test_signin_flow.py` (14 tests); `test_admin_auth.py` updated. The sign-in screen was also driven end to end in headless Chrome against a throwaway server with a stand-in Duo. Real Duo was not contacted (no Duo account is set up).

---

## 2026-11-14 — The demo server runs on port 3000 by default

**Request:** "Can you set the port to run on 3000?"

### What changed
- `scripts/serve.py` now listens on `http://127.0.0.1:3000/` unless `--port` says otherwise (was 8000). The default in `backend.server.serve` and the address printed by `scripts/set_admin_password.py` match.
- Not changed: `docs/profile-backend-proposal.md` and `docs/BUGS.md` still mention port 8000.

---

## 2026-11-14 — Search handles short words, plurals, typos, accents, weekends and flooding words

**Request:** "do all the steps in the plan" (the eight-step search plan from the edge-case run below).

### What changed
1. **Matching** (new `src/backend/graph/text_match.py`). A keyword now matches the start of a word from two letters ("rob" finds robotics while typing), ignores accents and letter width ("café" = "cafe"), and treats plurals and endings alike ("robots", "hiking"/"hike"). Invisible characters no longer split a word.
2. **Several words.** Results that contain every word are listed before results that contain only some. A word found in more than half of everything ("demo" in the demo data) is left out when another word narrows things down, and the page says so.
3. **"This weekend"** covers Saturday and Sunday (on a Sunday, just that day). `SearchFilters.days`, `Extraction.days`; the API adds `filters.date_end`; Discover shows "Sat, Nov 14 – Sun, Nov 15".
4. **Typos.** When nothing matches, one wrong, missing, extra or swapped letter per word is allowed (words of four letters or more), and the page says "Nothing matched “robtics”, so this shows results for “robotics”."
5. **Filler and type words.** "about", "named", "called", "likes" and similar are no longer keywords. If the text named a kind ("people who like hiking") and nothing of that kind matched, every kind is searched and the page says so. A type ticked by hand is never widened.
6. **AI timing.** The sentence reader waits at most 4 seconds with no retry (was 30 seconds plus a retry), then reads the sentence locally. After a failure it skips AI for 60 seconds so later searches don't wait again.
7. **Scale.** On a temporary database with 7,726 people and 1,329 events, searches took 0.3–0.5 s. Most of that was thousands of repeated small lookups, so the demo server's store now remembers its own reads for the length of one request (`SqliteGraphStore(read_cache=True)`, cleared on every write and rollback). After: 0.15–0.25 s there, about 0.05 s on the demo database.
8. **Tests.** `tests/backend/test_search_edge_cases.py` (113 tests): about 65 awkward inputs must each get a well-formed answer in under 2 s, plus tests for each behaviour above.

### Decisions
- Typo tolerance only runs when nothing matched as typed, so exact results are never mixed with guesses. A correction can only come from records the viewer may see.
- A two- or three-letter start counts a little less (0.8) than a whole word.
- The flooding rule needs a second, narrower word; "demo" on its own still searches for "demo".
- The read cache is off by default and on only for the request-scoped store; a long-lived store would miss other connections' writes.

### Not done / known
- The Claude path itself was not timed (it costs money); only its timeout and fallback are tested.
- The first search after the server starts is slower (about 1 s on the large database) while records are decoded for the first time.
- "alice demo" on the large database takes about 1 s because it searches twice.
- The older meaning-based search (`graph/ai_search.py`) has its own copy of the stem rule and was left alone.

---

## 2026-11-14 — Search: a page number like "²" no longer crashes

**Request:** "make a plan to debug the search bar to be able to handle almost any input in reasonable time and return accurate results. Search for edge cases and make sure it still works"

### What changed
- `GET /api/find?page=²` answered 500 ("something went wrong"). Python counts "²" as a digit but can't turn it into a number. `AppApi.find` now accepts plain digits only and answers 400 like any other bad page.
- Four cases added to `test_bad_search_input_is_refused` in `tests/backend/test_unified_search.py`.

### Found, not fixed yet
- A 100-query edge-case run (AI off) found no other crash and nothing slower than 0.35 s, but several accuracy gaps (short words, plurals, typos, accents, "this weekend", flooding words). The plan for those was given to the user in chat; nothing else was changed.

---

## 2026-11-14 — Admin powers, an owner who manages admins, and deleted accounts sent home

**Request:** "ensure that there are as little problems with platform admin as possible and also make it so if an account is deleted they are kicked back to home screen. Also make it so there is another account type that manages the admins and has the ability to change powers of admin. For example view only, delete power, view all info, impersonation power, etc."

### What changed
- **Admin powers.** Each platform admin now has a list of powers (`Person.admin_powers`): view all info, view as, edit, create, sign people out, delete. With none, an admin can only see the list of accounts (no emails) and the log. Every admin method checks its own power on each request, so a change applies on the admin's next click.
- **The owner.** A new level above admins (`src/backend/admin_policy.py`). The owner has every power and is the only one who can make or remove admins, set their powers, change a sign-in email, or touch another admin's account. Who the owner is comes from the credentials file (`role: "owner"`), never from the app. New routes: `GET/POST /api/admin/admins`.
- **Admin page.** The owner gets an "Admins and their powers" panel with a tick box per power and "Remove admin"; "Make platform admin" is in the Manage panel. Other admins only see the buttons their powers allow.
- **Deleted accounts go home.** When an account is deleted (or signed out everywhere), each of its browsers is sent to the landing page with a short notice. Open pages check every 8 seconds; any click is refused at once. With sign-in turned off, a deleted account is no longer quietly signed in as Drew.
- **Admin sign-ins end after eight hours.**
- `scripts/set_admin_password.py` gained `--owner` and `--make-owner <username>`.

### Problems closed
- An admin could give themselves or anyone the admin role; that is now the owner's alone.
- An admin with edit rights could change someone's sign-in email and then sign in as them; email changes are now the owner's alone.
- Admins could read, edit, sign out or delete each other and the owner; admin accounts are now the owner's alone to manage.
- A view-only admin could see and search every email; emails now need "view all info".
- The owner account can't be deleted or demoted from the app.
- `/api/me` now reports `is_owner` and `powers`.

### Decisions
- "Impersonation" stays read-only view-as, as the v1.1 spec asks.
- Without an owner in the credentials file nobody can manage admins; tests and old callers that pass no owner list treat every admin as an owner, as before.
- A new admin still needs a login made with the script on the machine running the server; the owner can't set passwords from the page.

### Tests
- `tests/backend/test_admin_powers.py` (17 tests); `test_accounts.py` updated for the moved role change.

---

## 2026-11-14 — A hidden, password-protected admin sign-in at /admin

**Request:** "I need a hidden method to sign in that is still easy to log in from, but normal people won't be able to. Make a config file that contains a field for username and password for admins (if this is secure enough and if not, then recommend other methods)"

### What changed
- **`/admin` is the admin entrance.** It isn't linked from any page. It shows a username and password form (`admin-login.html`) until you are signed in as a platform admin, then the Admin page.
- **Credentials live in `config/admin.local.json`**, which is git-ignored and readable only by you. It holds a username, the admin account's email and a salted scrypt hash of the password, never the password itself. `config/admin.example.json` shows the shape.
- **`scripts/set_admin_password.py`** creates or changes an admin's username and password (`--generate` makes a strong one).
- **Admin accounts can no longer be opened by email.** Before, anyone who typed `pat.demo@northeastern.edu` on the sign-in page became the admin. Now the email form and `serve.py --as` both refuse platform-admin accounts.
- New code: `src/backend/admin_auth.py` (`AdminAuth`), `POST /api/admin/signin` in `server.py`.

### Security rules built in
- A plain `password` field in the file is refused at startup.
- Wrong username and wrong password get the same answer and take the same time.
- Five wrong passwords lock that username for fifteen minutes.
- Every admin sign-in, and every failed one, goes in the admin log (never the password).
- Until the script has been run, nobody can open `/admin`.

### Decisions
- A config file with a plain-text password was not secure enough (anyone with the repo or the file would have it), so the file stores a hash and stays out of git.
- "Hidden" means unlinked; the password is what keeps people out, not the URL.

### Tests
- `tests/backend/test_admin_auth.py` (15 tests).

---

## 2026-11-14 — Account management: admin tools and a user Account page

**Request:** "We need an admin page where we can access and manage accounts freely and then a user page that represents the full user run through. Can you create the secure methods that this requires"

### What changed
- **New backend module `src/backend/accounts.py` (`AccountsApi`)** with two separate sets of methods:
  - *Your own account:* read it, change your two data settings (`ai_uses_history`, `analytics_consent`; no API could set these before), sign out everywhere, delete your account (true erasure).
  - *Platform admins:* read any account in full, edit it (profile fields, visibility settings, sign-in email, platform-admin role), create an account, sign someone out everywhere, delete an account.
- **New routes:** `GET/POST /api/account`, `POST /api/account/signout-all`, `POST /api/account/delete`, `GET/POST /api/admin/account`, `POST /api/admin/account/create|signout|delete`.
- **Admin page** (`admin.html`): a "Manage" button on each user opens a panel to edit, view as, sign out or delete that account; a "Create an account" form; the log now lists every admin change. `admin.html?id=<person id>` opens an account directly.
- **New Account page** (`account.html`, in the sidebar): sign-in email, a "Getting set up" checklist (profile, first connection, community, first RSVP), data settings, sign out everywhere, delete my account.
- **Admin audit log** (`src/backend/audit.py`, written to `data/admin_audit.log`): admin, action, account and the names of changed fields, never the values.

### Security rules built in
- The acting person always comes from the session, never the request. Each admin method checks the stored admin flag first, before reading any input.
- Deleting needs the account's email typed back. Admins can't delete themselves from the admin page, can't change their own admin role, and the last platform admin can't be removed or deleted.
- Removing someone's admin role signs them out, so no old admin session lingers. Deleting an account ends its sessions.
- Admins can't change anyone's consent settings; those stay with the person.
- No account changes while "viewing as" someone (still read-only).
- The server now refuses any POST whose `Origin` is another site.

### Decisions
- "Manage freely" is done with explicit, logged admin methods rather than letting admins act as a user; view-as stays read-only as the v1.1 spec asks.
- The graph layer's "only you can edit your profile / RSVP visibility" rule now also lets a platform admin through (`may_manage` in `graph/rsvps.py`).
- Self-deletion is not written to the admin log (the account is meant to be gone).
- I read "a user page that represents the full user run through" as an Account page covering the account from first sign-in to deletion.

### Tests
- `tests/backend/test_accounts.py` (27 tests): non-admins refused on every admin route, validation, guard rails, logging, erasure, cross-site POST refused.

---

## 2026-11-14 — Search lists what's in your network first, above a divider

**Request:** "make it so everything you are connected to is above the top results and there is a clear divider separating the connected part and the top results."

### What changed
- **Search results are in two parts:** "In your network" first, then a ruled line and "Top results". Each part keeps its usual best-first order. If nothing in the results is in your network, there is no heading or divider.
- **What counts as in your network:**
  - a person you're connected to;
  - an org you belong to;
  - an event you're going to or marked Maybe, that you host, or whose main host is one of your orgs.
- **Paging:** the split holds across pages (all in-network results come before any others).
- **`graph/unified_search.py`:** `SearchResult.connected`, `SearchPage.grouped`. **`app_api.py`:** each item carries `in_network`. **`discover.js`, `discover.css`:** the heading and divider.

### Decisions
- **Plain Discover is not split.** With nothing typed and no filter ticked it stays one ranked list.
- **"Friends are attending" alone does not count** as in your network; most events in the demo have friends going, so the top part would swallow the list.
- When a vague request falls back to "what's coming up", the list is not split either.

### Tests
- `test_unified_search.py`: three new tests (in-network results come first across pages and each part stays best-first; what counts as connected for people, orgs and events; plain Discover is not split).
- **In a browser:** searching "robot" as Drew shows two events under "In your network", then the divider, then the Robotics Club and Carol.

---

## 2026-11-14 — Search and Discover answer about five times faster

**Request:** "do 1 and 2" (cache decoded records; match keywords before ranking).

### What was slow
- One search re-read about 18,000 records from the database and rebuilt each one from its stored text, mostly the same hosts, RSVPs and tags over and over. It also ranked all 413 events and only then dropped the ones that didn't match.

### What changed
- **`graph/sqlite_store.py`:** each distinct stored record is decoded once and reused (up to 100,000 remembered). It cannot serve stale data: the lookup key is the stored text itself, so a record that changes is looked up under its new text. Records are frozen, so sharing them is safe. This speeds up every page that reads the database, not only search.
- **`graph/discovery.py`:** `rank_all` takes an optional `keep(event, host, tag_ids)` filter that runs after the visibility checks and before ranking.
- **`graph/unified_search.py`:** the keyword check now runs through that filter, so only events that match are ranked.

### Measured (demo data, AI off, same machine)
- Keyword search ("robot"): about 0.64 s before, 0.10 s after.
- Discover with no query: about 0.49 s before, 0.13 s after.
- The first search after the server starts is a little slower (0.18 s) while the records are decoded for the first time.
- Ten queries compared before and after: identical results, order and scores.

### Not changed
- The AI call for sentence searches (not timed; it is a paid call).

### Tests
- New `tests/backend/test_decode_cache.py` (decoded once, a saved change is read back at once, bad stored text fails every time) and two tests in `test_unified_search.py` (non-matching events are never ranked; the filter only sees events the viewer may see).

---

## 2026-11-14 — "show me something rad" no longer comes back empty

**Request:** "the following comes up with no searches: show me something rad."

### What was wrong
- Search drops filler words ("show", "me", "something") and searches the rest. "fun" and "cool" were on the filler list but "rad" was not, so it searched for the word "rad", which is in no event, org or person.

### What changed
- **`graph/query_understanding.py`:** praise words that name no topic (rad, awesome, great, amazing, interesting, exciting, neat, sweet, sick, dope, epic, lit, best, whatever, random) are now filler. This also applies to keywords the AI reader returns.
- **`graph/unified_search.py`:** a safety net for words not on the list. When a *request* (a sentence) has words that match nothing, search answers with what's coming up instead of an empty page, keeps any type, topic or day the request gave, and says so: "Nothing matched “…”, so here's what's coming up."
- **Not changed:** a plain keyword or name that matches nothing ("zzyzx") still shows no results.

### Tests
- `test_unified_search.py`: four new tests (praise words, the vague request, the fallback with its note, a name that matches nothing).
- **In a browser:** "show me something rad" lists events; "show me some zzyzx stuff" lists events with the note.

---

## 2026-11-14 — Fixed the three failing tests (one was a broken Discover page)

**Request:** "fix the three failing tests."

### A real break: the Discover page's script did not run
- The "merging branch" commit (`963d7af`) pasted pieces of the older Discover page on top of the v1.1 one. `discover.js` declared `Api` twice, which is a syntax error, so the whole script failed to load. `discover.html` also had two search boxes with the same id.
- **Fix:** `discover.js` and `discover.html` are restored to the v1.1 versions (commit `0e6c4bc`).
- **Removed:** `find.js` and `find.css`, the older name-search panel. The v1.1 unified search replaced it and had already deleted these files; the merge brought them back. Nothing else uses them.

### Two tests that were out of date
- **`test_find_over_http`** checked the older name-search answer. It now checks the unified search: the answer's shape, that signed-out visitors get 401, and that a bad page number gets 400.
- **`test_a_browser_that_stops_waiting_is_not_reported_as_a_failure`** predates the sign-in gate, so it was turned away before reaching the code it tests. It now signs in first. The server fix it covers was never broken.

### Not changed
- `graph/directory.py` (the older name search on the server) is still there and still tested, but no page calls it any more.

### Tests
- Full suite: 1981 passed, 4 skipped, none failing.
- **In a browser:** the Discover page loads and a search shows results.

---

## 2026-11-14 — The network bubble draws each connection's line to the orgs you share

**Request:** "draw each connection's line to the orgs we share."

### What changed
- **Before:** an org you share with a connection was drawn once, with only the center's line to it. The connection's membership showed only indirectly (they sat closer in).
- **Now:** every person in the bubble gets an accent-colored line to each org in the bubble that they belong to. The org is still drawn once. The key has a new entry, "In the community".
- **`graph/network.py`:** `NetworkMap` has a new `memberships` field, (person id, org id) pairs for the people and orgs already on the map. `/api/network` sends it as `memberships`.
- **`network-data.js`, `network-layout.js`:** the page reads the pairs (dropping any that name someone or something not on the map) and draws them; members are also pulled gently toward their org.

### What did not change
- Nobody new appears on the map: the lines only join people and orgs that were already shown.
- A membership someone has hidden from you is not drawn (it uses the same visibility check as the rest of the map).
- An org's own map is unchanged: its members already have a line to it.

### Tests
- New `tests/backend/test_map_memberships.py`: shared org is tied, an org you aren't in is not, a private membership is not drawn, mutual friends on a connection's map are tied, an org's own map adds nothing.
- **In a browser:** on Drew's map, three connections now have lines to the Alpha Beta, Gamma Chapter.

---

## 2026-11-14 — The Connect button sends a connection request

**Request:** "make the connect button actually send a connection request."

### What was wrong
- The button on a person's page was already wired to the server (`POST /api/connect`), but it only switches on when it knows whose page it is. The page's data reader (`network-data.js`) was dropping the person's id, so the button was always greyed out.

### What changed
- **`network-data.js`** keeps the person's id, so the button is live on the page of anyone you aren't connected to.
- **`profile-render.js`:** pressing **Connect** sends the request and the page redraws with **Request sent** (no full reload). If they had already asked you, the button reads **Accept connection** and pressing it connects you. While it's working it says "Sending…"; if it fails, the button comes back and the reason shows underneath.
- **`network.js`** passes the redraw so the page updates in place.

### Tests
- `test_profiles.py`: a request shows as "pending_out" on your side and "pending_in" on theirs, pressing twice doesn't duplicate it, asking back accepts, and the page script passes the id through.
- **In a browser:** on a stranger's page the button went from "Connect" to "Request sent", the server listed the outgoing request, and I then cancelled it so the demo data is unchanged.

---

## 2026-11-14 — "Can't connect to the database": the local demo database was out of date

**Request:** "the software seems to not be able to connect to the database."

### What happened
- **The database connection was fine.** The server was reading `data/test.db` and returning events and topics.
- **The local `data/test.db` had been seeded before the v1.1 sign-in work.** None of its demo people had an email. So signing in as `drew.demo@northeastern.edu` (automatic now that sign-in is off) found nobody and created a brand-new, empty "Drew Demo" account: no connections, no orgs, no events. That empty account is what looked like a missing database.

### Fix
- **Re-seeded `data/test.db`** with the current seed, where the demo people have their `<name>.demo@northeastern.edu` emails. Drew is the real demo Drew again (8 connections, 1 org, upcoming events).
- **The old file is kept** as `data/test.db.before-reseed-2026-11-14` (not in git). Delete it once you're sure nothing in it is needed.
- **No code changed.** `data/` isn't in git, so each teammate whose database predates v1.1 needs to run `uv run python scripts/seed_test_db.py --reset` once, then restart the server.

---

## 2026-11-14 — The .edu sign-in step is temporarily off (one switch turns it back on)

**Request:** "can you temporarily disable the .edu sign in part, but make it so it is easy to re-enable."

### What changed
- **Sign-in is skipped by default.** Running `scripts/serve.py` no longer sends you to the page that asks for a Northeastern email: you're signed in automatically as the demo account (`drew.demo@northeastern.edu`; pick another with `--as <email>`). Everything else behaves as it does when signed in, and the sign-in form still works if you sign out and want to switch accounts.
- **To turn sign-in back on:** set `LOGIN_REQUIRED = True` in `src/backend/config.py`. That one line is the whole change.
- **For a single run:** `serve.py --login` asks for sign-in whatever the switch says, and `serve.py --no-login` skips it.
- **The server prints a warning** at start-up while sign-in is off, with these instructions.

### Not changed
- **Who may sign in.** The form still only accepts `@northeastern.edu` addresses (`ALLOWED_EMAIL_DOMAINS`, same file).
- **The gate itself** (`server.py`) and its tests. This reuses the existing development option; only the default moved into the config.

### Tests
- `test_access.py`: the switch decides when no flag is given, and a flag wins for that run.

---

## 2026-11-14 — Search for people, organizations and events by name

**Request:** "add people search, organization search, events search."

### What you can do now
- **Type a name in the Discover search bar.** From two characters on, a panel under the bar lists matching **People**, **Organizations** and **Events**, each with a count. It updates as you type and costs nothing; pressing Search still runs the AI search for events by description.
  - **People** open their page on the Network tab. Your connections come first and are marked "Connected", with what you have in common.
  - **Organizations** open their page (kind, website, upcoming events). Ones you belong to say "You're a member".
  - **Events** open their day on the Calendar.
  - Each kind shows up to 8 results and says how many more there are.
- **You can now open the page of someone you aren't connected to, or an org you aren't in.** You see their page as far as they allow (a locked profile shows only name, badge and colors). Their network is not shown; a note takes the bubble's place. Before, these links fell back to your own page.

### Backend
- **New `DirectoryService`** (`graph/directory.py`, `graph.directory`): `find(viewer_id, text, now, limit=8)` returns matching people, orgs and events with totals.
  - **People:** only people the viewer may see; never yourself; matched on the name only (not bio, About or email). Logged-out visitors find nobody.
  - **Orgs:** only orgs the viewer may see, by name.
  - **Events:** the Discover search with the text as a filter (title, description, place), so the same visibility and ranking rules apply.
  - **Matching:** ignores case; every word typed must appear; names starting with the text come first. The demo data's "[Demo]" and "(demo role)" tags aren't searchable.
  - **Limits:** 2 to 100 characters, at most 25 results per kind.
- **`GET /api/find?viewer=&q=`** (`network_api.py`, `demo_api.py`, `server.py`).
- **`GET /api/network`** now answers for any person or org the viewer may see, with `network_open: false` and an empty map when the viewer isn't connected or isn't a member. Opening the map itself is still refused by `NetworkService`.

### Frontend
- New `find.js` and `find.css` (the results panel); `discover.html` and `discover.js` hook it to the search bar. `network.js` and `network-data.js` handle a closed network.

### Decisions to confirm
- **Anyone signed in can find anyone whose account is visible to signed-in users** (the default). A person who sets their visibility to connections-only is found only by their connections. There's no separate "don't show me in search" setting yet.
- **The Connect button still only shows the state.** Search makes sending a request the obvious next step; it isn't built.

### Tests
- **New `tests/backend/test_directory.py`** (51 runs): matching and ranking, connections first, hidden people and orgs not found, logged-out finds no people, name-only matching, drafts and members-only events hidden from outsiders, caps and totals, length limits, a fuzz test, and the API.
- `test_person_map.py`: a stranger's and a non-member org's page open with the network closed. `test_server.py`: the endpoint over HTTP.
- Full suite apart from the `test_audit_*` files: 1864 pass. Checked in a browser: typing "ri" lists all three kinds, and a non-connection's page opens with the note in place of the bubble.

---

## 2026-11-14 — Server no longer logs a crash when the browser stops waiting

**Request:** "can you look at error.md and figure out what happened? I believe it was when I tried searching ben in the search bar and it was unable to find any items."

### What happened
- **The traceback in `error.md` is not from the search.** It is from `GET /api/calendar`: the browser closed the connection before the server finished sending the calendar (leaving the Calendar page mid-load does this). The server then tried to send a "something went wrong" answer down the same closed connection, which failed again and printed the long second traceback. No data was lost and nothing was actually broken.
- **"ben" found nothing because nothing matches it.** The Discover search bar searches events only. The demo data has no person, org or event with "ben" in its name, title or description.

### Fix
- **`server.py`:** a connection the browser closed (`BrokenPipeError`, `ConnectionResetError`) is now logged as one short line and not treated as a failure, so there is no traceback and no second attempt to answer.

### Tests
- `test_server.py`: a dropped connection is not reported as a failure and the server keeps serving.

---

## 2026-11-14 — Profile page and network bubble combined, on real data, with editing

**Request:** "imagine combining profile page information display and then displaying the small graph bubble in the same page. Then in the profile page you can change settings, layout of the public profile display, colors, what events you want shown to who, etc."

This replaces the thin profile header and large circle described in the entry below.

### What you can do now
- **One page per person: their profile with their network bubble inside it.** James's profile design (card with name, badge, bio and website; sections for About, Top 3, Orgs, Events) now runs on real data, and "Network" is one of its sections: a small circle (400px) you can drag or move with the arrow keys when the network doesn't fit.
- **Network tab:** starts on your page. Clicking a connection in the bubble opens their page and bubble, in the colors and layout they chose. Clicking a community opens its page (kind, website, upcoming events) and its bubble of members. "Back to you" and "Edit your page" are in the header.
- **Profile tab:** your own page, with **Edit page** and **View as visitor**. Editing has a live preview and covers:
  - **Text:** display name, bio, About, Top 3, website.
  - **Colors:** background and outline; the bubble takes them on too.
  - **Layout:** tick which sections visitors see and move them up or down, including where the network bubble sits (or hide it).
  - **Who can see what:** your profile (everyone signed in, connections only, only you), the events you're going to (same choices), and whether to hide who you're connected to.
- **Locked profiles:** if someone limits their profile and you don't qualify, you see their name, badge and colors and the network you share, nothing else.

### Backend
- **`Person`** (`objects/person.py`) gains `bio`, `top3_title`, `top3_items`, `website` (https only), `color_background`, `color_outline`, `profile_visibility` and `profile_sections`, all with defaults and all validated by the record. `profile` stays as the About text. Existing databases load without re-seeding.
- **New `ProfileService`** (`graph/profiles.py`, `graph.profiles`):
  - **`view(person_id, viewer_id, now)`**: full or locked, connection state, and the orgs, hosted events and "going" events the viewer may see. Hidden people look missing.
  - **`update(person_id, by_person_id, **changes)`**: only you, only the listed fields, every limit checked, all or nothing. Changing who sees your events updates your existing RSVPs.
- **API** (`network_api.py`, `demo_api.py`, `server.py`): `GET /api/network` returns the full profile (with `settings` on your own); new `POST /api/profile` saves edits, with its own 8 KB limit.

### Frontend
- **Split James's `profile.js`** (732 lines, sample data) into `profile-render.js` (renderer, rules, theme), `profile-editor.js` (the editor, plus Layout and Who-can-see-what) and a new `profile.js` (the page). `profile-mock.js` is deleted; nothing uses it.
- **New `network-data.js`**: loads and checks the server's answer for both pages. `network-view.js` gains `NetworkBubble`. `network.js` now draws people with the shared renderer.

### Decisions to confirm
- **No usernames yet.** The proposal makes `username` required, which would break the seed data and 26 test calls and needs agreeing with the team. Pages are addressed by id for now (`network.html?center=<id>`).
- **The Connect button only shows the state** ("Connected", "Request sent"); sending requests from the page isn't wired up.
- **On the Network tab the bubble always shows,** even if the person left the network section out of their layout: it appears under their page. On their own Profile tab it follows their layout.
- **A person's Orgs section lists every org the viewer may see them in,** including ones the viewer hasn't joined. The bubble still shows only what the viewer can open.
- **Saving keeps a demo person's "(demo role)" tag** unless the name itself was changed.

### Tests
- **New `tests/backend/test_profiles.py`** (142 runs): every limit just inside and outside, only you can edit, protected fields refused, failed edits change nothing, full vs. locked for stranger / connection / self, connection states, hidden looks missing, private memberships and RSVPs never leak, upcoming-only events, and the API including malformed bodies, the size limit over HTTP and the demo-name rule.
- Full suite apart from the `test_audit_*` files: 1810 pass.
- **In a browser:** edited bio, background color, section order, a hidden section and profile visibility through the real form, saved, and confirmed the page redrew with them; then restored that demo person. No script errors on either page.

---

## 2026-11-14 — Network page: profile on top, network in a fixed circle you can move around

**Request:** "make it so the network is inside a certain size circle, and if the network doesn't fit in the circle, only show what does fit, and allow arrow key or touch movement to navigate… The circle should be positioned below whoever you are viewing… If you click another node on the graph it should appear different profile info. If it is an organization, it should navigate to the organization page and their graph."

### What you can do now
- **Profile first, network below.** The Network tab opens on your own profile (name, role, how many connections and communities), with your network in a circle right under it. Clicking a node swaps both: the profile becomes theirs and the circle shows their network.
  - **A connection:** their name and role, what you have in common (mutual connections, shared communities), and their profile text if they wrote one.
  - **A community:** its page: what kind of org it is, a Website button when it has one, how many members you're connected to, and its next three upcoming events (each links to that day on the Calendar). Its network of members is below. There was no organization page in the app before, so this is it; the address is `network.html?center=<org id>`.
- **A fixed-size circle.** The map is always the same circle (600px wide, smaller on a phone). Whatever fits is shown and the rest is cut off at the edge, which fades to show there's more.
- **Moving around a big network:** drag with a mouse or finger, or press the arrow keys while the map has focus. Tabbing to a node that is out of sight brings it into view. "Back to the middle" returns to the center. A network that fits doesn't move, and the hint only appears when there's more to see.
- **The lists** of communities and connections moved under the circle.

### Backend
- **New `src/backend/network_api.py`**: `network_json` builds the answer to `GET /api/network`, now with a `profile` for whoever is in the middle. Moved out of `demo_api.py` to keep that file under 500 lines.
  - **Person:** `name`, `role`, `about`, `verified`, `in_common` (null for yourself). Never the email or any setting.
  - **Org:** `org_kind`, `website` (http/https only), `upcoming_count` and up to three `upcoming` events the viewer may see (published, not cancelled, not ended).

### Frontend
- **New `network-view.js`** (`NetworkView`): the circle, clipping, dragging, arrow keys and the nodes. `network-layout.js` no longer squeezes nodes into a box; it reports how far the network reaches. `network.js` is the page: loading, profile, lists.
- **Layout tweak:** someone tied to many others is pulled less by each tie, so a tightly knit group no longer collapses into a clump.

### Decisions
- **The org "page" lives on the Network tab** rather than a new separate page, so the profile-then-circle layout is the same for people and communities.
- **Profile counts only cover what's on the map** (your own connections and communities), in line with leaving out nodes you can't open.

### Tests
- `tests/backend/test_person_map.py` (70 runs) adds the profile: yours, a connection's in-common, an org's kind and upcoming events, cancelled and draft events left out, and website links.
- Checked in a browser: three arrow presses move the map and stop at the limit, "Back to the middle" resets, a touch drag moves it, and a network that fits stays put. Screenshots at desktop and phone widths.

---

## 2026-11-14 — Network map lines: bold for connections, light for "close", none otherwise

**Request:** "I wanted a mix of bold and light. Bold represents a connection/friend request that the parties accepted from each other… light is those who are connected within a certain proximity in the backend graph, and no line means the people don't really have a connection."

This replaces the line styles described in the entry below.

### What the lines mean now
- **Bold:** the two people accepted a connection with each other. It looks the same whoever is in the middle.
- **Light, dashed:** the two people aren't connected, but are close in the network: they share a connection or a community, not counting the node in the middle (everyone on a map shares that).
- **No line:** no real tie between them.
- **Green:** a community's tie to the node in the middle (membership), unchanged.
- **Layout:** connected people are pulled side by side; "close" people are pulled together more loosely.

### Backend
- **`NetworkMap.near`** (`graph/network.py`): pairs of people on the map who are not connected but share at least one other link the viewer may see. Never overlaps `links`. Computed on demand, never stored.
- **`GET /api/network`** returns `near` alongside `links`.

### Decision to confirm
- **"Proximity" is two steps:** two people count as close when one link separates them (a shared connection or community). A shared community only counts if the viewer may see both memberships, so private memberships don't produce a line. A light line does hint that two people have something in common without saying what.

### Tests
- `tests/backend/test_person_map.py` (63 runs) adds: near through a mutual connection, near through a shared org, sharing only the center is not near, connected people are linked and not near, private memberships don't count, and org maps.

---

## 2026-11-14 — Network map: only nodes you can open, random layout, lines between connected people

**Request:** "make it so the nodes you don't have access to simply don't show on the graph, and then randomize the graph and make sure to connect the people in the graph if they are connected and add lighter/dashed lines and put the ones that are more similar or closer on the backend graph closer together."

This replaces the greyed-out nodes and the fixed circle described in the entry below.

### What changed
- **Nodes you can't open are gone,** not greyed out. A map only ever shows you, your connections and your orgs. On a connection's map that means the connections and orgs you have in common; on an org's map, the members you're connected to. The server leaves the rest out, so the page never receives them.
- **Connected people are joined.** Any two people on the map who are connected get the same solid dark line, whoever is in the middle (first built as a lighter dashed line; changed on request so a real connection always looks the same). Green lines join a community to the middle.
- **Close nodes sit together.** Each node has a `closeness`: how many of the middle node's other links it also has (mutual connections and shared orgs). The more it shares, the nearer the middle it sits, and connected people are pulled side by side.
- **The layout is random.** Nodes start at random spots and settle into place, so the same network is drawn a little differently each visit.
- **Side panel:** the "Communities you haven't joined" section is gone (those orgs no longer show); each person's row says how many others on the map they're connected to.

### Backend
- **`NetworkMap`** now has `links` (pairs of person ids) and `closeness` on `MapOrg` / `MapPerson`; `shared`, `mutual` and `can_open` are gone because everything returned can be opened. People are listed closest first.
- **Links follow the existing rules:** a connection between two of your friends is listed only if you're allowed to see it (for example, not when one of them hides their connections).
- **`GET /api/network`** returns `links` and `closeness`.

### Decisions
- **"Similar" is counted from the graph, on demand, and never stored,** in line with `user_Orgs.md` ("no stored similarity between people"). It uses only links the viewer may already see.
- **Trade-off to be aware of:** `network_plan.md` asks the view to highlight a connection's communities you haven't joined ("where discovery happens") and not to draw relationships between other people. This request overrides both.

### Tests
- `tests/backend/test_person_map.py` rewritten (51 runs): nodes you can't open are absent, everything on a map can be opened, links between shown people (including hidden-connections and off-map cases), closeness and ordering, org maps, and the API. Full suite apart from the `test_audit_*` files: 1644 pass.

---

## 2026-11-14 — Network map shows direct links only; orgs open to show members

**Request:** "hide any connections that aren't directly connected through connection or if you are under an organization. If you click on a node, it rerenders the circle with the clicked node in the middle and the connections directly connected to that node shown, but doesn't let you look at the second peoples individual graph network… This should also be applied to organizations where they don't display members unless you click on the organizations node."

This replaces the clustered layout described in the entry below.

### What changed
- **Only direct links are drawn.** The node in the middle has a circle of what is directly linked to it, and nothing else. A person's map no longer shows which of their connections are in which org.
- **Click a node to put it in the middle:**
  - **A connection of yours:** their connections and orgs.
  - **An org you belong to:** its members (the ones you're allowed to see). Members never appear anywhere else.
- **That is as far as it goes.** People you aren't connected to and orgs you aren't in show on the map but can't be opened; clicking one says why. So you only ever see people linked to you directly or one step beyond.
- **Side panel:** orgs you're in get a "Members" button; people you're connected to get "Open".

### Backend
- **`NetworkService.node_map(viewer_id, center_id=None)`** picks the right map; `person_map` no longer returns shared-org groupings; new **`org_map`** returns an org's visible members and raises `PermissionDeniedError` unless the viewer is a confirmed member. `PersonMap` is renamed `NetworkMap`; `MapOrg.can_open` is new; `MapPerson.org_ids` is gone.
- **`GET /api/network`**: `center` may be a person or an org; the answer includes `center.kind` and `can_open` on orgs.

### Decision to confirm
- **Orgs you haven't joined stay closed**, even though member lists are public elsewhere in the app. Opening a friend's org would show people three steps away from you, which the request rules out.

### Tests
- `tests/backend/test_person_map.py` is now 47 runs: org maps (members, order, private members hidden, non-members and pending members refused), a member of your org who isn't your connection can't be opened, `node_map` dispatch, and the API for both kinds. Full suite apart from the `test_audit_*` files: 1640 pass.

---

## 2026-11-14 — Network page: a map of a person's communities and connections

**Request:** "can you read network_plan.md and implement the network section of the app?" (the plan's "How the network view works").

### What you can do now
- **Network page** (`src/frontend/network.html`, `network.js`, `network-layout.js`, `network.css`) replaces the "Coming soon" placeholder. It uses the same "Viewing as" person as Discover and Calendar.
  - **The map:** the person in focus is at the center. Their orgs are hubs around them, and each of their connections sits by the org they share with that person (between the hubs if they share several). Connections who share no org sit in their own group, tied to the center. Links between the other people are never drawn.
  - **Tap a connection** (on the map or the "Open" button in the list) to see their network with them at the center. The address keeps it (`?center=<id>`), so Back and Forward work.
  - **What you share and what's new:** green marks communities you're in too and people you're connected to; dashed amber marks communities you haven't joined ("where you'd meet new people"); grey marks people you aren't connected to. The side panel lists the same things in words.
  - **Tap an org** to highlight its cluster.
- **Only your own connections can be opened.** A friend of a friend shows on the map, but tapping them explains that their network stays closed. A link to a network you may not open falls back to your own with a note.
- **You only see what each person allows:** the map is built from the existing visibility rules, so two people can see different maps of the same person.

### Backend
- **`NetworkService.person_map(viewer_id, person_id=None)`** (`graph/network.py`) returns a `PersonMap`: the center, their orgs (`MapOrg`, with `shared`), and their connections (`MapPerson`, with the orgs they share with the center, `mutual`, `is_viewer`, `can_open`).
  - **Who may open it:** yourself or an accepted connection; anyone else raises `PermissionDeniedError`. Orgs, hidden people and missing ids all look like "not found".
  - **Capped** at 60 connections (`MAX_MAP_PEOPLE`), with a `truncated` flag.
- **`GET /api/network?viewer=&center=`** (`demo_api.py`, `server.py`): viewer required; names are sent without the demo prefixes.

### Decisions
- **The layout is computed, not simulated.** Positions come from simple geometry, so the same network always draws the same way.
- **"Full view only for your own connections"** is enforced on the server, not just hidden in the page.

### Tests
- **New `tests/backend/test_person_map.py`** (32 runs): contents, grouping by shared org, shared vs. new orgs, who may open a map (stranger, pending connection, logged out, org, hidden person), hidden connection lists, private memberships, two viewers seeing different maps, the cap, and the API.
- **`test_server.py`:** the endpoint over HTTP, and the two new scripts added to the "never renders server text as HTML" check.
- Checked in a browser at desktop and phone widths.

### Also restored
The three entries below this one ("Co-hosting gaps fixed", "I'm going…", "Faster AI search") had been dropped from this file by a later merge; they are back, unchanged, from commit `ddb8a24`.

---

## 2026-11-14 — Co-hosting gaps fixed, with edge-case and fuzz tests

**Request:** "can you write tests that help you determine the bugs and fix, and also test edge cases" (about caumartin-maker's `tests/backend/test_cohosting_gaps.py`, whose 14 tests were failing).

### Fixes (all 14 gap tests now pass; nothing in that file was changed)
- **Inviting co-hosts:** refused once the event is cancelled, archived or over (`status_at(now)` is ENDED). Drafts can still invite.
- **Accepting:** refused if the event is cancelled or archived, or the link was declined or withdrawn (clear `DomainRuleError`). Accepting twice returns the link unchanged. Nobody can approve their own org's or their own request to join; another host must.
- **Withdrawing:** whoever sent a pending invitation can withdraw it (before, only the invited party or the primary could).
- **Cancel and archive:** only someone acting for the primary host (any admin of a primary org still can). Both close every pending invitation and request; accepted co-hosts stay.
- **Erasing the primary host:** the co-host that *accepted* first takes over, not the one invited first. New `Hosts.accept_order` (1, 2, 3…); links saved before it existed (0) come last.
- **Member lists:** a membership or profile set to connections-only is listed only for that member and their connections; private stays hidden; the default stays public. The network view follows the same rule. `RosterService` now takes `ConnectionService`.
- **Host calendar window:** an event shows if it overlaps the window, so one under way at `starts_after` is kept.

### Tests
- **New `tests/backend/test_cohosting_fixes.py`:** accepting twice, accepting on an archived event, withdrawn-link message, a person admin of both sides, inviting at exactly `ends_at`, sender vs. outsider withdrawal, co-host can edit but not cancel, cancel keeps accepted co-hosts, promotion order (reverse acceptance, a removed co-host skipped, legacy links), connections-only lists for connected viewers / self / logged out, connections-only profiles, network view, exact window edges, and a Hypothesis fuzz test of random invite/request/accept/remove/cancel/archive/erase sequences checking: never two primaries, no open links on cancelled/archived events, and a clean integrity audit.
- **Updated** `test_edge_graph.py`'s window test to the overlap rule (it pinned the old start-only window).
- Full suite: 1590 pass.

### Product decisions to confirm
The gap file marked four of these as needing a decision; I implemented its proposed behaviour: connections-only members on lists, inviter withdrawal, acceptance order for takeover, and primary-only cancel/archive.

---

## 2026-11-14 — "I'm going", "Maybe" and a star, wired to a working calendar

**Request:** "Add the I'm going, maybe, add a star icon and make it update the calendar, and then add errors to make sure the calendar can't break (along with anything else you think could raise errors), and make a way to unclick the I'm going button and remove from catalogue of events."

### What you can do now
- **On every Discover card:** ✓ **I'm going**, ? **Maybe** and ☆ **star** (`src/frontend/shared.js`, `EventActions`, styled in `event-actions.css`).
  - **Each button toggles:** clicking an active choice clears it, so un-clicking "I'm going" removes your RSVP.
  - **Updates show at once:** if the server says no (for example "this event is full"), the button goes back and the reason appears.
  - **The card redraws from the server's answer,** which updates the "You're going" badge and the going count, and a status line confirms "…: you're going. Your calendar is updated."
  - **When the buttons are disabled:** while logged out ("choose who you are first"). On cancelled events, Going and Maybe are disabled unless already set, so you can still undo.
- **The calendar** (`src/frontend/calendar.js`) now shows the events of the person you're viewing as. It's the same person as on Discover, chosen in a matching "Viewing as" menu and remembered across pages.
  - **Day cells** show your events as chips: going in solid green, maybe outlined, starred with ★, hosting in dark, and cancelled struck through. They also show "+N more" and "N on campus" for everything else, and there's a key above the grid.
  - **The day panel** lists *My events* and *Community events*, with time, place, host and tags (Hosting, Your org, Cancelled, Draft), plus the same three buttons. Changing them reloads the calendar, so un-clicking "I'm going" moves the event out of *My events* straight away.
  - **Deep links:** `?date=YYYY-MM-DD` opens that day; malformed dates are ignored.

### Backend
- **`Starred`** (`objects/edges.py`): Person → Event, always PRIVATE.
  - **`StarService`** (`graph/stars.py`, `graph.stars`) handles star (idempotent), unstar (hard delete, always allowed) and `starred_event_ids`.
  - **Rules:** you can only star listed events you can see that haven't ended. A star is never counted or shown to anyone, and erasing an account removes its stars.
- **`PersonalCalendarService`** (`graph/my_calendar.py`, `graph.my_calendar`): for a window of at most 62 days, it lists every event the viewer may see that overlaps it.
  - **Mine:** events you host (yourself, as an org admin or as a co-host), are going to, said maybe to, or starred.
  - **Community:** everything else, capped at 400, with `community_truncated` reported. Your orgs' events are marked `my_org`.
  - Drafts appear only for their editors, archived events never appear, and cancelled events stay, flagged.
  - **Decision:** "My events" are only what you personally chose. Your org's events used to count too, but then un-clicking "I'm going" on a chapter meeting left it in "My events", which isn't what was asked.
- **New API endpoints** (`src/backend/demo_api.py`, split out of `server.py` to keep files under 500 lines):
  - `POST /api/rsvp {viewer, event_id, status: "going"|"maybe"|null, near}`
  - `POST /api/star {viewer, event_id, starred}`
  - `GET /api/calendar?viewer&start&end` (ISO 8601 with a time zone)

  Discover and search results now include `starred`. **The search cache refreshes your RSVP, star and count** when it reuses an answer, so a cached search never shows stale state.

### Making it hard to break
- **Calendar page:**
  - if loading fails, the grid still works and a banner offers **Retry**;
  - answers to requests that have since been superseded (for example after quick month changes) are ignored;
  - each server entry is checked: bad or missing dates are skipped, a missing title becomes "Untitled event", and an end before the start is fixed up;
  - multi-day events appear on each day they cover, at most 14;
  - long days collapse to "+N more", and long titles are cut off cleanly;
  - storage being blocked doesn't matter;
  - an unknown saved person falls back to the first one.
- **API errors are now distinct:** missing → **404** "that isn't available (it may have been removed)"; not allowed → **403**; rule broken → **400** with the reason; database busy (two saves at once) → **503** "busy right now, please try again"; anything else → **500**, without internal details. Input checks cover the viewer (it must be a real person, and it's required to RSVP or star), the event id (type and length), the status (only going, maybe or null), `starred` (a real true/false), and dates (valid, with a time zone, start before end, at most 62 days).
- **Fuzzing found a real crash:** `{"status": []}` crashed the RSVP endpoint with `TypeError: unhashable type`. It now returns 400.
- **No HTML from server data:** none of the three scripts uses `innerHTML`/`outerHTML`/`insertAdjacentHTML`/`document.write`/`eval`, and a test enforces that. Icons are built from element data.

### Verified
- **Tests:** `tests/backend/test_stars_and_calendar.py` adds 95 runs, covering:
  - stars: privacy, idempotency, visibility, ended and archived events, erasure;
  - the calendar: mine vs community, un-clicking, my-org marking, drafts, hidden, archived and out-of-window events, events spanning the window, logged-out viewers, the cap, bad windows, time zones;
  - the endpoints: set, change and clear; star toggle; `starred` in results; validation; RSVP rules through the API; cached search freshness;
  - Hypothesis fuzzing of the calendar, RSVP and star inputs, which must never crash.

  In total, 1515 pass, excluding the teammate's in-progress `test_cohosting_gaps.py`, which still has 28 failing. Ruff is clean.
- **Over HTTP against the large demo world:** going → in My events; star → `["going","starred"]`; un-click both → gone. Bad viewer → 400, missing event → 404, list status → 400, bad dates → 400, a year-long window → 400.
- **Headless Chrome screenshots:**
  - Discover cards with the three buttons;
  - Drew's November calendar, with hosting, going and chapter-meeting chips and "N on campus" counts;
  - the day panel for 18 November, with *My events* (the study jam he hosts) and *Community events*, each with buttons.
- **Backend reference:** `docs/BACKEND_REFERENCE.md` was regenerated (373 entries, all links checked).

### Not done
- **Testing the clicks themselves:** the in-browser click flow was checked over HTTP and in screenshots, not with a browser automation test (Playwright isn't set up here).
- **Week and Day views** of the calendar are still "coming soon", as in the teammate's shell.
- **The star's meaning:** it's a private bookmark. If it should mean something else (for example, notifying friends), that's a product decision.

---

## 2026-11-14 — Faster AI search: Sonnet 5.5 for the agent, Haiku 5.5 for the single call

**Request:** "Can you switch the model to sonnet or haiku? A faster model that would still be appropriate for the analysis of both the data and the sentence?"

### What changed
| Path | Before | Now | Why |
|---|---|---|---|
| **Search agent** (`search_agent.py`, `AGENT_MODEL`) | `claude-opus-5-5`, effort medium | **`claude-sonnet-5-5`**, effort medium | A multi-step tool loop that reads the person's data, chooses searches and judges fit needs real judgment. Sonnet 5.5 is faster and half Opus's price ($2 / $10 per MTok), and `medium` is Anthropic's starting point for multistep tool use on it. |
| **Single-call search** (`claude_interpreter.py`, `DEFAULT_MODEL`), also the agent's fallback | `claude-opus-5-5`, effort low | **`claude-haiku-5-5`**, effort low, thinking off | Scoring one list of events against one sentence is classification-style work, which Haiku is built for ($0.10 / $0.50 per MTok). |

### API differences handled
- **Haiku 5.5 has no server-side refusal fallback.** Sending `fallbacks` would do nothing, and a list form would return a 400. A new `refusal_fallback(model)` adds the fallback beta and `fallbacks: "default"` only for models that support it (Sonnet and Opus). A refusal from Haiku simply falls back to keyword search.
- **Haiku 5.5 thinks by default.** For this one scoring call, thinking mostly added latency, so `thinking_options(model)` sends `{"type": "disabled"}` for Haiku only. That's allowed at effort low to high, and the call uses no tools, so the documented caveat about tools combined with JSON output doesn't apply. Sonnet and Opus keep adaptive thinking.
- **Shorter answers:** the single-call prompt now asks for reasons only on scores of 0.5 or higher, and blank reasons for poor fits. The page only shows reasons for good fits, so nothing visible is lost.

### Verified live (on the large mock world, as Drew, near campus, "fast paced puzzles that make me think")
- **Agent on Sonnet 5.5: 7.1 s end to end.** It read Drew's overview first, ran one targeted search and picked "Robotics study jam" (fit 0.95: "Timed coding puzzles in quick rounds, close by, and 2 friends are going"). It also flagged "Game night" as a weaker 0.45 fit.
- **Single call on Haiku 5.5:**
  - 16.1 s with thinking on;
  - 15.7 s once the answer was shortened;
  - **9.8 s with thinking off** (about 2 s of that is Python and database start-up).
  
  Every run picked "Robotics study jam" first (90%) with a clear reason.
- **Cost:** 5 live searches in total, about 5 cents.
- **Tests:** 1418 pass, excluding the teammate's in-progress `test_cohosting_gaps.py`. New tests cover `refusal_fallback`, `thinking_options` and choosing a different model. The existing tests now assert the new models. `docs/BACKEND_REFERENCE.md` was regenerated (359 entries, all links checked).

### Not done
- **Measuring quality properly:** there's no eval set, so the only quality check is these live runs. A small set of saved requests with expected picks would show whether either model misses things Opus would catch.
- **Lower agent effort:** if the agent needs to be faster still, effort `low` on Sonnet 5.5 is the next lever. Anthropic notes that at `low` it's more likely to stop before finishing on long tasks, which here would mean falling back.

---

## 2026-11-14 — Codebase audit: new tests and a bug report

**Request:** "Run through codebase again and write test cases and write any errors you find in a .md"

### Added
- **`docs/TEST_AUDIT.md`:** every bug found, with file:line, the failing test and what to do next. It also lists open policy questions and what was checked and found fine.
- **New test files** (all in `tests/backend/`; 41 tests fail on purpose, one for each bug, and 24 pass as new coverage):
  - `test_audit_server.py`
  - `test_audit_graph.py`
  - `test_audit_discovery_ai.py`
  - `test_audit_seed_export.py`

### Notes
- No source code was changed. The failing tests are meant to be fixed one by one.
- The committed `.venv` didn't have `anthropic` or `hypothesis`, so it couldn't run the suite. Both were installed with pip because `uv` isn't installed here.

---

## 2026-11-14 — Discover page with AI search, and a local demo server

**Request:** "Can you now do the discover page using the mockup database and the users, events, and orgs in it? Then hook the search function to a search bar on the top of the discover page?"

### Run it
```
uv run python scripts/seed_test_db.py --reset     # the large mock world (default --size large)
uv run python scripts/serve.py                    # http://127.0.0.1:8000/src/frontend/discover.html
uv run python scripts/serve.py --no-ai            # same, but search uses keywords (no API calls)
```

### Added
- **`src/backend/server.py`:** a small local web server, standard library only. It serves the frontend pages and a JSON API (`scripts/serve.py` starts it):
  - `GET /api/personas` lists the demo people you can view as, with Drew, Avery, Casey and Kai suggested first.
  - `GET /api/tags` lists the topics.
  - `GET /api/discover?viewer=&page=&near=1&tag=` returns one page of Discover, **10 per page** as in the plan.
  - `POST /api/search {"query", "viewer", "near"}` runs the **search agent**. It returns the understood goal, the steps (in plain language) and the picks.
  - `DiscoverApi` holds the API's logic without any HTTP, so it can be tested directly.
- **The Discover page** (`src/frontend/discover.html`, `.css`, `.js`) replaces the "Coming soon" placeholder and shares the calendar's look:
  - **The search bar at the top** sends what you type to the search agent. Results show "Looking for: …" with the agent's goal, a fold-out **"How we searched"** list of its steps, and its picks. Each pick has its fit reason highlighted, and "Back to all events" returns to browsing.
  - **A "Viewing as" persona switcher** works on the demo data only, as in the plan's persona switcher. Next to it is an **"On campus" toggle** for distances.
  - **Topic filters**, numbered pages with windowing (`‹ 1 … 4 5 [6] 7 8 … 42 ›`), loading placeholders, empty states and friendly errors.
  - **Event cards** show:
    - a date tile and the time and place, with distance;
    - the host;
    - badges such as You're going, Your org, Cancelled, Hosted by a student and Unverified listing;
    - the description and up to three reasons;
    - friends going, as initials with "Avery, Gale and 2 more going";
    - a likelihood meter ("96% likely for you") and the going count, which is hidden below 5.
  - The persona and the toggle are remembered (localStorage, with a fallback), and the search and page live in the URL (`?q=…&page=…`). The page works on phones: controls stack and the topics scroll sideways.

### Safety decisions
- **Demo only.** The server refuses to run on the production database. There's no login yet, so "viewing as" anyone is a demo feature, not authentication.
- **Local only.** It listens on `127.0.0.1` only.
- **Static files** come only from `src/frontend`, `public` and `app`:
  - every path is resolved and checked;
  - `..`, encoded traversal, NUL bytes, dotfiles and symlinks leading outside are refused;
  - `data/`, the source code and `.git` all return 404 (checked over HTTP).
- **Input validation:** every input is validated, including viewer, page, topic, query, JSON type and body size (4 KB). Errors are `{"error": …}`, and a 500 never shows internal details. Responses carry `nosniff`, `X-Frame-Options: DENY`, `no-referrer` and, for the API, `no-store`.
- **No HTML injection:** the page inserts server data with `textContent` only. A test checks that `discover.js` never uses `innerHTML`.
- **Cost control:**
  - identical searches (tidied and case-folded) are answered from an in-memory cache of 64;
  - only one AI search runs at a time;
  - `--no-ai` makes no API calls at all.

### Verified
- **Tests:** `tests/backend/test_server.py` (50, all pass) covers:
  - personas and topics;
  - Discover ranking, logged-out visitors, distances, topics and paging;
  - bad input of every kind;
  - search through a fake agent, including the cache, with no real API calls;
  - the production refusal;
  - the static path checks (12 traversal cases);
  - HTTP status codes, headers and error bodies, the redirect, serving the real page, no leaked internals, and listening on 127.0.0.1 only.
- **On the large mock world** (110 orgs, 881 people, 995 events; re-seeded, integrity check clean):
  - Drew's Discover lists 412 events and returns a page in about 0.5 s;
  - the persona list loads in 0.3 s;
  - a keyword search takes under 1 s.
- **Screenshots in headless Chrome:**
  - the browse view, the search view (with the fallback note) and page 6 of 42 at 1300–1440 px;
  - a phone layout at 500 px (headless Chrome can't go narrower; the layout is fluid below that).
- **Live AI search through the page hasn't been run**, to avoid paid calls. The same search agent ran live earlier.

### Other changes
- **Backend reference:** `docs/BACKEND_REFERENCE.md` was regenerated. It now has 357 entries, including the server and the new `seed_bulk.py` / `seed_catalog.py`, with every link checked.

### Not done / noticed
- ⚠️ **Teammate's tests failing:** the committed `tests/backend/test_cohosting_gaps.py` (from a teammate) has 28 failing tests out of 30. It reads like tests written ahead of fixes that haven't been made yet. It isn't caused by this change: everything else passes (1413 tests).
- **RSVPing from a card** isn't built yet (the plan's demo step 5).
- **Search speed:** a live agent search takes several seconds; the page says so while it works.
- **Persona menu:** it lists all 881 demo people, which is long. A searchable picker would be better.
- **Changelog repair:** the "Backend reference document" entry was dropped when the teammate's mock-data branch was merged (`e12f26f` kept their copy of this file). It's restored from commit `c13fa49`.

---

## 2026-11-14 — Large generated mock world for the test database

**Request:** "Create a large amount of mock up user organizations and events and all the data under them put into the data mock up base."

**What changed:** `scripts/seed_test_db.py` now adds a large generated world on top of the hand-built demo by default. A full seed takes about 6 seconds and produces roughly:
- **112 orgs** across three fictional campuses: Northbridge University (reusing the hand-built university and IFC), Riverside College and Harborview Institute. There are 10 national fraternities and sororities, 5 chapters per campus, an IFC, Panhellenic and Club Sports Council per campus, and 22 clubs per campus.
- **~880 people**: org admins and 250 students per campus.
- **~1,000 events**: months of past events (ended, some archived), upcoming events (some drafts, some cancelled, some members-only), weekly meeting series, events co-hosted by two orgs, and events hosted by students.
- **~10,000 RSVPs, ~2,700 friendships, ~2,200 memberships, ~1,900 interests and ~1,400 tag links**, plus 18 new curated tags (music, tech, outdoors and others).

Use `--size small` for a small world or `--size demo` for the hand-built demo only.

**How:**
- New `backend/seed_catalog.py` holds the invented content: campuses, buildings, club and chapter templates, event templates and names.
- New `backend/seed_bulk.py` (`_BulkWorld`) builds the world. Every write goes through the normal services, so claims, admin checks, hierarchy kinds, co-host acceptance and RSVP rules all apply, and `check_graph.py` reports no problems.
- `seed_mock_data` takes an optional `bulk: BulkScale` argument. Its default is `None`, so existing callers and tests get exactly the old demo.

**Decisions:**
- History is simulated by passing past times as `now`. Orgs are claimed months ago, publish events 4–21 days before they start, and students RSVP in between. As a result, freshness (some dormant clubs show as stale), ended events and learned travel habits come out the way they would from real use. Plans run in publish-time order, so each org's "last published" date is its newest event.
- The world is deterministic: a fixed seed, and people are ordered by creation rather than by their random ids. A test checks this.
- It follows the same labelling as the demo: orgs are "[Demo] …", people "(demo …)", and every event has `is_demo=True`. Org websites point at `example.org`.

**Tests:** added `test_bulk_world_is_large_fictional_and_rule_abiding` and `test_bulk_world_is_the_same_every_time` to `tests/backend/test_seed.py`.

---

## 2026-11-14 — Backend reference document

**Request:** "Can you add a document that describes all the backend functions and where the functions are that have the functions?"

### Added
**`docs/BACKEND_REFERENCE.md`** (about 690 lines) lists every public class, method and function in `src/backend/`, with its signature, a one-line description and a link to its exact line, for example [L35](../src/backend/graph/membership.py#L35).

**Hand-written sections at the top:**
- **Start here:** how to get a `CollectivizeGraph` (`open_graph()`, or `CollectivizeGraph()` in tests), its constructor options, and a table mapping every `graph.<service>` to its class, file and job.
- **Conventions:**
  - the acting person and `now` are always passed in;
  - records are immutable;
  - which error means what (`NotFoundError` also covers "you may not know this exists");
  - privacy is enforced in the backend;
  - where AI calls happen.
- **Scripts:** what each script in `scripts/` does.

**The function lists** are grouped into nine areas:
- membership and orgs;
- people and the network;
- events;
- Discover and ranking;
- AI search;
- privacy, integrity and data access;
- storage;
- domain objects (with their fields);
- setup and demo data.

### How it was made
- **Generated from the code:** signatures, line numbers and existing docstrings were read from the source, so they're exact.
- **Descriptions written by hand:** 143 functions and 78 classes had no docstring, so their descriptions were written from reading the code.
- **Checked:** every one of the 337 entries links to the right line (the named `def`/`class` is there), and every contents link resolves.
- **No source files changed.** The generator was a throwaway script, so line numbers will drift as the code changes.
---

## 2026-11-14 — Edge-case hunt: 26 bugs found and fixed

**Requests:** "Can you make tests to test as many edge cases as possible and figure out where the bugs are", followed by "fix the bugs they find".

**How the bugs were found:** four independent reviewers each wrote an edge-case test file without changing the app:
- `test_edge_ranking.py` (72 runs)
- `test_edge_ai.py` (221 runs)
- `test_edge_graph.py` (101 runs)
- `test_edge_storage.py` (103 runs)

Every bug became a test of the **correct** behaviour, marked `xfail(strict=True, reason="BUG: …")`. Each fix removed its marker, so all of them now run as ordinary regression tests. **1361 pass, 3 are skipped (opt-in live AI tests), and 0 are xfail.** Ruff is clean.

### Privacy and permissions
1. **A non-member friend could see an RSVP to a members-only event** (high). Visibility took only the strictest single level, but "members only" and "connections only" are different groups, so passing one doesn't mean passing the other. `PrivacyService.can_view` now requires **every** party to allow it: the edge's own setting and both endpoints.
2. **Claiming an org gave admin rights before staff approval** (high). A confirmed member who claimed a released org became admin straight away. A claim is now always unconfirmed until `approve_claim`, which also means the claimant's membership is on hold while the claim is pending.
3. **The network showed people the viewer can't see** (medium). Member links and paths ignored the member's own profile visibility. `_membership_shown` now checks `can_view(viewer, person)`.
4. **Friends going ignored the RSVP consent flag** (medium). RSVPs marked `recommendation_use=NONE` are now never named or counted.
5. **You could RSVP to, or request to co-host, an event hidden by its host** (medium). The new `PrivacyService.can_view_listing` (event and host both visible) is now used by RSVPs and co-host requests, matching Discover.
6. **An org's admins couldn't see their own org's private or connections-only event** (medium). Anyone who can edit an event can now always see it.
7. **The ML export included private drafts of people who hadn't consented** (medium). It now exports only events that were published, aren't private or connections-only, and are hosted by an org or only by consenting people. Interactions with other events are left out as well.
8. **Anyone who could edit an event could add it to another org's series** (low). Adding now requires being an admin of the series' org.

### Data safety
9. **Changing a published event's coordinates crashed on SQLite** (high). The change log stored `GeoPoint`s the codec couldn't encode. They're now tagged `$geo` and round-trip.
10. **A failed COMMIT left the connection mid-transaction** (medium-high). Later writes were silently lost. The store now rolls back and re-raises.
11. **`seed_test_db.py --reset` could delete an unstamped database** (medium). It now reads the stamp read-only (`read_environment_stamp`) and deletes only files stamped `test`. A file that isn't a database is refused cleanly instead of crashing.
12. **`seed_mock_data` trusted its argument over the store's own stamp** (low-medium). It now refuses any store that isn't stamped test.
13. **The export script quietly created a missing database** (low). It now stops with an error.
14. **Unloadable records raised `TypeError`/`AttributeError`** (low). The codec now raises `ValueError`, so `check_graph` reports them instead of crashing.

### AI search and agent robustness
15. **A malformed model answer could crash search instead of falling back** (medium). Unhashable refs, huge integers, deeply nested JSON and over-long numbers now all become `InterpreterError`, then keyword fallback. Absurd scores are skipped like NaN.
16. **An unhashable pick ref crashed the agent** (medium), and **huge numbers raised `OverflowError`** in tool input (low). Both now return a tool error the agent can fix.
17. **Agent picks could vanish with more than 100 events** (medium). The new `DiscoveryQuery.event_ids` filter ranks exactly the picks.
18. **Short or non-ASCII keywords matched nothing** (medium). "AI", "Go", "5K" and "日本語" now work: tokenizing is Unicode-aware with a 2-character minimum, and filler-only keywords no longer filter.
19. **Bad `limit`/`offset` was only rejected after the paid model call** (low). It's now validated first.
20. **Undecodable Keychain output raised** (low). It now returns `None`, as documented.

### Ranking and RSVPs
21. **Search didn't Unicode-normalize** (low). "café" typed with a combining accent missed "Café night". Text is now NFKC-normalized and case-folded (`normalize_text`).
22. **`DiscoveryQuery` accepted naive datetimes** (low), and the search then crashed. They're now rejected up front.
23. **An event already under way said "Starts within 48 hours"** (low). It now says "Happening now".
24. **Going → not going → going counted the same trip twice** (low-medium). The new `Rsvp.trip_recorded` flag limits it to one trip per RSVP.

### Integrity audit false alarms
25. **Memberships confirmed by an admin who was later demoted were flagged** (low-medium). The new `MemberOf.was_admin` remembers confirmed admin rights after a demotion, and the audit accepts it.
26. **Memberships confirmed by an admin whose account was erased were flagged** (low-medium). Erasure now rewrites their `confirmed_by` to `ERASED_CONFIRMER`, which keeps the fact that an admin confirmed it without keeping who.

### Tests changed (behaviour improved, not weakened)
- **`test_edge_storage.py::test_seed_script_reset_on_a_non_database_file_does_not_delete_it`** expected a `DatabaseError` crash. The script now refuses cleanly (exit code 1), and the test still asserts the file is untouched.
- **`test_data_access.py::test_person_hosts_appear_only_if_they_consented`** became `…exported_only_when_published_and_their_host_consented`, following fix 7.

### Reported but left as is (need a decision, not a bug fix)
- **Staff checks:** `person_data(staff_purpose=…)` doesn't verify the caller is staff. That needs the login and API layer.
- **Friends going and consent:** friends going uses RSVPs with `OWN_ONLY` consent. Read strictly, the spec reserves "placing someone in front of others" for `NETWORK`.
- **Member lists:** they show members whose profile is CONNECTIONS or MEMBERS. This is documented roster policy, but it's lenient.
- **Error messages:** `calendar` and `roster` give a different error for a hidden org than for a missing one, which could reveal that the org exists.
- **Cancelled events:** learned categories count RSVPs to events that were later cancelled. A co-host invite can also be accepted on a cancelled event.
- **Email aliases:** `a+x@northeastern.edu` can create a second account.

---

## 2026-11-13 — Search agent: goal → person → searches → best events

**Request:** "Can you make it so the search bar is analyzed by the anthropic agent, the agent determines the goal of the person, then looks at the most important information about the person, then chooses the best things to search for the events and present the best events."

### How it works (`graph/search_agent.py`, `graph/search_tools.py`)
```python
result = graph.search_agent.search(viewer_id, "fast paced puzzles that make me think", now,
                                   origin=GeoPoint(...))
result.goal     # "Find a fast-paced event built around puzzles or problem solving…"
result.steps    # the tools it used, in order, with inputs
result.page     # its picks, ranked by the full likelihood model
```
Claude (`claude-opus-5-5`, effort `medium`) runs a capped tool loop:
1. **Goal:** it reads the search text and works out what the person wants, along with any limits they mentioned.
2. **The person:** it **always** calls `get_person_overview` (interests, categories they go to, usual travel distance, whether their location is known). It also calls `get_active_orgs` and `get_recent_events` when they'd sharpen the search.
3. **Searches:** it calls `search_events` with keywords (matching any word, best first), tags (`list_tags` gives the valid slugs), an org (including the orgs under it), a time window or a radius. It can try several angles.
4. **Presents:** it calls `submit_picks` with the goal and up to 5 events, each with a fit score from 0 to 1 and a reason. The fit scores become `request_match` signals:
   - picks get their fit score;
   - events it looked at but didn't pick count as 0.25;
   - everything else is neutral.

   Discover then ranks **only the picks**, so friends going, distance, tastes and trust still decide the order among them.

### Guard rails
- **Scope:** tools are bound to one viewer and one search. Searches go through Discover with the viewer's id, so visibility rules apply.
- **Privacy:** tool output never includes names of people, emails, positions or database ids. Events are `e1`, `e2`… and friends going is a count. `ai_uses_history` turns off the person tools.
- **Untrusted input:** the agent's inputs are validated. Types, ranges, text length, tag slugs, org names, the radius needing a location, fit scores in 0–1, no duplicate picks, and refs it has actually seen are all checked. Bad input goes back to the agent as an `is_error` result it can fix; it never crashes the run.
- **Cost caps:** at most **8 turns and 20 tool calls**, and a 60-second timeout per request. The loop is append-only, so the conversation is never edited. Tools are `strict: true`, and the request uses refusal fallback (`fallbacks: "default"`) and prompt caching.
- **Fallback:** a refusal, a cut-off, answering in prose without submitting, too many turns or calls, or any API or credential error falls back to the single-call AI search, and from there to keywords. `note` says what happened.
- **Why a manual loop** rather than the SDK's tool runner: it allows hard caps on turns and calls, a finishing tool, and a client that tests can replace.

### Tests: never calling the real API
- ⚠️ **What went wrong:** while I was building this, the agent's fallback tests created a real single-call interpreter, which read the Keychain key and **made real API calls**. That happened over two test runs, about 25 small low-effort requests, an estimated cost under $1. It should not have happened.
- **Fix:** an autouse fixture in `tests/backend/conftest.py` now replaces `anthropic.Anthropic` with a stand-in that refuses to construct, so **no test can reach the API** unless `COLLECTIVIZE_LIVE_AI=1` is set. A guard test (`test_the_suite_can_never_reach_the_real_api`) keeps it that way. The agent tests went from 40 seconds to 1.5.
- **`test_search_agent.py`** (70 runs, plus 1 opt-in live test) uses a scripted fake client. It covers:
  - the full loop;
  - an append-only conversation, with all tool results in one message and matching ids;
  - request settings;
  - schemas that strict mode accepts;
  - ranking of picks, with only picks presented and empty picks allowed;
  - recovery from bad tags, made-up refs and unknown tools;
  - every way a run can fail falling back;
  - visibility, **no identifying data in any tool output**, and the opt-out;
  - every search filter and input validation;
  - Hypothesis feeding random input to every tool, which always gets JSON back and never raises.
- **Totals:** 864 pass and 3 are skipped (the opt-in live tests). Ruff is clean.

### Live run (one search, about 4 API calls, with the user's key)
`uv run python scripts/ai_search.py --as Drew --near-campus "fast paced puzzles that make me think"`:
```
Goal: Find a fast-paced event built around puzzles or problem solving that makes them think hard.
Steps:
  - search_events {'keywords': 'puzzle puzzles speed timed escape room trivia brain teaser', 'limit': 15}
  - list_tags
  - search_events {'keywords': 'problem solving challenge competition game strategy chess quiz hackathon', 'limit': 15}
  - submit_picks {... 'e1', fit 0.85, 'Quick rounds of timed coding puzzles in pairs, with lots of problem solving.'}
Results:
   80%  Robotics study jam   Fits what you asked for: Quick rounds of timed coding puzzles… | 2 friends going | Close to you (500 m away)
```
- **Prompt change afterwards:** in that run the agent skipped the person lookups for a specific request. The prompt now makes it **always** read the person's overview first, as requested. That change hasn't been run live yet.
- **Script:** `scripts/ai_search.py` now runs the agent by default and shows the goal, steps and picks. `--single` runs the one-call search.

### Not done
- **Speed:** a search takes several seconds over several calls. A search bar UI should show progress, such as the steps.
- **Evaluation:** there's no eval set for the agent's picks yet.

---

## 2026-11-13 — API key stored securely; first live AI search

**Request:** "Can you add the following to a secure method for a key: sk-ant-…", followed by the earlier request to "run the live search as Drew".

### Key storage
- **Where it lives:** the key is stored in the **macOS login Keychain** as the item `collectivize-anthropic-api-key`. It's encrypted at rest and in no file in the repo. A search of the repository confirms no copy exists.
- **`src/backend/credentials.py`:** `anthropic_api_key()` returns `ANTHROPIC_API_KEY` if that's set (for servers and CI), otherwise the Keychain item on macOS, otherwise `None`. With `None`, the SDK falls back to its own sources, such as an `ant auth login` profile.
  - It calls `/usr/bin/security` with a fixed argument list, no shell and a 5-second timeout.
  - Any failure returns `None`, and the key is never logged.
- **`ClaudeInterpreter`** now builds its client with that key.
- **Tests:** `test_credentials.py` (7) plus 2 new interpreter tests. **Tests never read the real Keychain;** it's replaced by fakes. In total, 793 pass and 1 is skipped. Ruff is clean.
- ⚠️ **The key was pasted into a chat, so treat it as exposed and rotate it** in the Claude Console. To store a replacement without it appearing anywhere, run `security add-generic-password -U -a "$USER" -s collectivize-anthropic-api-key -w`, which prompts for the value. To remove it, run `security delete-generic-password -s collectivize-anthropic-api-key`.

### First live AI search (one paid call)
`uv run python scripts/ai_search.py --as Drew --near-campus "fast paced puzzles that make me think"`:

```
Understood as: You want quick, brain-teasing puzzle activities that challenge your thinking.
Used AI: True
   87%  Robotics study jam   Fits what you asked for: Quick timed coding puzzles in pairs,
                             lots of problem solving. | 2 friends going | Close to you (500 m away)
   75%  Chapter meeting      3 friends going | Not much like what you asked for | Like your orgs: Social
   74%  Spring philanthropy 5K   3 friends going | Like your orgs: Social | Not much like what you asked for
```
- **Compared with the keyword fallback:** the fallback had ranked Drew's chapter meetings first, on friends and his org. Claude recognised the study jam as the puzzle event and moved it to the top, while the other signals (friends going, distance) still shaped the rest of the list.

---

## 2026-11-13 — AI search from a sentence + user data access for ML

**Request:** "I need it to look at both the requested sentence and the user profile and most interacted with organizations and events to then make the best search of the closest weighted event (along with all other weights that have already been included). I believe this analysis should be done using AI that analyses both your request and your past history. Also make a function to query each user's data to be able to run machine learning analysis or whatever else we might need later on."

### AI search (`graph/ai_search.py`, `graph/claude_interpreter.py`)
```python
result = graph.ai_search.search(viewer_id, "something fast paced that uses my brain", now,
                                origin=GeoPoint(...), max_distance_km=5, limit=10)
result.page            # a normal DiscoveryPage, best fit first
result.understood_as   # how the request was read
result.used_ai, result.note
```
1. **Candidates:** Discover finds every event the viewer may see (filters and radius apply). Cancelled events are left out, and at most 60 candidates go to the model.
2. **Claude scores them.** It reads the sentence and the viewer's context:
   - interests they chose;
   - learned categories;
   - their orgs' tags;
   - **top 5 most-interacted orgs** and **8 most recent events** (`graph/activity.py`);
   - their usual travel distance.

   It returns a 0–1 fit score and a reason of at most 12 words for each candidate.
3. **The score becomes the `request_match` signal** in the likelihood model, weighted 2.5 because it was asked for directly. The other signals (friends, distance, tastes, trust, soonness) still count, so friends going breaks a tie between two equal fits, a strong fit beats a weak one that has friends, and a nearer event wins between equals. Reasons include "Fits what you asked for: fast team strategy…".
4. **Fallback:** if the model call fails for any reason (no credentials, network, rate limit, refusal, a cut-off or malformed answer), keyword matching takes over and `note` says why. A keyword miss is neutral rather than negative, because missing keywords are weak evidence.

**Claude call details:**
- **Model and effort:** `claude-opus-5-5` at `effort: "low"`, since scoring a list is a judgment task.
- **Output:** structured JSON (`output_config.format`), validated again locally:
  - unknown refs are dropped;
  - scores must be finite numbers, and out-of-range ones are clamped to 0–1;
  - duplicates are dropped;
  - reasons and the summary are trimmed.
- **Refusal fallback is on** (`fallbacks: "default"`).
- **Caching:** the system prompt is fixed and cached.
- **Client:** it's created on first use, with a 30-second timeout and 1 retry. Credentials come only from the environment.

**Privacy decisions:**
- **What the model receives:** the sentence, tag and org names, titles of events the viewer interacted with, and candidate events under refs like `e1`. It never receives database ids, other people's names, emails, positions or friend identities. Friends going is sent as a number, and person hosts appear as "a student".
- **Injection guard:** host-written event text is placed in JSON data fields, and the system prompt says never to follow instructions found there.
- **Consent:** history marked `recommendation_use=NONE` is never sent. The new `Person.ai_uses_history` setting (default on: your own data, for your own results) turns history off entirely, and then only the request is sent.

### User data access (`graph/data_access.py`)
- **`person_data(person_id, requested_by, now, staff_purpose=None)`:** everything held about one person, including memberships, connections, RSVPs, interests, invites sent (never codes), hosted events, settings, travel average, learned categories and top orgs. The person can always get their own. Staff need a stated purpose, and their access is recorded.
- **`ml_dataset(staff_id, purpose, now, key)`:** tables of `people`, `interactions` (RSVPs), `memberships`, `connections`, `events` and `orgs` for analytics and ML.
  - **Opt-in only:** it includes only people with the new **`Person.analytics_consent`**, which defaults to off, following user_Orgs.md's "the default is the narrower choice". Facts marked `NONE` are skipped, and a connection appears only if both people opted in.
  - **Pseudonymized:** each person id becomes an HMAC-SHA256 of the real id under a secret key (`COLLECTIVIZE_EXPORT_KEY`, at least 16 bytes, never hard-coded). The same key gives stable pseudonyms across exports, and without it they can't be reversed.
  - **What's left out:** names, emails, positions and invites. Travel distance is rounded to 0.5 km, and join dates are kept to the month.
  - **Recorded:** every export saves a `DataExport` node saying who ran it, why, and how many people and rows it covered.
- **Scripts:**
  - `scripts/export_ml_dataset.py --staff ID --purpose "…"` writes JSONL tables and a manifest to `data/exports/<timestamp>/`, and refuses any path outside that folder.
  - `scripts/ai_search.py --as Drew --near-campus "…"` tries AI search from the terminal.

### Other changes
- `RankingWeights.request_match = 2.5`, and `EventSignals.request_match` (`None` is neutral, matching 0.5).
- `DiscoveryService.search(..., request_matches=...)` and `event_tag_ids()` are new, along with the new `RequestMatch` type.
- **Seed:** demo events have descriptions the AI can read, and 29 of the 32 demo students opted in to analytics (3 deliberately didn't).
- **Dependencies:** `anthropic` (SDK 2.8.0) was added, and `.coverage` is now git-ignored.

### Verified
- **Tests:** 785 pass and 1 is skipped. Coverage is 99% overall, and 100% for `ai_search`, `claude_interpreter` and `ranking`. Ruff is clean.
  - `test_ai_search.py` (57) uses a fake interpreter. It covers ranking (fit, friends and distance interplay), the context sent (history, consent, opt-out, logged out), **nothing identifying being sent**, visibility, the candidate cap, the fallback, validation, paging, injection staying as data, and a Hypothesis check that any valid answer gives a sorted, sane page.
  - `test_claude_interpreter.py` (24 + 1 opt-in live test) uses a fake client, with **no API calls in the suite**. It covers the request settings (model, effort, fallbacks, structured output, cached system prompt), answer validation (including Hypothesis over arbitrary text), refusal and cut-off handling, every SDK error class, missing credentials, and client reuse. The live test runs only with `COLLECTIVIZE_LIVE_AI=1`.
  - `test_data_access.py` (33) covers self-access, staff access, opt-in only, pseudonym stability, **no names, emails or ids leaking**, connections needing both people to consent, `NONE` exclusion, features, export records, key handling and erasure.
- **On the reseeded `data/test.db`:**
  - The integrity check passes.
  - An export wrote 29 people, 64 interactions, 61 memberships, 47 connections, 10 events and 11 orgs. That test export was then deleted.
  - The keyword fallback works with no credentials.
  - **No live Claude call has been made yet,** because it costs money; that needs the user's approval.

### Not done
- **A live AI run:** `uv run python scripts/ai_search.py --as Drew --near-campus "fast paced puzzles that make me think"` makes one paid Claude call (or `COLLECTIVIZE_LIVE_AI=1` for the test).
- **An eval set** to measure how good the AI's scores are, and tuning of the request weight against it.
- **A consent screen:** there's no UI or API yet for people to opt in to analytics or turn off AI history; the fields exist.
- **Recalling exported files:** files already exported can't be pulled back when someone deletes their account. Keep them short-lived.
- ⚠️ **`collectivize_plan.md` still says "no behavioral tracking in v1"** and should be updated.

---

## 2026-11-13 — Discover becomes a "would they go?" model: location, travel habits, tastes

**Request:** "Add a weighting by location radius from the user's current position, and also gather information about how far they averagely go for events and what category. Change point system to a formula weight to determine if they would go. Also have a weight based on how closely the event is to their liked values/hobbies. Basically change the weighting to be more dynamic rather than discrete. Add large testing to make sure there are no errors in the algorithm and check edge cases."

### The model (`graph/ranking.py`)
The fixed points are gone. Each event now gets an estimated **likelihood (0–1) that this viewer would go**:

```
likelihood = sigmoid(bias + Σ weightᵢ × signalᵢ)
```

| Signal | Value | Shape |
|---|---|---|
| friends | log(1 + friends going) | Diminishing returns: the first friend matters most |
| my_org_host | 1 if one of your orgs hosts or co-hosts | Counted once |
| affinity | how well the event's tags match your tastes, 0–1 | Cosine similarity × strength of your taste |
| proximity | closeness − 0.5, where closeness = 1 / (1 + (d/s)²) | 1 next door, 0.5 at **your usual distance s**, towards 0 beyond. Unknown distance is neutral (0) |
| soonness | e^(−days/7) | Fades smoothly |
| host_trust | 1 verified, 0.4 pending, 0 unclaimed or a person | |
| staleness | 0 for 30 days, then rising smoothly towards 1 | Replaces the active/quiet/stale buckets |
| verified / disputed | 1 or 0 | |

- **Cancelled events** get likelihood 0 and always sort last.
- **The weights** live in one `RankingWeights` object, set with `CollectivizeGraph(ranking_weights=...)`. They're hand-tuned so that an event with nothing going for it sits near 10%, a strong match lands around 90%, and the plan's order holds: friends going, then your org hosting, then sharing your orgs' tags.
- **The weights aren't fitted to data yet.** Until they're fitted to real attendance (logistic regression), the likelihood is a ranking estimate, not a calibrated probability.

### Location
- **New query fields:** `DiscoveryQuery(origin=GeoPoint(...), max_distance_km=..., include_unlocated=True)`.
- **Radius filter:** the radius is inclusive. Events with no location are kept by default, and `include_unlocated=False` drops them. Without an origin, distance plays no part.
- **New fields on each result:** `distance_km`, and `factors`, which gives each signal's value and effect for "why am I seeing this?".
- **Events have places:** `Event.coordinates` (a `GeoPoint`) is editable, and changes to it are logged like location changes. `EventSeries.default_coordinates` covers series meetings.
- **Distance maths:** `GeoPoint` validates latitude and longitude, rejecting NaN, infinity and booleans. `haversine_km` is safe for identical points, antipodes and the date line.

### Learning (`graph/preferences.py`)
- **How far you usually go.** When you RSVP "going" and the app sends your current position (`rsvps.respond(..., origin=...)`), the distance updates a running average of log-distance on your own `Person` record. The average becomes your scale `s` after 3 trips. Before that, the scale is the search radius ÷ 2, or 2 km.
  - Trips are counted once per event, only for "going", and only if the RSVP's consent allows it.
  - Distances below 0 or above 500 km, or not finite, are ignored. One long trip barely moves the average.
- **What you like.** Three sources are blended into one tag vector:
  - interests you chose (new `add_interest` / `remove_interest` / `interests_of`; only you can set them), at weight 1.0;
  - your orgs' tags, at weight 0.5;
  - **categories you've gone to**, learned from your RSVPs, at weight 0.8. "Going" counts double "interested", and older RSVPs fade with a 120-day half-life.
- **Reasons name the source:** "Matches your interest: Robotics", "Like your orgs: Social", "Like events you've gone to: Robotics".
- **Transparency and control:** `my_profile` shows you what's been learned, and `forget_travel` resets your travel average.

### Privacy decisions
- **Your current position is used for one search or RSVP and never stored.**
- **No per-event distance is stored either,** because many distances to known places could reveal where someone lives. Only the running average is kept, and it's private like `email`.
- **Learned categories and the likelihood are computed per search and never stored.** This follows user_Orgs.md: "Predicted attendance… computed when ranking and then discarded".
- **Consent:** RSVPs and interests with `recommendation_use=NONE` are never learned from, and everything learned only improves the person's own results.
- **Erasing an account** removes the travel average, interests and RSVPs.
- ⚠️ **This goes beyond `collectivize_plan.md`,** which says "no behavioral tracking in v1". It stays within `user_Orgs.md`'s consent rules, and the plan should be updated to match.

### Reasons (`graph/explain.py`)
- **Reasons come from the model's own contributions:** any factor that moved the estimate by at least 0.2 in log-odds is mentioned, biggest first, after the host line.
- **New reasons:**
  - "Close to you (600 m away)";
  - "Farther than you usually go (40 km away)";
  - "Like events you've gone to: …".
- **Distances are formatted** as "under 50 m", "450 m", "2.3 km" and "40 km".

### Seed
- **Named campus places with coordinates,** and a new off-campus event, "Night market food crawl", about 6 km away. The seed now has 10 events.
- **Interests:** students have 0–2 interests each.
- **Travel:** each RSVP "going" passes a made-up position near campus, so travel habits are learned through the real flow. The positions are never stored.
- **Results on the seeded `data/test.db`:** it passes the integrity check.
  - Drew's likelihoods range from 0.96 down to 0.21.
  - Kai, who chose Robotics as an interest, sees "Robot demo day" first.
  - Logged-out visitors see about 0.1 across the board.
  - A search takes 13–16 ms.

### Testing
The suite grew from 506 to **666 tests, all passing**, with **99% coverage** of `backend`.
- **`test_ranking_math.py`** (63) covers the maths:
  - Hypothesis property tests over thousands of inputs: distance symmetry, bounds and the triangle inequality; the sigmoid never overflowing; every curve bounded and monotonic.
  - **Monotonicity of the estimate in every signal**: more friends, a better match, closer, sooner and a more trusted host never lower it, and a staler host never raises it.
  - The contributions add up exactly to the likelihood.
  - Reference values for known distances (Boston–NYC, pole to pole, across the date line, antipodes).
  - Validation of every bad input.
- **`test_preferences.py`** covers interests, learned categories (decay, consent, inherited tags) and travel averaging (too few trips, outliers, zero distances, NaN/∞/negative, overflow-proofing, staying between the shortest and longest trip). It also checks that **positions and single distances are never stored**.
- **`test_discovery_location.py`** covers the radius filter and its inclusive boundary, query validation, distance ordering, neutral unknown distance, personal travel scale ("homebody" vs "traveller"), trip recording rules, taste-match ordering and distance formatting.
- **`test_discovery_fuzz.py`** generates random worlds and searches with Hypothesis. Each world has orgs, people, events with random places, times, tags, visibility and status, plus friendships, memberships, RSVPs, hidden RSVPs, interests and trips. Every page must:
  - give only finite probabilities;
  - include only events the viewer may see, and never drafts;
  - respect every filter;
  - put cancelled events last at 0, with everything else in likelihood order;
  - name only real friends who are going;
  - never show a count under 5;
  - never list an event twice;
  - split into pages that exactly match the full list;
  - leave the database unchanged and give the same result when repeated.

  The default is 120 worlds per test. `FUZZ_EXAMPLES=2000` runs a deep hunt, and 2,000 worlds per test passed. The generator is biased towards realistic searches: 89% of cases return results, 30% involve friends going and 67% involve distances.
- **Mutation check:** I deliberately broke the distance curve, the consent check and the sigmoid's overflow guard in turn. The suite caught each one (14, 2 and 2 failures).
- **Changed:** 4 discovery tests that asserted exact point gaps (+2, +1) now assert ordering, the model's factors and reasons. Hypothesis was added as a dev dependency.

### Not done
- **Weights fitted to data:** this needs attendance records (ATTENDED isn't built) and enough real usage.
- **Embedding similarity:** `Event.embedding` and `Person.embedding` aren't used yet. Tags are the taste signal.
- **Venues:** coordinates live on events. Venue nodes (spec "Later") could supply them.
- **Page size:** Discover still defaults to 20 results per page; the plan says 10.

---

## 2026-11-13 — The rest of the plan's Discover formula

**Request:** "Add the rest of the plan's ranking formula."

Discover now applies the whole formula from `collectivize_plan.md`: **3 × friends going + 2 × hosted by one of my orgs + 1 × tag overlap with my orgs' tags.**

### How the new parts work
- **"My orgs":** orgs you're a confirmed, current member of. Pending requests, past memberships and logged-out visitors get nothing.
- **+2 (`MY_ORG_HOST_SCORE`):** given once when any accepted host, primary or co-host, is one of your orgs. The reason reads "Hosted by your org: …" and names every one of your orgs that's hosting.
- **+1 per shared tag (`MY_ORG_TAG_SCORE`):** tags the event shares with the tags your orgs carry. The event's tags include those inherited from its host orgs, matching the tag filter. The reason reads "Like your orgs: Robotics, Social".

### Decisions
- **The formula adds to the existing score.** Host trust, freshness, provenance, chosen interests (+2.5 each), soonness (up to +2) and the cancelled penalty all still apply. They mostly break ties between events the network ranks equally.
- **An event hosted by your org usually gets both bonuses**, because it inherits its host's tags. It gets +2 for the host and +1 per inherited tag that's also one of your orgs' tags. This follows the plan's formula literally. If it pushes your own orgs' events too high, the fix is to count only the event's own tags.

### Verified
- **Tests:** `test_discovery.py` gained 5 tests (10 runs), covering:
  - an exact +2 gap;
  - co-hosting counting, with the bonus given only once;
  - no bonus for pending members or logged-out visitors;
  - +1 per shared tag;
  - the full formula's order: friends going above my org's event, above a shared tag.

  In total, 506 pass and ruff is clean.
- **On `data/test.db`:**
  - Drew's top events are chapter meetings, with "4 friends going | Hosted by your org | Like your orgs: Social".
  - Casey's are the Robotics Club events.
  - A search takes 10–17 ms.

### Not done
- **Page size:** Discover still defaults to 20 results per page. The plan says 10.

---

## 2026-11-13 — RSVPs and "friends going" in Discover

**Request:** "Add RSVPs and friends going to discover."

This is demo step 5 from `collectivize_plan.md` ("Results are paginated cards with '3 friends going.' Open the event and RSVP"). The rules come from the RSVP section of `user_Orgs.md`.

```python
graph.rsvps.respond(event_id, person_id, RsvpStatus.GOING, now)   # or INTERESTED / NOT_GOING
graph.rsvps.respond(event_id, person_id, None, now)               # clear it
graph.rsvps.mine(event_id, person_id)
graph.rsvps.friends_going(viewer_id, event_id)                    # tuple of Person
graph.rsvps.going_count(event_id)                                 # int, or None when small
graph.rsvps.set_rsvp_visibility(person_id, by, Visibility.PRIVATE)  # "who can see my RSVPs"
```

### RSVP rules
- **Responding:** there's one RSVP per person per event, and it can be changed or cleared. RSVPs are only allowed while an event is published and hasn't ended. After it ends they freeze, so they can't be changed or cleared.
- **Visibility:** you can only RSVP to events you can see. Drafts and other orgs' members-only events look like missing events.
- **Capacity:** a full event refuses new "going" RSVPs, but "interested" still works.
- **Who sees your RSVPs:** this is your setting, `Person.rsvp_visibility`. The choices are logged-in users (NETWORK), your connections (CONNECTIONS, the default) or nobody (PRIVATE). Each RSVP carries the setting, so the normal privacy rules decide who sees it. Changing the setting updates all your existing RSVPs.
- **Counts:** totals count everyone, including people who hide their RSVPs. A total is hidden (`None`) below 5 (`MIN_PUBLIC_COUNT`), so a small number can't identify anyone.

### Discover changes
- **New fields on each result:**
  - `friends_going`: your connections who are going and whose setting lets you see it;
  - `my_rsvp`;
  - `going_count`.
- **Ranking:** each friend going adds +3, following the plan's formula, with the reason "N friends going". The existing factors (trust, freshness, interests, soonness) are unchanged.
- **Logged-out visitors** get no friends and no RSVP, but they do see counts.
- **Refactor:** a search's settings now travel in one internal context object instead of a growing argument list.

### Seed
About 80 RSVPs, clustered:
- Members tend to go to their own org's events (55%).
- People whose friends are going are more likely to go (30%).
- Anyone else rarely goes (4%).
- 85% say "going" and the rest "interested".

The seeded `data/test.db` has 78 RSVPs (69 going, 9 interested) and passes the integrity check. Drew's Discover ranks chapter meetings first with "4 friends going", and a search takes about 15 ms.

### Tests
`tests/backend/test_rsvps.py` adds 27 runs. In total, 496 pass and ruff is clean.

### Not done
- **Notifications:** nobody is told when an event's time or location changes, although the change is logged on the event.
- **Attendance:** recording who actually attended after an event isn't built.
- ~~The rest of the plan's ranking formula~~: added in the entry above.
- **Page size:** Discover still defaults to 20 results per page. The plan says 10.

---

## 2026-11-13 — Invites: your inviter is your first connection

**Request:** "Add invites so the inviter becomes the first connection."

This is demo step 1 from `collectivize_plan.md`. `graph.invites` (`graph/invites.py`):

```python
issued = graph.invites.create(inviter_id, now)        # issued.code: show it once
joined = graph.invites.redeem(code, email, display_name, now)
joined.person, joined.inviter, joined.connection      # "You're connected to …"
graph.invites.revoke(invite_id, by_person_id)         # inviter only, unused invites
graph.invites.invites_of(person_id, by_person_id)     # your own invites only
```

### Rules
- **Codes:** any person can invite. Codes are random (16 URL-safe characters) and single-use, and they expire after 14 days. Each person can have at most 20 open invites.
- **Redeeming:** checks the email, creates the person, connects them to the inviter and marks the invite used. It all happens in one transaction, so a failure leaves the invite unused.
- **First connection:** it starts out accepted by both people. The inviter agreed by inviting, and the new person by joining. It's marked `origin=INVITE`, and either person can remove it like any other connection.
- **Email:** it has to be a valid address on an allowed domain, matched exactly. The default is `northeastern.edu`, so `mail.northeastern.edu` and look-alikes such as `northeastern.edu.evil.com` are rejected. Addresses are normalized to lowercase, and each one can have only one account. Change the domains with `CollectivizeGraph(invite_email_domains=(...))`.

### Security decisions
- **The code itself is never stored.** An `Invite`'s id is the SHA-256 fingerprint of its code, so reading the database doesn't give anyone a usable invite.
- **Every failure looks the same.** Unknown, used, expired, revoked, or sent by an erased account all give "invalid or expired invite", so codes can't be probed. Spaces around a pasted code are ignored.
- **Email is private.** `Person.email` is never part of network or member-list results, and a future API must not send it to other users.
- **Erasure covers invites.** Deleting an account also deletes invites the person sent or redeemed.

### Added
- **Data model:**
  - the `Invite` node (`objects/invite.py`);
  - `Person.email`;
  - `ConnectionOrigin` (`REQUEST` / `INVITE`) on `Connected`;
  - `ConnectionService.connect_via_invite`.
- **Seed:** an open invite from Drew with the fixed code `demo-join-from-drew`, so the join screen can be demoed. The seed script prints it, and `SeedResult.invite_code` holds it.
- **Tests:** `tests/backend/test_invites.py` adds 46 runs, and `test_seed.py` gained one test. In total, 469 pass and ruff is clean. `data/test.db` was re-seeded, its demo invite is unused, and it passes the integrity check.

### Not done
- **Email verification:** nothing proves the person owns the address yet. That needs a magic link or login, which is part of the future login layer.
- **Rate limiting:** there's no limit on redeem attempts yet. Codes have 96 bits of randomness, so guessing isn't practical, but the API layer should still rate-limit attempts.
- **Picking orgs:** choosing "the orgs you're in" during onboarding uses the existing `membership.request`. There's no single call that combines it with joining.

---

## 2026-11-13 — Network graph: neighborhoods, paths, in common

**Request:** "Build the network graph with those recommendations."

This is demo step 2 from `collectivize_plan.md`. `graph.network` (`graph/network.py`) answers four questions for a logged-in viewer:

```python
graph.network.neighborhood(viewer_id, center_id=None, depth=1, max_nodes=150)  # nodes + links
graph.network.find_path(viewer_id, target_id)        # shortest route, at most 4 links, or None
graph.network.focus(viewer_id, focus_id)             # a clicked node: its links + the path from you
graph.network.in_common(viewer_id, other_id)         # mutual friends + shared orgs, .summary
```

Results are plain data the frontend can draw directly: `NetworkNode(id, kind=person|org, label)` and `NetworkLink(source, target, kind=connection|membership)`.

### Decisions (the three recommendations)
1. **Paths can run through people or orgs.** When two routes are equally short, the one through fewer orgs wins, so You → Maria → Jordan beats You → Surf Club → Jordan. Paths longer than 4 links return `None` ("No close connection yet").
2. **Only links the viewer may see are used.** That applies to drawing, paths and in-common alike. Hidden things are left out entirely, with no "anonymous" placeholder. This is stricter than the plan's anonymous "a mutual connection" node, which would still reveal that a link exists.
   - **Connections:** a connection shows if you're one of the two people, or if neither person has turned on hide-connections.
   - **Memberships:** a membership shows if it's yours, or if the org's member list shows it to you.
   - **Not shown:** pending requests, past memberships, private memberships, and orgs or people you can't see.
3. **Member links follow the member-list policy.** Changing `RosterPolicy` changes the graph too.

### Added
- **`Person.hide_connections`:** set it with `graph.connections.set_hide_connections(person, by, hidden)`. Only the person can change it, and it hides only their connections, not their memberships.
- **`RosterService.shows(viewer, edge)`:** checks whether a single membership is listed for a viewer.
- **Denser demo data** (`src/backend/seed_network.py`):
  - 5 new orgs: Surf Club, Club Soccer, Cooking Club, and two more chapters under the IFC. That makes 11 orgs.
  - 5 new org admins and 32 students, for 42 people in total.
  - Each student belongs to 1–3 orgs, and every membership was confirmed by that org's admin.
  - Each person has 3–6 friendships, about 75% of them with people who share an org, and each one accepted by both people.
  - Quinn has hide-connections turned on.
  - The data is deterministic (fixed random seed), so the demo is the same every time.

### Changed
- **`Connected` visibility now defaults to logged-in users (NETWORK).** It was connections-only. That default would have limited the network to friends-of-friends, so searching for a stranger would rarely find a path. Each person's own switch is now `hide_connections`, which matches the plan's "hide my connections" setting.

### Verified
- **Seeded `data/test.db`:** it passes the integrity check.
  - Drew can reach all 41 other people within 3 links: 6 direct, 16 at two links, 19 at three.
  - On SQLite, a depth-1 view takes about 11 ms and a depth-2 view about 45 ms. Each path takes about 35 ms.
- **Tests:** `tests/backend/test_network.py` adds 43 runs. In total, 422 pass and ruff is clean.

### Not done
- **Invites:** the inviter doesn't become your first connection yet.
- **Org-to-org links:** PART_OF and PARTNERS_WITH aren't part of the graph.
- **Speed at scale:** path search is plain Python over the store, which is fine for the pilot. At scale it would need caching or a graph index.

---

## 2026-11-13 — Calendar page shell and nav placeholders

**Request:** "Add the following pages to the navigation: calendar, discover, network, and profile. Then add an empty calendar to the calendar page with all the basic things that a calendar has that won't really affect the backend."

There is now a Calendar page (`src/frontend/calendar.html`), and the nav lists the pages from the plan. The calendar is a layout only: it shows no events and loads no data. Nothing in `src/backend/` or `tests/` changed.

### How to use it
- Run `python3 -m http.server` from the repo root and open `http://localhost:8000/src/frontend/calendar.html`.

### Added
- **`src/frontend/calendar.html`, `calendar.css` and `calendar.js`:** the Calendar page.
  - **Header:** the month and year, a Today button, previous and next arrows, and a Month / Week / Day switch. Week and Day are disabled and marked "Coming soon".
  - **Month grid:** Sunday to Saturday, always six weeks so its height never changes. Days outside the month are faded, today is circled, and clicking a day selects it.
  - **Day panel:** the selected day, with empty **My events** and **Community events** sections, as described in the plan. It moves below the grid on screens 960px and narrower.
- **`src/frontend/discover.html`, `network.html` and `profile.html`, with `placeholder.css`:** "Coming soon" pages so the new nav links don't lead to an error page.

### Changed
- **`src/frontend/nav.js`:** the nav now reads Home, Calendar, Discover, Network, Profile, then Demo. Each new page has its own icon. Network uses the graph icon, so Demo has a new flask icon.

### Decisions
- **Its own page for now:** the plan puts the calendar on Home, below the hero. It's a separate page for now because Home is still just the hero and Discover doesn't exist yet. It can move into Home later.
- **No calendar library:** the month grid is about 100 lines of plain JS, which matches the rest of the frontend. Week and day views will take more work than they would with FullCalendar.
- **Demo stays in the nav,** at the bottom, until the Network page replaces it.

### Not done
- **Events:** no data, fetching or event display. When events are added, they should use the backend's field names (`starts_at`, `ends_at`, `location`, `status`, `visibility`, hosts with `role`) so an API can replace the placeholder data without changing the page.
- **Backend gaps for the calendar:**
  - There's no query that returns everything a viewer should see on their calendar in a date range. `calendar.host_events` covers one host, and `discovery.search` only returns upcoming events.
  - RSVPs have no service, so "Going" can't come from the backend yet.
  - There's no API.
- **Locations are free text.** There's no address or map until `Venue` is built.
- **Plan mismatch:** the plan's visibility levels (public / members / invite) don't match the backend's (public / network / members / connections / private). The backend has no "invite specific people".
- **Restored entry:** the "Home page and shared navigation" entry below was dropped by commit `5fad060` and has been put back unchanged.

---

## 2026-11-13 — Fixed the 4 known bugs

**Request:** "Fix the 4 known bugs first."

These are the bugs the edge-case tests had marked as expected failures (`xfail`). The markers are removed, so those tests now run as normal tests. I also added tests for two related holes.

### Fixes
1. **Cancelling a draft made it public.** `Event` now records `published_at` when it's first published, and a `was_published` property reads it. A draft cancelled before publishing stays hidden everywhere:
   - **Privacy:** only its editors can see it.
   - **Discovery:** it's never listed.
   - **Calendars:** it appears only in the hosts' private list.

   A published event that's later cancelled still shows until it ends. Older records with no `published_at` count as published if their status says so.
2. **Publishing a series wasn't all-or-nothing.** `SeriesService.publish_occurrences` now runs inside one transaction, so if any occurrence is rejected, none are created.
3. **SQLite nested transactions.** A failure caught inside an inner block still committed the inner block's writes. Now the outermost `transaction()` is a real `BEGIN … COMMIT`, and each nested block is a SQLite `SAVEPOINT`. A failed inner block rolls back only its own writes, matching the in-memory store. The connection now runs in autocommit mode, and the store issues every transaction statement itself.
4. **A pending claim could leave an org stuck.** Erasing the account of someone with an unapproved claim left the org in `claim_pending`, so nobody else could claim it. Now erasing that account reopens the org. Withdrawing the claim with `leave` reopens it too; that path had the same hole.

### Tests
Added these tests, which now pass:
- three levels of nested transactions on both stores;
- nested SQLite work surviving a reopen;
- a cancelled draft staying off outsiders' calendars but showing in the hosts' private list;
- a published event that's cancelled staying visible;
- withdrawing a claim reopening the org.

In total, 379 pass and nothing is marked `xfail` any more. Ruff is clean. `data/test.db` was re-seeded and passes the integrity check.

---

## 2026-11-13 — Home page and shared navigation

**Request:** "When you first enter the website, fullscreen you see the logo and wordmark… a nav bar on the left that allows you to switch between pages… similar to how the Claude nav bar works."

There is now a Home page (`src/frontend/index.html`) showing only the logo with the wordmark below it, centered on an off-white background. A shared sidebar nav, which works like Claude's, switches between Home and the demo graph page (`main.html`). We stayed with plain HTML/CSS/JS instead of moving to Next.js for now.

### How to use it
- To view it, run `python3 -m http.server` from the repo root and open `http://localhost:8000/src/frontend/`.
- To add a page to the nav, add one entry to `PAGES` at the top of `src/frontend/nav.js`, then add these two lines to the new page's `<head>`:
  ```html
  <link rel="stylesheet" href="nav.css">
  <script src="nav.js"></script>
  ```
  Load `nav.js` without `defer`, so the open/closed state is set before the page paints.

### Added
- **`src/frontend/index.html` and `landing.css`:** the Home page. The logo is sized `min(58vh, 80% of the space beside the nav)` and the wordmark `min(70%, 520px)`, so neither ever scrolls. The tab title is "Collectivize" and the tab icon is `app/icon.svg`.
- **`src/frontend/nav.js` and `nav.css`:** the shared nav, built from a single page list.
  - **On desktop:** a 56px icon rail. The toggle button expands it to 232px with page names, which pushes the page over. On the closed rail, hovering or focusing an icon shows its name.
  - **On phones (640px and under):** a thin top bar. Its button slides the nav over the page, and tapping outside or pressing Escape closes it.
  - **Behavior:** the current page is highlighted. Desktop remembers whether the nav was open; phones always start closed. Toggling and links work from the keyboard, with a focus outline, and reduced-motion settings turn off the animation.

### Changed
- **`src/frontend/main.html`:** 2 lines in `<head>` load the nav. Nothing else on the demo page changed, and `main.css` is untouched. The nav's own CSS makes room for itself.
- **`public/brand/wordmark-on-paper.svg`:** the fill of the wordmark's 44 dots changed from `#FDFDFB` to `#F5F4F0` so they match the page background. Everything else is unchanged.

### Decisions
- **Background color:** every page and the nav use `#F5F4F0`. It's a warm off-white close to Claude's, and it's already the demo page's background, so the pages match.
- **Phone layout:** a top bar instead of a floating corner button, because the floating button covered the demo page's header logo.
- **Image paths:** pages link to images with relative paths (`../../public/brand/`). These may need updating when the site is hosted.

---

## 2026-11-13 — Requesting to co-host an event

**Request:** "Add the ability to request to join an event as co-host."

### How it works
- `graph.co_hosting.request(event_id, host_id, by_person_id, now)` lets a person ask for themselves, or an org admin ask for their org. The request stays pending, and the event doesn't appear on the requester's calendar until it's approved.
- **Approving:** a request is approved by anyone acting for a current host of the event, through the same `events.accept_co_host`. That includes co-hosts who were accepted earlier. Invitations still need the invited party to approve.
- **Declining or withdrawing:** the same `events.remove_co_host` covers both. Any current host can decline, and the requester can withdraw. A declined request can be sent again.
- **What's waiting:** `co_hosting.pending(event_id, by)` shows hosts all unanswered invitations and requests on an event. `co_hosting.pending_for(host_id, by)` shows a person or org what it's been invited to or has asked to join. Each side sees only its own.

### Decisions
- **Recording the direction:** `Hosts` gained `origin: HostOrigin` (`INVITED` or `REQUESTED`), which decides who must approve. Older stored links default to `INVITED`, which matches how they were created.
- **Hidden events:** a request about an event the requester can't see fails exactly like a missing event. That covers drafts, members-only events of other orgs and bad ids. It means requests can't be used to probe for hidden events.
- **Event status:** only published events that haven't ended take requests. Cancelled, ended and archived events don't.
- **Separate service:** request lives in a new `CoHostingService` (`graph/cohosting.py`) because it needs the privacy check, and the privacy service already depends on the event service.

### Seed and tests
- **Seed:** Emery has asked to co-host "Robot demo day", and the request is left pending for Casey. The test database passes the integrity check.
- **Tests:** added `tests/backend/test_cohost_requests.py` (24 runs). In total, 363 pass and the 7 known-bug xfails are unchanged. Ruff is clean.

### Not done
- Nobody is notified when a request arrives or is answered. There's no notification system yet.
- The integrity audit can't tell which host approved a request. It only sees that the link was accepted.

---

## 2026-11-13 — People can host, combined events, host calendars, public member lists

**Request:** "The stack can be put off until the frontend is actually made. The people who can post/host events are both individual people and organizations. Add a function to allow more than one person and organization to throw the same event (if it is a combined event, the event must be requested by one party to another and the other accepts). The event should be shown on both organizations' calendars and under their events [public/private]. Member list should be public (for now, but make it easy to change who can see people for any future decision changes)."

### Decisions
- **Stack:** postponed until the frontend exists. No API work has been done.
- **Hosts:** both people and orgs can host. This overrides `user_Orgs.md`, which says HOSTS is Org → Event, and follows the hackathon plan. The spec file itself hasn't been edited.
- **Member lists:** public, controlled by one policy setting. The spec says only the person can make their membership public, so anyone who set their own membership or profile to private stays off the list. One flag (`hide_private_memberships=False`) turns that off.

### Added
- **People as hosts.** A HOSTS edge can start at a Person or an Org. `EventService.acts_for(person, host)` holds the one rule: a person acts for themselves, and for orgs they are an admin of. Creating, editing, inviting, accepting and removing all go through it. Nobody can create an event in someone else's name.
- **Combined events.** `invite_co_host(event, host, by, now)` lets any current host invite a person or an org. Only the invited person, or an admin of the invited org, can `accept_co_host`. The invited party can decline, and either the co-host or the primary host can later remove it with `remove_co_host`. There's no limit on co-hosts, and they can be any mix of people and orgs. New queries: `host_ids` (all accepted hosts) and `host_node`.
- **Host calendars** (`graph.calendar.host_events(host_id, viewer_id, starts_after=, starts_before=)`) return a `HostEvents` with `public` and `private` lists, sorted by start time.
  - **Which events appear:** an event shows on every host that accepted it. Pending invites don't appear, and an event disappears from a co-host's calendar when that co-host leaves.
  - **Private list:** members-only, connections-only or private events, plus drafts. Drafts are shown only to the hosts.
  - **Viewer filtering:** the viewer only sees events they're allowed to see. If the viewer can't see the host, they can't see its calendar either.
- **Member lists** (`graph.roster.members(org_id, viewer_id)`) list confirmed, current members only, ordered by role and then name.
  - `RosterPolicy(audience=...)` decides who can see the list: PUBLIC (the default), NETWORK, MEMBERS or PRIVATE (admins only). To change it, edit `DEFAULT_ROSTER_POLICY` in `graph/roster.py`, or pass `CollectivizeGraph(roster_policy=...)`.
  - A member list is never more visible than the org itself.
- **Discovery:** handles events hosted by a person. They get no trust bonus, show the reason "Hosted by a person", and have `host_freshness=None`.
- **Privacy:** people who host an event can always see it. A connections-only event is visible to the host's connections.
- **Erasing a host:** when a person who was primary host is erased, each of their events passes to the earliest accepted co-host. Events with no other host are deleted along with their edges.
- **Seed:** added "Robotics study jam", hosted by Drew with Robotics Club as co-host (Casey accepted). It appears on both calendars. The test database now has 9 events and passes the integrity check.
- **Tests:** added `tests/backend/test_hosting_and_rosters.py` (41 runs). In total, 339 pass and the 7 known-bug xfails are unchanged. Ruff is clean.

### Changed
- `EventService.create(event, host_id, by_person_id)`: `host_org_id` was renamed `host_id`, and it can now be the creator themselves.
- The existing test `test_co_host_invite_must_target_an_org` became `..._must_target_an_existing_host`, because inviting a person is now allowed.
- Removed an unused `STAFF` import in `test_events_and_privacy.py` and sorted `__all__`. These were lint fixes only.

### Not done
- ~~Requesting to join an event as co-host~~: added in the entry above.
- **Event series:** they still belong to orgs only.
- **Org freshness:** publishing updates only the primary host when it's an org. Co-host orgs aren't credited.
- **Logged-out visitors:** a person-hosted event is hidden from them, because a person's profile is visible only to logged-in users. This follows the rule that an event is never more visible than its host.
- **Event visibility:** it's set at creation time and can't be changed afterwards with `revise`.

---

## 2026-11-13 — Edge-case unit tests

**Request:** "Add more edge cases and test them."

The suite grew from 71 to 228 tests: 221 pass and 7 are marked as known bugs. No source code changed. Run the tests with `.venv/bin/python -m pytest`, or with `uv run pytest` if uv is installed.

### Added
- **`tests/backend/test_objects.py`:** validation boundaries: slug and blank-name rules, malformed URLs, self-loop edges, naive timestamps, and exact freshness and staleness cutoffs. Also the event lifecycle: publishing at the start time, publishing twice, editing frozen or ended events, and when changes are logged.
- **`tests/backend/test_membership_and_hierarchy.py`:** duplicate requests, rejoining after leaving, leaving twice, roles for unconfirmed members, and admin hand-off. For claims: pending claims grant no rights, double claims, and approving the wrong edge. For PART_OF: duplicates, one-sided acceptance, parent-side proposals, staff verification, pending ancestors, more disallowed kinds, and the cycle guard (exercised by loosening the kind table).
- **`tests/backend/test_events_and_privacy.py`:** co-host invite, accept, decline and removal permissions, re-inviting, who gets credit for a publish, tagging rules, and series permissions and defaults. Also every visibility level (NETWORK, MEMBERS, CONNECTIONS, PRIVATE) and the erasure cases.
- **`tests/backend/test_storage.py`:** config trimming and reading from the process environment, a codec round trip for each edge type, timezone offsets, re-validation on decode, store parity between the two backends, nested transactions, `:memory:` SQLite, Unicode, and the environment guard keeping data intact.

### Known bugs (marked `xfail(strict=True)`)
Each test flags itself as soon as its bug is fixed, so the marker can be removed.
1. **`SeriesService.publish_occurrences` is not atomic.** If one start time is invalid, the earlier occurrences stay published.
2. **Cancelling a never-published draft makes it public.** The draft becomes visible and discoverable, which breaks the "drafts are visible only to host admins" rule.
3. **Erasing a person with a pending claim leaves the org stuck in `CLAIM_PENDING`.** `release_if_last_admin` only counts confirmed admins, and no one is left to approve the claim.
4. **The two stores handle nested transactions differently.** With SQLite, a caught failure in an inner `transaction()` still commits; the in-memory store rolls it back.

---

## 2026-11-13 — Genuine connections: graph audit and fixes

**Request:** "Check that the logic is the graph and make sure that it is genuine connections between people and organizations."

### What the check found
- **The services were sound, but the storage layer wasn't.** Every rule (two-sided membership, admin-only confirmation, staff-approved claims) lived in the services. `save_edge` only checked that both endpoints existed, so storage accepted an org being a "member of" another org, a person "hosting" a tag, or a person "part of" an org. A probe script saved all of these without error.
- **Confirmations left no trail.** A confirmed membership didn't record who confirmed it. A hand-written `MemberOf(role=ADMIN, org_confirmed=True)` made someone an admin, and nothing could tell it apart from a real one.
- **People couldn't connect at all.** The `Connected` edge existed, but no code path created it. The only way to make one was to write it directly with both sides already "accepted".
- An ended membership could still be confirmed.

### Added
- **Endpoint rules on every edge type** (`SOURCE_TYPES` / `TARGET_TYPES` in `objects/edges.py`), taken from `user_Orgs.md`:
  - MEMBER_OF and FOLLOWS: Person → Org
  - PART_OF and PARTNERS_WITH: Org → Org
  - HOSTS: Org → Event
  - INSTANCE_OF: Event → EventSeries
  - RSVP and ATTENDED: Person → Event
  - CONNECTED: Person → Person
  - TAGGED: Org or Event → Tag
  - INTERESTED_IN: Person → Tag

  Both stores enforce these in `save_edge` through `check_edge_endpoints`, so nothing can bypass them.
- **`MemberOf.confirmed_by`:** records the admin who confirmed the membership, or the staff member who approved the claim. A confirmed membership without a confirmer can't be constructed, and nobody can confirm their own membership.
- **`ConnectionService`** (`graph.connections`): `request` and `accept` (only the recipient can accept), `remove` (either person can decline or disconnect), `between`, `are_connected` and `connections_of`. There is one edge per pair, and declining or removing hard-deletes it, so no record remains that two people were linked. `PrivacyService.are_connected` now delegates here.
- **`IntegrityService`** (`graph.integrity.audit()`) is read-only. It reports:
  - edges between the wrong kinds of node or pointing at missing nodes;
  - memberships confirmed by someone who was never an admin of that org and that staff didn't approve;
  - claimed orgs with no admin, and admins of unclaimed orgs;
  - connections that neither person requested;
  - PART_OF links between disallowed org kinds;
  - listed events without exactly one primary host.
- **`scripts/check_graph.py`:** runs the audit against the configured database. It exits with 1 if it finds problems.
- **Tests:** `tests/backend/test_connections_and_integrity.py` adds 48 test runs (counting both stores). In total, 148 tests pass and ruff is clean.

### Changed
- `MembershipService.confirm` records the admin and rejects ended memberships. `approve_claim` records the staff id.
- `data/test.db` was re-seeded. The old file failed the audit because its confirmations predate `confirmed_by`. The fresh seed passes, and every confirmed membership traces back to staff or a chapter admin.

### Not done
- The audit can't tell who accepted a co-host invite or a PART_OF link. It only checks the end state. Recording `accepted_by` on those edges would close that gap.
- Per-person visibility of a connection ("visible only if both people allow it") still uses one visibility field per edge.
- There's no way to reject a pending org claim, so a bogus claim leaves the org stuck in `claim_pending`.
- There's no "people closest to people the org knows" query from the README yet. These fixes make that query trustworthy, since it will only walk consented edges.
- A database with old records can't be loaded until it's re-seeded or migrated. There are no migrations yet.

---

## 2026-11-13 — Event discovery query

**Request:** "Build the discovery query."

This is the first user-facing feature. `graph.discovery.search(query, now)` returns upcoming events the viewer is allowed to see. Results can be filtered and paged, and each one is ranked with plain-language reasons.

### How to use it

```python
from backend.database import open_graph
from backend.graph import DiscoveryQuery

with open_graph() as graph:
    page = graph.discovery.search(
        DiscoveryQuery(viewer_id=person_id, text="robot",
                       preferred_tag_ids=(robotics_tag_id,), limit=20),
        now,
    )
    for item in page.items:
        item.event, item.host, item.score, item.reasons, item.is_cancelled
```

### Which events can appear
- Published events that haven't ended yet, including ones already under way.
- Cancelled events, until their original end time. They're flagged with the reason "Cancelled: this event is not happening" (always listed first) and always ranked last, so people who planned to go, even late, find out.
- Never drafts, archived events or ended events.
- Only events the viewer is allowed to see. **The host org must be visible to the viewer too,** so an event is never more exposed than the org running it.

### Filters (`DiscoveryQuery`)

| Field | Effect |
|-------|--------|
| `viewer_id` | Who is looking. `None` means a logged-out visitor. |
| `text` | Case-insensitive match on title, description and location. Max 200 characters. |
| `tag_ids` | The event must match at least one of these tags. The event's own tags and its host orgs' tags both count. |
| `preferred_tag_ids` | The viewer's interests. These **boost** matching events but never filter. |
| `org_id`, `include_related` | Events hosted by an org. By default this includes orgs below it in the hierarchy (e.g. "all IFC chapters"). |
| `starts_after`, `starts_before` | Only events starting within this time range. |
| `include_cancelled` | Default `True`. |
| `limit`, `offset` | Paging. `limit` is 1–100 (default 20). The result reports `total` and `has_more`. |

Invalid queries raise `DomainRuleError`.

### Ranking

Higher scores come first. Ties are broken by start time, then by id. Every factor that moves an event's score adds a reason:

| Factor | Score | Reason shown |
|--------|-------|--------------|
| Host claimed / claim pending / unclaimed | +3 / +1 / 0 | "Hosted by a verified org" / "Host's claim is being verified" / "Unclaimed listing: not managed by the org itself" |
| Host quiet / stale | −1 / −3 | "Host hasn't posted recently" / "Host info may be out of date" |
| Event details verified / disputed | +1 / −3 | "Event details verified" / "Event details are disputed" |
| Each matching interest tag | +2.5 | "Matches your interest: Robotics" |
| How soon it starts | up to +2, fading over 30 days | "Starts within 48 hours" (shown when it starts within 48 hours) |
| Cancelled | −100 | "Cancelled: this event is not happening" (always the first reason) |

All weights are named constants at the top of `discovery.py`, so they're easy to adjust.

### Added
- **`src/backend/graph/discovery.py`:** `DiscoveryQuery`, `DiscoveryItem`, `DiscoveryPage` and `DiscoveryService`.
- **`tests/backend/test_discovery.py`:** 15 test cases, each run against both stores, covering what can appear, visibility, every filter, ranking and reasons, paging, and input checks.

### Changed
- **`src/backend/graph/store.py`, `sqlite_store.py`:** new `nodes(cls)` method lists every node of a type. SQLite gained a `nodes_by_type` index.
- **`src/backend/graph/hierarchy.py`:** new `descendant_ids(org_id)` finds every org below an org through confirmed `PART_OF` links.
- **`src/backend/graph/__init__.py`:** `CollectivizeGraph` now has `.discovery`.

### Checked against the seeded test DB
- A logged-out visitor sees 7 of the 8 events. The draft is hidden, and the cancelled mixer is last.
- When Drew (demo) has robotics as an interest, "Robot demo day" moves to #1 with the reason "Matches your interest: Robotics".

### Decisions
- **Inherited tags:** tags on a host org also apply to its events, so tagging the Robotics Club makes its events show up under robotics.
- **Interests are passed in for now:** `preferred_tag_ids` comes with the query because people's interest edges aren't built yet. Once they are, they can feed this directly.
- **Scan everything, then filter:** each search loads every event and filters in Python. That's fine at pilot scale but should move into SQL queries as data grows.

### Not done yet
- No interest edges, embeddings, follows or "related to orgs you follow" suggestions.
- No API endpoint or frontend to call this.

---

## 2026-11-13 — Separate test and production databases

**Request:** "Make it so there is a test database that stores mockup information and then a production database that stores real data."

There are now two SQLite databases. The test database holds fictional mock data; the production database holds real data. The `COLLECTIVIZE_ENV` variable picks which one is used. Several guards keep mock data out of production and stop either database from being opened as the other.

### How to use it

| Task | Command |
|------|---------|
| Create the test DB with mock data | `uv run python scripts/seed_test_db.py` |
| Wipe and re-seed the test DB | `uv run python scripts/seed_test_db.py --reset` |
| Use the test DB in code (the default) | `with open_graph() as graph: ...` |
| Use the production DB in code | Run with `COLLECTIVIZE_ENV=production` |
| Use a different database file | Set `COLLECTIVIZE_DB_PATH=/path/to/file.db` |

The default files are `data/test.db` and `data/production.db`.

### Added
- **`src/backend/config.py`:** the `Environment` setting (`test` or `production`) and `load_config()`, which reads `COLLECTIVIZE_ENV` and `COLLECTIVIZE_DB_PATH`. It defaults to **test**, so nothing writes real data by accident. Unknown values are rejected.
- **`src/backend/graph/sqlite_store.py`:** `SqliteGraphStore`, a persistent store with the same interface as the in-memory store. It has three tables: `meta`, `nodes` and `edges` (with indexes on source and target). Records are stored as JSON. `transaction()` makes a block of writes all-or-nothing.
- **`src/backend/graph/codec.py`:** converts records to and from JSON exactly (enums, datetimes, durations, nested objects, change-log values). Loaded data goes back through each class's validation. Unknown types or fields are rejected.
- **`src/backend/database.py`:** `open_graph()`, which opens the configured database and closes it when you're done.
- **`src/backend/seed.py`:** `seed_mock_data()` creates a fictional campus: 6 orgs, 5 people, 5 tags and 8 events. That includes a weekly meeting series, a co-hosted fundraiser, a cancelled event, a draft, an unclaimed org and a pending membership request. All writes go through the normal services, so the mock data follows every graph rule.
- **`scripts/seed_test_db.py`:** a command-line script for seeding, with a `--reset` option.
- **Tests:**
  - `tests/backend/test_storage.py`: config, the JSON conversion, the SQLite store, and transactions on both stores.
  - `tests/backend/test_seed.py`: mock data is clearly fake and follows the rules; seeding production is refused.
- **`data/test.db`:** created and seeded.

### Changed
- **`src/backend/graph/store.py`:**
  - `GraphStore` is now an interface that both stores implement.
  - The in-memory store is renamed `InMemoryGraphStore`.
  - It gained `transaction()`, which restores a snapshot if the block fails, and `close()`.
- **`src/backend/graph/__init__.py`:** `CollectivizeGraph()` still uses the in-memory store by default. Pass a `SqliteGraphStore` to persist data.
- **`src/backend/graph/privacy.py`:** `erase_person` now runs in a transaction, so an account deletion can never be left half-done.
- **`tests/backend/conftest.py`:** every service test now runs against **both** stores. There are now 71 tests, up from 33.
- **`.gitignore`:** added `data/`, so database files, and especially real production data, are never committed.

### Safeguards
1. **Seeding production is refused,** both in `seed_mock_data()` and in the seed script.
2. **Each database file is stamped with its environment** the first time it's opened. Opening a production file as test, or the reverse, raises `EnvironmentMismatchError`.
3. **`--reset` only deletes a file stamped as a test database.** I confirmed it refuses when `COLLECTIVIZE_DB_PATH` points at a production file.
4. **Mock records are obviously fake:** org names start with `[Demo]`, people are labelled "(demo …)", and events have `is_demo=True`, which can never be removed.

### Decisions
- **SQLite** (built into Python, no new dependencies) is enough for the pilot. The services only use the `GraphStore` interface, so a Postgres store could be dropped in later.
- **JSON records with indexed edge columns,** rather than one table per type, so adding fields doesn't need a database migration yet.

### Not done yet
- No database migrations or schema versioning.
- No backups for production.
- No dedicated staging environment.

---

## 2026-11-13 — Graph architecture from `user_Orgs.md`

**Request:** "Create the architecture for user_Orgs.md."

The graph spec in `user_Orgs.md` is now an object-oriented Python backend, as `rules.md` requires. Every node and edge type from the spec exists. The four cross-cutting rules (provenance, visibility, recommendation consent, lifecycle) and all the MVP rules are enforced in code. The "Later" types are defined so the schema has a place for them, but their rules aren't enforced yet.

### Added

**Domain objects: `src/backend/objects/`**

All of these are immutable (frozen dataclasses). Changing one returns a new copy.

| File | Contents |
|------|----------|
| `base.py` | `GraphRecord`, the base for every node and edge: id, `Provenance`, `Visibility`, `RecordState`. Also `DomainRuleError` and `most_restrictive()`. |
| `person.py` | `Person` and `VerificationLevel` (records *which* level of identity verification was reached, not how). |
| `organization.py` | `Organization` with `OrgKind`, `ClaimState` (unclaimed, pending, claimed), external links (http/https only), and derived `freshness()` (active, quiet, stale). |
| `event.py` | `Event` with its lifecycle (draft, published, cancelled, ended, archived) and a change log for time and location edits. The demo flag can't be cleared. `EventSeries` holds defaults that its events inherit. |
| `taxonomy.py` | `Tag` (curated, kebab-case slug) and `Venue` (Later). |
| `edges.py` | All edges: `MemberOf`, `PartOf`, `PartnersWith`, `Hosts`, `InstanceOf`, `Rsvp`, `Attended`, `Follows`, `Connected`, `Tagged`, `InterestedIn`. Edges a person owns carry `RecommendationUse`, which defaults to `OWN_ONLY`. |

**Graph services: `src/backend/graph/`**

| File | Rules it enforces |
|------|-------------------|
| `store.py` | In-memory storage for nodes and edges. Hard delete is reserved for account erasure. |
| `membership.py` | The person claims a membership and the org confirms it. Only admins grant roles. Only the person controls their membership's visibility. An org must always have at least one admin. Also handles the claim flow: the org goes from unclaimed to claim pending, and becomes claimed once staff approve. |
| `hierarchy.py` | A `PART_OF` link needs both orgs to accept or staff verification. Only certain org types can link (see `ALLOWED_PART_OF`). An org can have several parents but can never become its own ancestor. |
| `events.py` | Exactly one primary host. Co-hosts count only after they accept and can remove themselves. Only admins of a host org can edit an event. Publishing updates the host org's activity. Admins tag their own orgs and events. |
| `series.py` | An event belongs to at most one series. `publish_occurrences` publishes a semester in one action. Editing the series updates only future events that still use the old default. |
| `privacy.py` | Effective visibility is the most restrictive of the edge and both endpoints. `can_view` checks who is looking. Draft events are visible only to host admins. `erase_person` truly deletes the person's edges. |
| `__init__.py` | `CollectivizeGraph`, which wires the store and all services together. |

**Tests: `tests/backend/`**
- 33 pytest tests covering the objects, membership, hierarchy, events, series and privacy.
- Run them with `uv run --group dev pytest`.

### Changed
- `src/backend/objects/organization.py`: replaced the empty stub with the full `Organization` model.
- `pyproject.toml`: added a `dev` dependency group with pytest, and pytest config (`pythonpath = ["src"]`, `testpaths = ["tests"]`).

### Removed
- `src/backend/objects/user.py`: the empty `User` stub. `Person` in `person.py` replaces it, to match the spec's terms.

### Generated
- `uv.lock` and `.venv/`, created by uv. `.venv` is already gitignored.

### Decisions (the spec doesn't specify these)
- **Visibility order:** public < network < members < connections < private.
- **Freshness:** quiet after 30 days and stale after 90. Measured from the more recent of the last profile confirmation and the last published event.
- **Allowed `PART_OF` links:** chapter → national; chapter or club → council; anything except an institution → institution.
- **Staff actions:** `staff_id` is trusted as given. A future auth layer must check it.
- **Series edits:** an event that was edited on its own keeps its edit.
- **Erasing the last admin's account:** the org goes back to unclaimed instead of blocking the deletion.
- **Hierarchy cycle check:** pending links count too, so accepting one later can never create a cycle.

### Bug fixed
- `HierarchyService.accept` let any user approve a pending link. It checked the link's existing approvals instead of whether the person approving is an admin. A test caught it, and it's fixed.

### Not done yet
- Rules for the "Later" edges (RSVP freezing, small-count suppression, attendance timing) aren't enforced.
- There's no API layer, persistent database or authentication yet.

---

## 2026-11-14 — Profile page on sample data (UI only)

**Request:** "Build a UI-only profile page on sample data, fully independent of Keaton's code."

`src/frontend/profile.html` now shows a profile: full, locked (connections only) or not found. Owners get an edit mode with a live preview. The page runs on three fictional sample profiles (`profile-mock.js`) and saves edits in the browser. No backend code changed. The backend design for real profiles is written up in `docs/profile-backend-proposal.md` (not implemented).

- **To view:** `profile.html?u=maya_r` (full), `?u=theo_k` (locked) or `?u=sam_2027` (mostly empty). Add `&as=self` to see your own page with **Edit page** and **View as visitor**.
- **Connecting it to the backend:** `ProfileDataSource` in `profile.js` is the only place data comes from. It already returns the planned `GET /api/profile` shape, so connecting the real endpoint means changing only that class.
- **Also:** `collectivize_plan.md` now names Keaton in the team list.


Nav header: logo to open, wordmark and toggle when open. In the shared nav (`nav.js`, `nav.css`), the closed rail and phone bar now show the logo, which opens the nav when clicked. Open, the nav shows the wordmark (a link home) with the collapse button at the top right. The home page (`index.html`), opened while signed in with no `?next=`, now hides the sign-in form and makes the wordmark a link to Discover. The tagline under the wordmark ("Find your people on campus…") is removed. The wordmark files in `public/brand/` are replaced with the new black-node versions.


My Events and Calendar are now one page, with hosting, working week/day views and new colours.

- **One page:** `my-events.html` has a **Calendar / List** switch. The nav's separate Calendar entry is gone; `calendar.html` now forwards to `my-events.html?view=calendar` (keeping `?date=`). The view, tab, search and calendar mode are kept in the URL (`?view=&tab=&q=&cal=&date=`).
- **Calendar view:** **Week** and **Day** now work, showing hours down the side, overlapping events side by side and a line for the current time. The arrows step by month, week or day.
- **List view:** four tabs, **Going, Maybe, Saved, Hosting** (an event you host is listed only under Hosting). The search bar uses Discover's search (`GET /api/find?scope=mine`), so typos, dates ("this week") and the "Searching for:" line work the same way. It searches upcoming events only.
- **Hosting:** events you host (yourself, or through an org you run) show only **Add to calendar**, on Discover, in the calendar and in the list.
- **Colours:** Saved is dark gold (the pressed bookmark button matches), My orgs is light blue, Hosting is dark red. Going and Maybe are unchanged.
- **Discover:** no more bubbles above titles on events, people or orgs. "Cancelled" and "Full" are now plain text at the start of the date line. "Add to calendar" is removed except on events you host. "Hosted by …" is bold.
- **Backend:** `GET /api/my-events` now includes events you host, with `hosting: true/false`. `GET /api/find` adds `is_hosting` on events and accepts `scope=mine` (anything else is a 400). `SearchFilters.event_ids` limits a search to given events. Tests: `tests/backend/test_my_events_hosting.py` (30 tests).


Tab icon is the new logo; Saved and Hosting use light fills. `app/icon.svg`, the tab icon every page links to, now holds the current logo (a copy of `public/brand/logo.svg`), and `main.html` now has a tab icon too. On the calendar (key, month chips, week/day blocks), Saved is light gold and Hosting is light red, each with a coloured outline, like Maybe and My orgs. The pressed bookmark button is the same light gold, and the day panel's "Hosting" tag is light red.
