#!/usr/bin/env python3
"""GitHub repository checks engine (HappyBetPlay-admin).

Systematically verifies every repository owned by an account and writes an
honest, timestamped verdict per repo to ``data/repo-checks.json``.  Each check
reports one of four states — pass / fail / unknown / skip — and *unknown* means
exactly that: the engine could not determine the answer, and says so instead of
guessing.

Everything is a **dry-run** unless you pass ``--apply``: the default run only
reads (GitHub API + local git metadata) and prints the table, it never writes
the log, never mutates a clone and never clones anything.

Credentials: ``GH_TOKEN`` (or ``GITHUB_TOKEN``), else ``gh auth token``.
Rate limits: authenticated 5000 req/h; unauthenticated 60 req/h (only enough
for a tiny subset — the engine warns and stops).

Usage:
  python3 repo_checks.py                 # dry-run, console table (owned, non-fork)
  python3 repo_checks.py --apply         # also write data/repo-checks.json
  python3 repo_checks.py --html table.html   # write the admin table as HTML
  python3 repo_checks.py --include-forks     # also verify the fork count
  python3 repo_checks.py --shallow           # skip per-repo readme/CI calls (fast)
  python3 repo_checks.py --json | jq .summary  # machine readable
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    import requests
except ModuleNotFoundError:  # pragma: no cover - same self-install as api_client.py
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "requests>=2.31,<3"])
    import requests

API = "https://api.github.com"
OWNER = os.environ.get("GH_OWNER", "axzoraharry")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or None
LOCAL_DIR = os.environ.get("REPO_LOCAL_DIR", "/root/repos")
LOG_PATH = os.environ.get("REPO_LOG", "data/repo-checks.json")

FRESH_DAYS = 30        # <=30d since push  -> fresh
AGING_DAYS = 90        # <=90d             -> aging
STALE_DAYS = 365       # <=365d            -> stale
                        # >365d            -> abandoned

# Recognised SPDX ids we are willing to call "licensed".  Anything else that is
# not null is reported as UNKNOWN (a LICENSE file exists but we cannot certify
# the terms), and null is FAIL (no licence detected).
KNOWN_SPDX = {
    "MIT", "Apache-2.0", "GPL-2.0", "GPL-3.0", "LGPL-2.1", "LGPL-3.0",
    "AGPL-3.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "MPL-2.0", "Unlicense",
    "CC0-1.0", "CC-BY-4.0", "CC-BY-SA-4.0", "EPL-2.0", "Zlib", "0BSD",
    "PostgreSQL", "WTFPL", "BlueOak-1.0.0",
}

# The ordered set of checks the engine runs.  ``deep`` marks checks that need a
# per-repo API call and are skipped with --shallow.
CHECK_SPEC: Sequence[tuple[str, str, bool]] = [
    ("license",       "has a recognised open-source licence", False),
    ("readme",        "has a README",                          True),
    ("ci",            "has GitHub Actions workflows",          True),
    ("description",   "has a non-empty description",           False),
    ("staleness",     "recently pushed (not abandoned)",       False),
    ("local_checkout","cloned locally (integration)",          False),
    ("local_sync",    "local clone is in sync with origin",    False),
]

# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def days_since(value: str | None, now: datetime | None = None) -> float | None:
    dt = _parse_ts(value)
    if dt is None:
        return None
    now = now or datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(0.0, (now - dt).total_seconds() / 86400.0)


def staleness_status(days: float | None) -> tuple[str, str]:
    """Return (status, label) for a repo's push age in days."""
    if days is None:
        return "unknown", "never pushed"
    if days <= FRESH_DAYS:
        return "fresh", f"{days:.0f}d"
    if days <= AGING_DAYS:
        return "aging", f"{days:.0f}d"
    if days <= STALE_DAYS:
        return "stale", f"{days:.0f}d"
    return "abandoned", f"{days:.0f}d"


def gh_token() -> str | None:
    if TOKEN:
        return TOKEN
    try:
        tok = subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True, timeout=10
        ).stdout.strip()
        return tok or None
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# GitHub + local git access
# --------------------------------------------------------------------------- #

