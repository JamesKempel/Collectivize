# Vercel demo (`main` of the fork CodyGrodsky/Collectivize)

**Live:** https://collectivize-tau.vercel.app

Until further notice, **all UI and feature work happens on `main` of the fork
https://github.com/CodyGrodsky/Collectivize**. Every push to the fork's `main` deploys to the live
URL above in about 20 seconds, and every PR into it gets its own preview link. The original repo
(`JamesKempel/Collectivize`) is parked: its `main` stays the Railway / real-server version and gets
the fork's `main` merged back when we switch over (see "Switching back to Railway").

## What this deploy is

- The whole app (pages + JSON API) runs as **one Vercel Python function**: `api/index.py`.
  It uses the real request handler in `src/backend/server.py`. Nothing in the backend was
  forked or rewritten, so a change to `src/` shows up here exactly as it does locally.
- **All data is fictional.** It comes from `demo/collectivize-demo.db`, a database seeded by
  `scripts/seed_test_db.py` and committed to this branch. No real people, no real accounts.
- **Data resets.** Each function instance copies the demo DB to `/tmp`. Changes (RSVPs, stars,
  profile edits) last while that instance stays warm (minutes), then everything goes back to
  the demo data. Two visitors can see slightly different states. This is on purpose.
- **Everyone is signed in automatically** as `drew.demo@northeastern.edu`. No email codes.
- **AI search is off** (keyword search only), so the public link can't run up an Anthropic bill.
  No API keys or secrets are used by this deploy at all.
- **Demo admin:** go to `/admin` and sign in with username **Billy Joe**, password
  **collectivize-demo**. That's Pat, the fictional platform admin (owner). It's public on
  purpose: the deploy only has fake data. Sign out to go back to Drew.

## Shipping a change

1. One-time setup: clone the fork (Cody adds you as a collaborator so you can push):

   ```
   git clone https://github.com/CodyGrodsky/Collectivize.git collectivize-vercel
   ```

   Or, in your existing clone, point `origin` at the fork:
   `git remote set-url origin https://github.com/CodyGrodsky/Collectivize.git`, then
   `git fetch origin` and `git reset --hard origin/main` (commit or stash your work first).

2. Run it locally first, the same way as always:

   ```
   uv run python scripts/serve.py --no-login --no-ai
   ```

3. Push to `main` on the fork (`git push`) and it deploys itself.
   For anything bigger, push a branch and open a PR into `main`: Vercel comments a
   preview link on the PR.

Manual deploy, if ever needed (Cody's machine, logged in to the Vercel project):
`vercel deploy --prod --yes` (on Windows with scripts blocked: `vercel.cmd`).

## Rules that still apply

- `rules.md`: log every change in `docs/CHANGES.md`, keep it modular, keep it object-oriented.
- Never commit `data/` (local databases) or `config/*.local.json` (secrets).
- Don't make the deploy depend on secrets, real data, or `COLLECTIVIZE_ENV=production`.
  The public URL must stay safe to share with anyone.

## Files that exist only for Vercel

| File | What it does |
|---|---|
| `api/index.py` | The function. Copies the demo DB to `/tmp`, builds the server state once per instance, and hands each request to the normal `RequestHandler`. |
| `vercel.json` | Sends every address to the function (`/api/index?__path=<original>`), and bundles `src/`, `public/`, `app/` and `demo/` with it. |
| `.vercelignore` | Keeps `.venv`, `data/`, tests and local secrets out of the upload. |
| `demo/collectivize-demo.db` | The fictional demo database. |

To refresh the demo data after a seed or schema change:

```
COLLECTIVIZE_DB_PATH=demo/collectivize-demo.db uv run python scripts/seed_test_db.py --reset
```

## Switching back to Railway

The backend is untouched, so switching back is a merge, not a migration:

1. Open a PR from `CodyGrodsky/Collectivize:main` into `JamesKempel/Collectivize:main` and merge it.
2. Delete `api/`, `vercel.json`, `.vercelignore` and `demo/` (or keep them for preview deploys:
   they don't affect `scripts/serve.py`).
3. Deploy `main` to Railway with a persistent volume for `data/`.
4. Delete the "work on the fork" notes from `CLAUDE.md`, `AGENTS.md` and `HANDOFF.md`.
