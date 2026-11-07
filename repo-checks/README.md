# repo-checks

A self-contained engine that verifies every repository on a GitHub account and
logs an honest, timestamped verdict per repo. It is the "admin table" for the
Second Brain OS surface: GitHub repos, AI-agent clones, and local checkouts —
one interface that says *pass / fail / unknown / skip* per check, with **unknown
stated explicitly rather than guessed**.

This folder ships with:

| path | what it is |
|---|---|
| `repo_checks.py` | the engine (stdlib `requests` only; no API keys needed) |
| `tests/test_repo_checks.py` | 10 pure-logic tests — no network, no git mutation |
| `data/repo-checks.json` | the last check result, **tracked** so history is visible over time |

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

## Config via environment

| var | default | use |
|---|---|---|
| `GH_OWNER` | `axzoraharry` | account to verify |
| `GH_TOKEN` / `GITHUB_TOKEN` | — | auth (else `gh auth token`) |
| `REPO_LOCAL_DIR` | `/root/repos` | where local clones live |
| `REPO_LOG` | `data/repo-checks.json` | log path |