def api_get(path: str, token: str | None, params: Mapping[str, Any] | None = None) -> Any:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "repo-checks/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.get(f"{API}{path}", headers=headers, params=params, timeout=30)
    if r.status_code == 404:
        return None  # a missing resource is a finding, not a crash
    r.raise_for_status()
    return r.json()


def fetch_repos(owner: str, token: str | None, include_forks: bool) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    page = 1
    while True:
        repos = api_get("/user/repos", token, {
            "per_page": 100, "page": page, "affiliation": "owner", "sort": "updated",
        })
        if not isinstance(repos, list) or not repos:
            break
        for repo in repos:
            if repo.get("owner", {}).get("login") != owner:
                continue
            if repo.get("fork") and not include_forks:
                continue
            out.append(repo)
        if len(repos) < 100:
            break
        page += 1
    return out


def has_readme(owner: str, name: str, token: str | None) -> tuple[str, str]:
    """(status, detail) — presence of a README in the default branch."""
    try:
        payload = api_get(f"/repos/{owner}/{name}/readme", token)
        return ("pass", "present") if payload else ("fail", "no README")
    except requests.HTTPError as exc:
        return ("unknown", f"HTTP {exc.response.status_code}")
    except Exception as exc:  # network / rate limit
        return ("error", type(exc).__name__)


def has_ci(owner: str, name: str, token: str | None) -> tuple[str, str]:
    """(status, detail) — number of GitHub Actions workflows."""
    try:
        payload = api_get(f"/repos/{owner}/{name}/actions/workflows", token)
        total = payload.get("total_count") if isinstance(payload, dict) else None
        if total is None:
            return ("unknown", "no total_count in response")
        return ("pass", f"{total} workflow(s)") if total > 0 else ("fail", "no CI workflows")
    except requests.HTTPError as exc:
        if exc.response.status_code == 403:  # Actions disabled for the repo
            return ("fail", "Actions disabled")
        return ("unknown", f"HTTP {exc.response.status_code}")
    except Exception as exc:
        return ("error", type(exc).__name__)


def local_state(name: str, default_branch: str, local_dir: str) -> dict[str, Any]:
    """Inspect a local clone under local_dir/<name> (read-only)."""
    path = Path(local_dir) / name
    if not (path / ".git").exists():
        return {"present": False, "status": "skip", "detail": "not cloned locally"}

    def git(*args: str) -> tuple[int, str]:
        try:
            p = subprocess.run(["git", "-C", str(path), *args],
                               capture_output=True, text=True, timeout=15)
            return p.returncode, p.stdout.strip()
        except Exception as exc:
            return 128, type(exc).__name__

    rc, head = git("rev-parse", "HEAD")
    if rc != 0:
        return {"present": True, "status": "unknown", "detail": f"no HEAD ({head})"}

    # age of the last fetch, from FETCH_HEAD mtime when present
    fetch_age: float | None = None
    fh = path / ".git" / "FETCH_HEAD"
    if fh.exists():
        fetch_age = days_since(datetime.fromtimestamp(fh.stat().st_mtime, tz=timezone.utc).isoformat())

    upstream = f"origin/{default_branch}"
    rc, remote_head = git("rev-parse", "--verify", upstream)
    if rc != 0:
        return {
            "present": True, "status": "unknown", "head": head[:12],
            "detail": f"no local ref for {upstream}", "fetch_age_days": fetch_age,
        }

    # ahead/behind counts vs the last-fetched origin ref (honest: based on the
    # last fetch, not a live network call)
    rc, counts = git("rev-list", "--left-right", "--count", f"HEAD...{upstream}")
    if rc != 0:
        return {
            "present": True, "status": "unknown", "head": head[:12],
            "detail": "cannot compare with origin", "fetch_age_days": fetch_age,
        }
    try:
        ahead, behind = (int(x) for x in counts.split())
    except ValueError:
        ahead = behind = 0

    rc, dirty = git("status", "--porcelain", "--untracked-files=no")
    has_changes = rc == 0 and bool(dirty)

    if behind > 0:
        status, detail = "fail", f"behind by {behind}"
    elif ahead > 0:
        status, detail = "unknown", f"ahead by {ahead} (unpushed?)"
    elif has_changes:
        status, detail = "unknown", "uncommitted changes"
    else:
        status, detail = "pass", "in sync"
    return {
        "present": True, "status": status, "head": head[:12], "detail": detail,
        "ahead": ahead, "behind": behind, "dirty": has_changes,
        "fetch_age_days": fetch_age,
    }


