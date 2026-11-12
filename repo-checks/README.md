# repo-checks

A self-contained engine that verifies every repository on a GitHub account and
logs an honest, timestamped verdict per repo. It is the "admin table" for the
Axzora Brain OS surface: GitHub repos, AI-agent clones, and local checkouts —
one interface that says *pass / fail / unknown / skip* per check, with **unknown
stated explicitly rather than guessed**.

This folder ships with:

| path | what it is |
|---|---|
| `repo_checks.py` | the engine (stdlib `requests` only; no API keys needed) |
| `tests/test_repo_checks.py` | 10 pure-logic tests — no network, no git mutation |
| `data/repo-checks.json` | the last check result, **tracked** so history is visible over time |
| `dashboard.html` | the **Control Room** frontend — single-file animated dashboard |
| `DESIGN-PROMPT.md` | the detailed UI/UX redesign prompt the dashboard implements |

## The Control Room dashboard

`dashboard.html` is a self-contained (no build, no CDN) frontend that turns
`data/repo-checks.json` into a live mission console:

- **Hero tiles** with count-up numbers + a verdict donut.
- **Automation pipeline** — Discover → Fetch → Check → Verdict → Log → Ship,
  drawn from the engine's real lifecycle (amber "preview" in dry-run, green in
  apply).
- **4D card grid** — 3D tilt + cursor-tracking glare, FLIP reordering on
  filter/sort, spring-eased entrance stagger.
- Search (repo names), verdict filter chips, grid ↔ table toggle.
- Reduced-motion + responsive (3 → 2 → 1 column) paths included.

Serve it and open in a browser:

```bash
python3 -m http.server 8899        # from this folder
# open http://127.0.0.1:8899/dashboard.html
```

It fetches `data/repo-checks.json`; if offline it falls back to an embedded
sample. `DESIGN-PROMPT.md` is the full spec (tokens, motion inventory,
automation workflow, accessibility) — feed it to any design generator to
extend the experience.

## Verdicts

Each repo gets one of: `ok`, `unlicensed`, `abandoned`, `fail`, `unknown`,
`warn`, `archived`, `disabled`.

## Checks

| check | verifies |
|---|---|
| `license` | recognised SPDX licence. `NOASSERTION` → unknown, none → fail |
| `readme` | README in the default branch (per-repo API call) |
| `ci` | GitHub Actions workflows present (per-repo API call) |
| `description` | non-empty description (soft warn) |
| `staleness` | days since last push → fresh / aging / stale / abandoned (>365d) |
| `local_checkout` | cloned under `--local-dir/<name>` (default `/root/repos`) |
| `local_sync` | local clone vs `origin/<branch>` — in sync / behind / unpushed / dirty |

## Run

```bash
export GH_TOKEN=...                 # or GH_TOKEN=$(gh auth token)
python3 repo_checks.py              # dry-run (default): console table, writes nothing
python3 repo_checks.py --apply      # also write data/repo-checks.json
python3 repo_checks.py --html table.html     # render the admin table as HTML
python3 repo_checks.py --shallow             # skip readme/CI calls (fast)
python3 repo_checks.py --include-forks       # also verify forks
python3 repo_checks.py --json | jq .summary  # machine readable
python3 -m unittest discover -s tests -v     # 10 tests
```

**Dry-run by default** — it only reads (GitHub API + local `git` metadata) and
never mutates a clone, clones anything, or writes the log unless you pass
`--apply`.

## Check history

`data/repo-checks.json` is committed (not gitignored). Every entry carries:

- `checked_at` — when this repo was last checked
- `previously_checked_at` — when it was checked the run before
- `check_age_days` — how stale the *previous* check was

…so the table shows staleness of the **check itself**, not just the repo. Run
`--apply` on a schedule (cron / GitHub Actions) to keep the history fresh.

### Scheduled refresh

- **GitHub Actions** — `.github/workflows/repo-checks.yml` runs daily and on
  `workflow_dispatch`, then commits the refreshed report. It needs one secret,
  `GH_TOKEN` (a PAT with read access to the account's repos — the automatic
  `GITHUB_TOKEN` is scoped to this repo only). Actions must be unblocked on the
  account (a billing hold previously failed every job).
- **Any host** — `./refresh.sh` runs the engine with `--apply`, then commits and
  pushes only if the report changed. Point a cron line at it anywhere with
  python3 + git + push access:

```bash
23 3 * * * cd /path/to/second-brain-os/repo-checks && ./refresh.sh >> refresh.log 2>&1
```

### Hosting

The dashboard is a single static file that fetches `data/repo-checks.json` by
relative path, so it works from any static host (GitHub Pages, nginx, NAS,
`python3 -m http.server`). On GitHub Pages it lives at
`https://<owner>.github.io/second-brain-os/repo-checks/dashboard.html`.

## Config via environment

| var | default | use |
|---|---|---|
| `GH_OWNER` | `axzoraharry` | account to verify |
| `GH_TOKEN` / `GITHUB_TOKEN` | — | auth (else `gh auth token`) |
| `REPO_LOCAL_DIR` | `/root/repos` | where local clones live |
| `REPO_LOG` | `data/repo-checks.json` | log path |
