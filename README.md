# zen-sync-auto

One-command Zen Browser sync between machines. Fork of
[zen-sync](https://github.com/prdai-archive/zen-sync), backed by a private
GitHub repo instead of a cloud bucket, using your existing `gh auth login`
session — no separate credentials, no encryption layer to manage.

```
zensync
```

That's it. It closes Zen, pulls whatever is in the private data repo,
merges tabs and workspaces, takes the newer copy of everything else, pushes
the merged result back, and reopens Zen. Run it before you close your
laptop and again when you open the other machine, and logins, cookies,
bookmarks, and tabs just show up.

## What gets synced

- Workspaces, spaces, tabs, tab groups, folders — merged (deduped by URL +
  workspace), not overwritten
- Bookmarks + history (`places.sqlite`), favicons
- Cookies (`cookies.sqlite`) and saved logins (`logins.json` + `key4.db`)
- Site permissions (`permissions.sqlite`), per-site zoom/prefs
  (`content-prefs.sqlite`), form autofill (`formhistory.sqlite`)
- Prefs, containers, and UI layout (`prefs.js`, `xulstore.json`) — sidebar
  placement, toolbar customizations, etc.
- Installed extensions and their per-extension settings (`extensions/`,
  `browser-extension-data/`, `extensions.json`, `extension-preferences.json`,
  `extension-settings.json`, `addonStartup.json.lz4`)
- Custom search engines (`search.json.mozlz4`), default app/protocol
  handlers (`handlers.json`), address autofill (`autofill-profiles.json`)
- Zen-specific settings: keyboard shortcuts, themes, live folders, tab notes,
  and custom `userChrome`/`userContent` CSS (`chrome/`)

Not synced, on purpose:
- `storage/` — per-site IndexedDB/localStorage. Often 500MB+ of web app
  cache, not a setting; would blow up the git repo.
- Firefox-Sync-account state (`weave/`, `signedInUser.json`,
  `storage-sync-v2.sqlite`, `synced-tabs.db`) — would fight with this tool's
  own sync mechanism if you're also signed into Firefox/Mozilla Sync.
- Cert store (`cert9.db`, `cert_override.txt`) — niche; open an issue if you
  need this.

Anything that isn't a session/tab file (i.e. can't be meaningfully merged)
is copied from whichever side has the newer content, decided by comparing
the local file's mtime against the data repo's last commit touching that
path — not just "whoever pushed last wins."

## How storage works

`zensync init` creates (or reuses) a **private** GitHub repo — default
`prdai-archive/zensync-data` — and clones it to
`~/.local/share/zensync/repo`. Every sync commits the current profile state
there and pushes. Auth is entirely `gh`'s: the script pulls a token via
`gh auth token` and passes it as a transient header on each git operation —
it's never written into `.git/config` or any file on disk.

Commits into the data repo are made under a fixed `Claude
<noreply@anthropic.com>` identity, not your real git name/email, so the
repo's commit log doesn't leak personal info even though it's already
private.

## ⚠️ No encryption, by design

The data repo holds **plaintext** cookies and saved logins — i.e. active
session tokens and passwords for every site you're logged into. This is
safe only as long as:

- The repo stays **private** (never flip it public)
- You don't add outside collaborators to it
- Your `gh` session / GitHub account itself is secured (2FA, etc.) — anyone
  with access to your GitHub account or a clone of that repo has your
  sessions

If you want an encrypted-at-rest option instead, use upstream
[zen-sync](https://github.com/prdai-archive/zen-sync) (age + R2, or SSH
direct device-to-device).

## Setup

```bash
gh auth login          # if you haven't already
./install.sh
zensync init             # on machine A — creates the private data repo
zensync init             # on machine B — same owner/repo name, own gh auth
```

## Usage

```bash
zensync           # close Zen, merge with remote, push, reopen Zen
zensync status     # see when the data repo was last synced and from where
```

No scheduler is set up — run it manually when you switch machines.

## Requirements

- `gh` (GitHub CLI), logged in via `gh auth login`
- `python3`
- `liblz4` (for reading/writing Zen's `.jsonlz4` session files) —
  `brew install lz4` / `sudo pacman -S lz4` / `apt install liblz4-1`
- macOS or Linux (X11/Wayland desktop or Flatpak Zen)
