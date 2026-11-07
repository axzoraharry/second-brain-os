#!/usr/bin/env python3
"""Tests for repo_checks.py — pure logic only, no network, no git mutation.

Run:  python3 -m unittest discover -s tests -v
      python3 tests/test_repo_checks.py
"""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import repo_checks as rc  # noqa: E402


def repo(**overrides):
    base = {
        "name": "sample",
        "full_name": "axzoraharry/sample",
        "owner": {"login": "axzoraharry"},
        "fork": False,
        "archived": False,
        "disabled": False,
        "private": False,
        "default_branch": "main",
        "language": "Python",
        "license": {"spdx_id": "MIT"},
        "pushed_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        "description": "a sample repo",
    }
    base.update(overrides)
    return base


class StalenessTests(unittest.TestCase):
    def test_boundaries(self):
        self.assertEqual(rc.staleness_status(0)[0], "fresh")
        self.assertEqual(rc.staleness_status(30)[0], "fresh")
        self.assertEqual(rc.staleness_status(31)[0], "aging")
        self.assertEqual(rc.staleness_status(90)[0], "aging")
        self.assertEqual(rc.staleness_status(91)[0], "stale")
        self.assertEqual(rc.staleness_status(365)[0], "stale")
        self.assertEqual(rc.staleness_status(366)[0], "abandoned")
        self.assertEqual(rc.staleness_status(None)[0], "unknown")

    def test_days_since(self):
        now = datetime(2026, 11, 7, tzinfo=timezone.utc)
        self.assertAlmostEqual(
            rc.days_since("2026-11-01T00:00:00Z", now=now), 6.0, places=1
        )
        self.assertIsNone(rc.days_since(None))


class VerdictTests(unittest.TestCase):
    """run_checks in shallow mode (deep=False) so readme/ci are skipped and no
    network is touched; local_dir points at a dir that does not exist."""

    LOCAL = "/nonexistent-repos"

    def test_ok(self):
        r = rc.run_checks(repo(), token=None, deep=False, local_dir=self.LOCAL)
        self.assertEqual(r["verdict"], "ok")
        self.assertEqual(r["checks"]["license"]["status"], "pass")
        self.assertEqual(r["checks"]["readme"]["status"], "skip")

    def test_unlicensed(self):
        r = rc.run_checks(repo(license=None), token=None, deep=False, local_dir=self.LOCAL)
        self.assertEqual(r["verdict"], "unlicensed")
        self.assertIn("license", r["fails"])
        self.assertEqual(r["checks"]["license"]["status"], "fail")

    def test_noassertion_is_unknown_not_fail(self):
        r = rc.run_checks(repo(license={"spdx_id": "NOASSERTION"}),
                          token=None, deep=False, local_dir=self.LOCAL)
        self.assertEqual(r["verdict"], "unknown")
        self.assertIn("license", r["unknowns"])
        self.assertEqual(r["checks"]["license"]["status"], "unknown")

    def test_abandoned_outranks_unlicensed(self):
        old = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat()
        r = rc.run_checks(repo(license=None, pushed_at=old),
                          token=None, deep=False, local_dir=self.LOCAL)
        self.assertEqual(r["verdict"], "abandoned")
        self.assertEqual(r["staleness"]["status"], "abandoned")

    def test_archived(self):
        r = rc.run_checks(repo(archived=True, license=None),
                          token=None, deep=False, local_dir=self.LOCAL)
        self.assertEqual(r["verdict"], "archived")

    def test_disabled(self):
        r = rc.run_checks(repo(disabled=True, license=None),
                          token=None, deep=False, local_dir=self.LOCAL)
        self.assertEqual(r["verdict"], "disabled")


class ReportTests(unittest.TestCase):
    def test_check_age_merge(self):
        now = "2026-11-07T12:00:00Z"
        entries = [
            {"full_name": "a/b", "verdict": "ok", "name": "b"},
        ]
        prev = {"a/b": "2026-11-05T12:00:00Z"}
        rep = rc.build_report(entries, "axzoraharry", "dry-run", prev, now)
        e = rep["repos"][0]
        self.assertEqual(e["checked_at"], now)
        self.assertEqual(e["previously_checked_at"], "2026-11-05T12:00:00Z")
        self.assertAlmostEqual(e["check_age_days"], 2.0, places=1)

    def test_html_renders_verdict(self):
        rep = {
            "owner": "axzoraharry", "mode": "dry-run", "generated_at": "x",
            "summary": {"ok": 1}, "repos": [
                rc.run_checks(repo(), token=None, deep=False, local_dir="/nonexistent")
            ],
        }
        html = rc.render_html(rep)
        self.assertIn("repo-checks", html)
        self.assertIn("ok: 1", html)
        self.assertIn("check age", html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
