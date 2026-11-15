# Collectivize: notes for coding agents

## Where to work right now

**All work happens on `main` of the fork https://github.com/CodyGrodsky/Collectivize.**
Pushes there deploy themselves to https://collectivize-tau.vercel.app.
Read `VERCEL.md` before changing anything about how the app is served. The original repo `JamesKempel/Collectivize` is parked (its `main` is
the Railway / real-server version); don't build features there until `VERCEL.md` says we've
switched back.

## Pushing (five people share one `main`)

- Before every push: `git pull --rebase`, then push. If the push is rejected, pull again and retry.
  Never force-push `main`.
- Small changes go straight to `main` (live in about 20 seconds). Bigger or risky ones: push a
  branch and open a PR into `main`; Vercel comments a preview link on the PR.
- The live site is shared: say which page you're working on so two people don't change the same
  one at once. The last push wins.
- Never edit `demo/collectivize-demo.db` by hand (it's binary and can't be merged); reseed it
  (see `VERCEL.md`) and tell the others.

## The project

- Python 3.13 backend (standard library HTTP server + SQLite) in `src/backend/`, plain HTML/JS/CSS
  frontend in `src/frontend/`. Dependencies through `uv`.
- Run locally: `uv run python scripts/serve.py --no-login --no-ai` (http://127.0.0.1:3000).
- New machine? `SETUP.md` is the step-by-step setup (tools, GitHub sign-in, invite, clone).
- Tests: `uv run pytest`.
- Deeper references: `docs/BACKEND_REFERENCE.md`, `docs/collectivize-v1.1-spec.md`.

## Rules (from `rules.md`)

1. Every change gets an entry in `docs/CHANGES.md` (newest first, same format as the others).
2. Keep it modular.
3. Keep it object-oriented.

## Never

- Commit `data/` or `config/*.local.json`.
- Make the Vercel deploy depend on secrets, real data, or `COLLECTIVIZE_ENV=production`.