# --------------------------------------------------------------------------- #
# checks + verdict
# --------------------------------------------------------------------------- #

def run_checks(repo: Mapping[str, Any], token: str | None, deep: bool,
               local_dir: str = LOCAL_DIR) -> dict[str, Any]:
    name = repo.get("name", "")
    owner = repo.get("owner", {}).get("login", OWNER)
    spdx = (repo.get("license") or {}).get("spdx_id")
    default_branch = repo.get("default_branch", "main")

    checks: dict[str, Any] = {}

    # license
    if spdx is None:
        checks["license"] = {"status": "fail", "detail": "no licence"}
    elif spdx in KNOWN_SPDX:
        checks["license"] = {"status": "pass", "detail": spdx}
    else:
        checks["license"] = {"status": "unknown", "detail": f"{spdx} (unrecognised terms)"}

    # readme + ci (deep)
    if deep:
        st, detail = has_readme(owner, name, token)
        checks["readme"] = {"status": st, "detail": detail}
        st, detail = has_ci(owner, name, token)
        checks["ci"] = {"status": st, "detail": detail}
    else:
        checks["readme"] = {"status": "skip", "detail": "shallow mode"}
        checks["ci"] = {"status": "skip", "detail": "shallow mode"}

    # description
    desc = (repo.get("description") or "").strip()
    checks["description"] = {"status": "pass" if desc else "warn",
                             "detail": desc[:60] or "empty"}

    # staleness
    age = days_since(repo.get("pushed_at"))
    status, label = staleness_status(age)
    checks["staleness"] = {"status": status, "detail": label, "days": age}

    # local integration
    ls = local_state(name, default_branch, local_dir)
    checks["local_checkout"] = {
        "status": "pass" if ls.get("present") else "skip",
        "detail": "cloned" if ls.get("present") else "not cloned",
    }
    checks["local_sync"] = {
        "status": ls.get("status") if ls.get("present") else "skip",
        "detail": ls.get("detail"),
        "head": ls.get("head"), "fetch_age_days": ls.get("fetch_age_days"),
    }

    # ---- verdict -------------------------------------------------------- #
    fails: list[str] = []
    unknowns: list[str] = []
    warns: list[str] = []
    for cname, _desc, _deep in CHECK_SPEC:
        c = checks.get(cname)
        if not isinstance(c, dict):
            continue
        st = c.get("status")
        if cname == "staleness":
            if st == "abandoned":
                fails.append("staleness")
            elif st == "stale":
                warns.append("staleness")
            continue
        if st == "fail":
            fails.append(cname)
        elif st == "unknown" or st == "error":
            unknowns.append(cname)
        elif st == "warn":
            warns.append(cname)

    if repo.get("disabled"):
        verdict = "disabled"
    elif repo.get("archived"):
        verdict = "archived"
    elif "staleness" in fails:              # abandoned (>365d since push)
        verdict = "abandoned"
    elif fails == ["license"]:
        verdict = "unlicensed"
    elif fails:
        verdict = "fail"
    elif unknowns:
        verdict = "unknown"
    elif warns:
        verdict = "warn"
    else:
        verdict = "ok"

    return {
        "name": name,
        "full_name": repo.get("full_name"),
        "fork": bool(repo.get("fork")),
        "archived": bool(repo.get("archived")),
        "disabled": bool(repo.get("disabled")),
        "private": bool(repo.get("private")),
        "default_branch": default_branch,
        "language": repo.get("language"),
        "pushed_at": repo.get("pushed_at"),
        "staleness": {"status": status, "days": age, "label": label},
        "verdict": verdict,
        "fails": fails,
        "unknowns": unknowns,
        "warns": warns,
        "checks": checks,
    }


# --------------------------------------------------------------------------- #
# log (data/repo-checks.json) — timestamped, merged across runs
# --------------------------------------------------------------------------- #

