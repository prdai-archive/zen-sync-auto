# zen-sync-auto

One-command Zen Browser sync between machines. Fork of
[zen-sync](https://github.com/prdai-archive/zen-sync) with the SSH mode and
age encryption stripped out, and everything collapsed into a single command.

```
zensync
```

That's it. It closes Zen, pulls whatever is in your R2 bucket, merges tabs
and workspaces, takes the newer copy of everything else, pushes the merged
result back up, and reopens Zen. Run it before you close your laptop and
again when you open the other machine, and logins/cookies/bookmarks/tabs
just show up.

## What gets synced

- Workspaces, spaces, tabs, tab groups, folders — merged (deduped by URL +
  workspace), not overwritten
- Bookmarks + history (`places.sqlite`), favicons
- Cookies (`cookies.sqlite`) and saved logins (`logins.json` + `key4.db`)
- Site permissions (`permissions.sqlite`)
- Prefs, containers, and UI layout (`prefs.js`, `xulstore.json`) — sidebar
  placement, toolbar customizations, etc.

Anything that isn't a session/tab file (i.e. can't be meaningfully merged)
is copied whichever side has the newer mtime — last-write-wins per file, not
per bucket.

## ⚠️ No encryption, by design

This fork uploads a **plaintext** tar to your R2 bucket over HTTPS (TLS
in transit only, nothing at rest). That tar contains your cookies and saved
logins — i.e. active session tokens and passwords for every site you're
logged into. Anyone with read access to that bucket can take over those
sessions without a password.

This tradeoff only makes sense if:
- The R2 bucket is **private** (default — just don't make it public)
- The API token you generate is **scoped to this one bucket only**
- You're not sharing the bucket or credentials with anyone else

If you want encryption at rest, use upstream
[zen-sync](https://github.com/prdai-archive/zen-sync) instead (age + R2, or
SSH direct device-to-device).

## Setup

```bash
./install.sh
zensync init   # on machine A — pick/create the R2 bucket, get credentials
zensync init   # on machine B — same account ID / bucket / keys
```

`init` needs a Cloudflare account ID, an R2 API token (access key + secret),
and a bucket name. Create the token in the Cloudflare dashboard scoped to
R2 → your bucket → Object Read & Write.

## Usage

```bash
zensync           # close Zen, merge with remote, push, reopen Zen
zensync status     # see when the bucket was last updated and by which host
```

No scheduler is set up — run it manually when you switch machines. (If you
want it automatic on login/logout later, that's a small addition on top —
not built in here on purpose, to keep this to one predictable command.)

## Requirements

- `python3`
- `liblz4` (for reading/writing Zen's `.jsonlz4` session files) —
  `brew install lz4` / `sudo pacman -S lz4` / `apt install liblz4-1`
- macOS or Linux (X11/Wayland desktop or Flatpak Zen)
