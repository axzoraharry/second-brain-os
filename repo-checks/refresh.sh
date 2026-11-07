#!/usr/bin/env sh
# refresh.sh — run the repo-checks engine, commit and push the fresh report.
#
# Usage:
#   ./refresh.sh                      # uses GH_TOKEN env, else `gh auth token`
#   GH_TOKEN=... ./refresh.sh
#
# Safe to run from any host that has: python3 + requests, git, and push access
# to this repository. Dry-run discipline is preserved: only --apply writes the
# log, and this script only commits when the file actually changed.

set -eu

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$HERE"

# Token: explicit env wins, then the GitHub CLI, then fail loudly.
if [ -z "${GH_TOKEN:-}" ]; then
  if command -v gh >/dev/null 2>&1 && gh auth token >/dev/null 2>&1; then
    export GH_TOKEN
    GH_TOKEN=$(gh auth token)
  else
    echo "refresh.sh: GH_TOKEN not set and \`gh auth token\` failed" >&2
    exit 1
  fi
fi

echo "== repo-checks: running engine (--apply) =="
python3 repo_checks.py --apply

if [ -n "$(git status --porcelain data/repo-checks.json)" ]; then
  echo "== committing refreshed report =="
  git add data/repo-checks.json
  git commit -m "chore(repo-checks): refresh check history ($(date -u +%F))" || true
  git push
else
  echo "== no change — report already current =="
fi
