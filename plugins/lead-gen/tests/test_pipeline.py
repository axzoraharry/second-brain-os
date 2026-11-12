"""Tests for the lead desk gate. No network; each test builds a desk in a temp dir."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "skills" / "setup" / "template" / "tools" / "pipeline.py"
spec = importlib.util.spec_from_file_location("pipeline", SRC)
pl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pl)

TODAY = "2026-11-12"


def lead(root, slug, **kw):
    f = {"name": "Asha Rao", "company": "Bright Dental", "email": f"{slug}@example.com",
         "phone": "+91 98765 43210", "whatsapp_opt_in": "false",
         "source": "https://example.com/team", "status": "qualified"}
    f.update(kw)
    (root / "leads" / f"{slug}.md").write_text(
        "---\n" + "\n".join(f"{k}: {v}" for k, v in f.items()) + "\n---\nnotes\n")


def draft(root, name, lead_slug, body="Hello.\n\nReply STOP to opt out.", **kw):
    f = {"lead": lead_slug, "channel": "email", "subject": "A quick idea",
         "status": "approved", "review": "pass", "approved_by": "owner"}
    f.update(kw)
    p = root / "outreach" / "drafts" / name
    p.write_text("---\n" + "\n".join(f"{k}: {v}" for k, v in f.items()) + "\n---\n" + body + "\n")
    return p


class Desk(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "leads").mkdir()
        (self.root / "outreach" / "drafts").mkdir(parents=True)
        (self.root / "desk.json").write_text(json.dumps(
            {"daily_cap": 2, "sender_identity": "Asha at Example Co"}))

    def tearDown(self):
        self.tmp.cleanup()

    def fails(self, needle):
        errs = pl.check(self.root)
        self.assertTrue(any(needle in e for e in errs), errs)

    def test_clean_desk_passes(self):
        lead(self.root, "a")
        draft(self.root, "a--email-1.md", "a")
        self.assertEqual(pl.check(self.root), [])

    def test_suppressed_contact_blocks(self):
        lead(self.root, "a")
        draft(self.root, "a--email-1.md", "a")
        (self.root / "suppression.md").write_text("- A@Example.com | 2026-11-01 | asked\n")
        self.fails("suppression list")

    def test_suppression_matches_phone_formats(self):
        lead(self.root, "a", phone="+91 98765 43210")
        draft(self.root, "a--email-1.md", "a")
        (self.root / "suppression.md").write_text("- 919876543210 | 2026-11-01 | asked\n")
        self.fails("suppression list")
        (self.root / "suppression.md").write_text("- 098765-43210 | 2026-11-01 | asked\n")
        self.fails("suppression list")  # no country code still matches

    def test_whatsapp_needs_opt_in(self):
        lead(self.root, "a")
        draft(self.root, "a--whatsapp-1.md", "a", channel="whatsapp")
        self.fails("whatsapp_opt_in")
        lead(self.root, "a", whatsapp_opt_in="true")
        self.assertEqual(pl.check(self.root), [])

    def test_email_needs_opt_out_line(self):
        lead(self.root, "a")
        draft(self.root, "a--email-1.md", "a", body="Hello, buy now.")
        self.fails("opt-out")

    def test_approval_needs_review_and_a_person(self):
        lead(self.root, "a")
        draft(self.root, "a--email-1.md", "a", review="pending", approved_by="")
        self.fails("compliance review")
        self.fails("approved_by")

    def test_lead_needs_source_and_sender_identity(self):
        lead(self.root, "a", source="")
        self.fails("no source")
        (self.root / "desk.json").write_text("{}")
        self.fails("sender_identity")

    def test_unapproved_drafts_are_not_gated(self):
        lead(self.root, "a")
        draft(self.root, "a--email-1.md", "a", status="draft", review="pending", body="x")
        self.assertEqual(pl.check(self.root), [])

    def test_export_refuses_on_violation(self):
        lead(self.root, "a", status="do-not-contact")
        draft(self.root, "a--email-1.md", "a")
        with self.assertRaises(SystemExit):
            pl.export(self.root, TODAY)
        self.assertFalse(list((self.root / "outreach").glob("export-*.csv")))

    def test_export_respects_daily_cap_then_mark_sent(self):
        for s in "abc":
            lead(self.root, s)
            draft(self.root, f"{s}--email-1.md", s)
        out, n, held = pl.export(self.root, TODAY)
        self.assertEqual((n, held), (2, 1))
        with out.open(newline="") as fh:
            self.assertEqual(len(list(pl.csv.reader(fh))), 3)  # header + 2
        _, n2, held2 = pl.export(self.root, TODAY)
        self.assertEqual((n2, held2), (0, 1))  # cap already used today
        self.assertEqual(pl.mark_sent(self.root, ["a--email-1.md"], TODAY), 1)
        self.assertEqual(pl.parse(self.root / "leads" / "a.md")[0]["status"], "contacted")
        self.assertEqual(pl.sent_today(self.root, TODAY), 1)
        with self.assertRaises(SystemExit):
            pl.mark_sent(self.root, ["c--email-1.md"], TODAY)  # never exported

    def test_suppress_stops_lead_and_its_drafts(self):
        lead(self.root, "a")
        p = draft(self.root, "a--email-1.md", "a")
        self.assertEqual(pl.suppress(self.root, "A@example.com", "unsubscribed", TODAY), ["a"])
        self.assertEqual(pl.parse(self.root / "leads" / "a.md")[0]["status"], "do-not-contact")
        self.assertEqual(pl.parse(p)[0]["status"], "rejected")
        pl.suppress(self.root, "a@example.com", "again", TODAY)
        self.assertEqual(len(pl.load_suppression(self.root)), 1)  # no duplicates

    def test_status_counts(self):
        lead(self.root, "a")
        lead(self.root, "b", status="new")
        draft(self.root, "a--email-1.md", "a")
        (self.root / "decisions.md").write_text("- [ ] pick\n- [x] done\n")
        s = pl.status(self.root)
        self.assertEqual((s["leads"]["qualified"], s["leads"]["new"]), (1, 1))
        self.assertEqual((s["drafts"]["approved"], s["open_decisions"]), (1, 1))


if __name__ == "__main__":
    unittest.main()