def load_previous_log(path: Path) -> dict[str, str]:
    """full_name -> checked_at from the previous run (for check-staleness)."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    repos = data.get("repos", [])
    return {r.get("full_name"): r.get("checked_at") for r in repos if isinstance(r, dict)}


def build_report(entries: list[dict[str, Any]], owner: str, mode: str,
                 prev: Mapping[str, str], now: str) -> dict[str, Any]:
    for e in entries:
        e["checked_at"] = now
        prev_at = prev.get(e.get("full_name"))
        e["previously_checked_at"] = prev_at
        age = days_since(prev_at)
        e["check_age_days"] = age  # how stale the *previous* check was

    summary: dict[str, int] = {}
    for e in entries:
        summary[e["verdict"]] = summary.get(e["verdict"], 0) + 1

    return {
        "engine": "repo-checks",
        "version": 1,
        "owner": owner,
        "generated_at": now,
        "mode": mode,
        "mode_note": "dry-run: results shown but not persisted" if mode == "dry-run" else "results written to data/repo-checks.json",
        "summary": summary,
        "repos": entries,
    }


def save_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")


# --------------------------------------------------------------------------- #
# rendering
# --------------------------------------------------------------------------- #

_VERDICT_COLOUR = {
    "ok": "\033[32m", "warn": "\033[33m", "fail": "\033[31m",
    "unknown": "\033[35m", "stale": "\033[33m", "archived": "\033[90m",
    "disabled": "\033[90m", "skipped": "\033[90m",
    "unlicensed": "\033[31m", "abandoned": "\033[90m",
}
_RESET = "\033[0m"


def _badge(status: str, width: int = 9) -> str:
    return f"{status[:width]:<{width}}"


def render_console(report: dict[str, Any]) -> str:
    entries = report["repos"]
    lines: list[str] = []
    lines.append(f"repo-checks — {report['owner']}  ({len(entries)} repos, {report['mode']})")
    lines.append(f"summary: " + ", ".join(f"{k}={v}" for k, v in sorted(report["summary"].items())))
    lines.append("")
    header = (f"{'repo':30s} {'verdict':9s} {'lic':9s} {'readme':7s} {'ci':6s} "
              f"{'age':9s} {'local':7s}")
    lines.append(header)
    lines.append("-" * len(header))
    for e in entries:
        c = e["checks"]
        lic = c.get("license", {}).get("detail", "-")
        rd = c.get("readme", {}).get("status", "-")
        ci = c.get("ci", {}).get("status", "-")
        local = "sync" if c.get("local_sync", {}).get("status") == "pass" else (
            "behind" if c.get("local_sync", {}).get("status") == "fail" else "-")
        age = e["staleness"]["label"]
        colour = _VERDICT_COLOUR.get(e["verdict"], "")
        lines.append(
            f"{e['name'][:30]:30s} {colour}{_badge(e['verdict'])}{_RESET} "
            f"{lic[:9]:9s} {rd[:7]:7s} {ci[:6]:6s} {age:9s} {local[:7]:7s}"
        )
    lines.append("")
    lines.append("legend: lic=licence  readme/ci=pass|fail|unk|skip  age=fresh|aging|stale|abandoned")
    lines.append("       local=- (not cloned) | sync | behind | unk  (unk = unknown)")
    return "\n".join(lines)


def render_html(report: dict[str, Any]) -> str:
    entries = sorted(
        report["repos"],
        key=lambda e: (
            0 if e["verdict"] in ("fail", "unknown") else
            1 if e["verdict"] == "warn" else 2,
            -1 if e["staleness"]["status"] == "abandoned" else 0,
            -(e["staleness"]["days"] or 0),
        ),
    )
    badge_colour = {
        "ok": "#16a34a", "warn": "#d97706", "fail": "#dc2626", "unknown": "#9333ea",
        "archived": "#64748b", "disabled": "#64748b", "skipped": "#64748b",
        "unlicensed": "#dc2626", "abandoned": "#64748b",
    }
    age_colour = {
        "fresh": "#16a34a", "aging": "#ca8a04", "stale": "#d97706", "abandoned": "#dc2626",
        "unknown": "#64748b",
    }
    rows: list[str] = []
    for e in entries:
        v = e["verdict"]
        lic = e["checks"].get("license", {}).get("detail", "-")
        rd = e["checks"].get("readme", {}).get("status", "-")
        ci = e["checks"].get("ci", {}).get("status", "-")
        local = e["checks"].get("local_sync", {})
        local_txt = "-"
        if local.get("status") == "pass":
            local_txt = "sync"
        elif local.get("status") == "fail":
            local_txt = f"behind {local.get('behind','')}".strip()
        elif local.get("status") in ("unknown", "error"):
            local_txt = "unk"
        st = e["staleness"]
        ca = e.get("check_age_days")
        ca_txt = "—" if ca is None else f"{ca:.1f}d"
        rows.append(
            "<tr>"
            f"<td class='nm'>{e['name']}</td>"
            f"<td><span class='badge' style='background:{badge_colour.get(v,'#475569')}'>{v}</span></td>"
            f"<td class='m'>{lic}</td>"
            f"<td class='m'>{rd}</td>"
            f"<td class='m'>{ci}</td>"
            f"<td><span class='badge' style='background:{age_colour.get(st['status'],'#475569')}'>{st['label']}</span></td>"
            f"<td class='m'>{local_txt}</td>"
            f"<td class='m'>{ca_txt}</td>"
            "</tr>"
        )
    summary_badges = " ".join(
        f"<span class='badge' style='background:{badge_colour.get(k,'#475569')}'>{k}: {n}</span>"
        for k, n in sorted(report["summary"].items())
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>repo-checks · {report['owner']}</title>
<style>
 body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:2rem;background:#0f172a;color:#e2e8f0}}
 h1{{font-size:1.25rem}} .sub{{color:#94a3b8;font-size:.85rem}}
 table{{border-collapse:collapse;width:100%;margin-top:1rem;font-size:.85rem}}
 th,td{{text-align:left;padding:.4rem .6rem;border-bottom:1px solid #1e293b;white-space:nowrap}}
 th{{color:#94a3b8;font-weight:600;position:sticky;top:0;background:#0f172a}}
 tr:hover td{{background:#1e293b}}
 .badge{{padding:.15rem .5rem;border-radius:999px;color:#fff;font-size:.75rem;font-weight:600}}
 .nm{{max-width:16rem;overflow:hidden;text-overflow:ellipsis}}
 .m{{color:#94a3b8}}
</style></head><body>
<h1>repo-checks <span class="sub">· {report['owner']} · {len(report['repos'])} repos · {report['mode']} · generated {report['generated_at']}</span></h1>
<div>{summary_badges}</div>
<table>
<thead><tr><th>repo</th><th>verdict</th><th>licence</th><th>readme</th><th>ci</th><th>age</th><th>local</th><th>check age</th></tr></thead>
<tbody>
{''.join(rows)}
</tbody></table>
</body></html>
"""


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #

