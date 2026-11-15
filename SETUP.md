# Setup for a new teammate (written for their coding agent)

You're setting up a teammate's machine to work on Collectivize. Do each step yourself, skip any
that's already done, and only stop for the steps marked **(human)**. Check the OS first
(`uname -s`: `Darwin` is a Mac). Most of the team is on Macs.

## 1. Tools: git, gh (GitHub CLI), uv

Check what's there: `git --version`, `gh --version`, `uv --version`.

### Mac

- **If Homebrew is installed** (`brew --version` works): `brew install git gh uv`. Done.
- **If not, don't install Homebrew** (it needs the human's admin password). Instead:
  - **git:** if `git --version` opens a dialog to install the "command line developer tools",
    tell the human to click **Install** and wait (a few minutes). **(human)**
  - **uv:** `curl -LsSf https://astral.sh/uv/install.sh | sh` (installs to `~/.local/bin`, no password).
  - **gh:** download the latest macOS release from GitHub without a password:

    ```
    mkdir -p ~/.local/bin /tmp/gh-install && cd /tmp/gh-install
    ARCH=$( [ "$(uname -m)" = "arm64" ] && echo arm64 || echo amd64 )
    URL=$(curl -s https://api.github.com/repos/cli/cli/releases/latest \
      | grep -o "https://[^\"]*macOS_${ARCH}\.zip" | head -1)
    curl -sL "$URL" -o gh.zip && unzip -q -o gh.zip
    cp gh_*/bin/gh ~/.local/bin/ && cd ~ && rm -rf /tmp/gh-install
    ```

  - Make sure `~/.local/bin` is on PATH: add `export PATH="$HOME/.local/bin:$PATH"` to `~/.zshrc`
    if it isn't, and use `~/.local/bin/gh` / `~/.local/bin/uv` directly in the current shell.

### Windows

```
winget install --id Git.Git -e --accept-source-agreements --accept-package-agreements
winget install --id GitHub.cli -e --accept-source-agreements --accept-package-agreements
winget install --id astral-sh.uv -e --accept-source-agreements --accept-package-agreements
```

New tools may not be on PATH in an open shell: call them by full path
(`C:\Program Files\GitHub CLI\gh.exe`). If PowerShell says "running scripts is disabled", use the
`.cmd`/`.exe` version of the command. Don't change the execution policy.

## 2. GitHub sign-in **(human approves)**

```
gh auth login --web --git-protocol https --hostname github.com
gh auth setup-git
```

`gh auth login` prints a one-time code and opens the browser: tell the human to copy the code,
paste it on the GitHub page and click **Authorize**. `gh auth setup-git` makes `git push` use the
same login. (If it asks a question first, the answer is Enter / yes.)

## 3. Accept the invite to the repo (you can do this for them)

```
gh api user/repository_invitations --jq '.[] | select(.repository.full_name=="CodyGrodsky/Collectivize") | .id'
gh api -X PATCH user/repository_invitations/<that id>
```

No invite listed? Check `gh repo view CodyGrodsky/Collectivize --json viewerPermission`: WRITE or
ADMIN means they're already in. READ means they need an invite from Cody: tell the human.

## 4. Clone and install

```
cd ~
git clone https://github.com/CodyGrodsky/Collectivize.git collectivize-vercel
cd collectivize-vercel
uv sync
```

(`uv` downloads Python 3.13 by itself if needed.)

## 5. Check it runs, then stop it

```
uv run python scripts/seed_test_db.py --size small
uv run python scripts/serve.py --no-login --no-ai
```

http://127.0.0.1:3000 should show the app signed in as Drew. Stop the server (Ctrl-C).
`data/` is git-ignored, so the local database never gets committed.

## 6. Hand over

Tell the human it's done, and that from now on they should **open the `collectivize-vercel`
folder** (in `~`) in Claude Code and just say what to change. Pushes to `main` go live at
https://collectivize-tau.vercel.app in about 20 seconds. Then read `CLAUDE.md` in the repo and
follow it: it has the push rules (always `git pull --rebase` before pushing).