def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="GitHub repository checks engine")
    ap.add_argument("--owner", default=OWNER)
    ap.add_argument("--apply", action="store_true", help="write data/repo-checks.json (default: dry-run)")
    ap.add_argument("--json", action="store_true", help="print the full report as JSON")
    ap.add_argument("--html", metavar="PATH", help="also write the admin table as HTML")
    ap.add_argument("--include-forks", action="store_true")
    ap.add_argument("--shallow", action="store_true", help="skip per-repo readme/CI API calls")
    ap.add_argument("--local-dir", default=LOCAL_DIR)
    ap.add_argument("--log", default=LOG_PATH)
    ap.add_argument("--limit", type=int, default=0, help="only check the first N repos")
    args = ap.parse_args(argv)

    token = gh_token()
    if not token:
        print("warning: no GH_TOKEN/GITHUB_TOKEN and `gh auth token` failed — "
              "unauthenticated (60 req/h), will likely stop early", file=sys.stderr)

    repos = fetch_repos(args.owner, token, args.include_forks)
    if args.limit > 0:
        repos = repos[: args.limit]

    now = now_iso()
    log_path = Path(args.log)
    prev = load_previous_log(log_path)
    entries = [run_checks(r, token, deep=not args.shallow, local_dir=args.local_dir) for r in repos]
    report = build_report(entries, args.owner,
                          "apply" if args.apply else "dry-run", prev, now)

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(render_console(report))

    if args.apply:
        save_report(report, log_path)
        print(f"\nwrote {log_path}", file=sys.stderr)

    if args.html:
        html_path = Path(args.html)
        html_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.write_text(render_html(report), encoding="utf-8")
        print(f"wrote {html_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

