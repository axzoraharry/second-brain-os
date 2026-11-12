#!/usr/bin/env python3
"""Lead desk pipeline: counts, hard-rule checks, export and send log.

The agents write markdown; this script is the gate they cannot talk their way
past. It never sends anything. Dependency-free.

    python3 tools/pipeline.py status
    python3 tools/pipeline.py check
    python3 tools/pipeline.py export
    python3 tools/pipeline.py mark-sent <draft-file> [...]
    python3 tools/pipeline.py suppress <email-or-phone> <reason>
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import sys
from pathlib import Path

LEAD_STATUSES = ["new", "qualified", "rejected", "drafted", "contacted",
                 "replied", "meeting", "closed", "do-not-contact"]
DRAFT_STATUSES = ["draft", "approved", "exported", "sent", "rejected"]
CHANNELS = ["email", "whatsapp"]
DEFAULTS = {
    "daily_cap": 30,
    "opt_out_phrases": ["unsubscribe", "opt out", "reply stop"],
    "sender_identity": "",
}


def parse(path: Path) -> tuple[dict[str, str], str]:
    """Split a markdown file into flat `key: value` frontmatter and body."""
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m:
        return {}, text
    meta: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.lstrip().startswith("#"):
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip("\"'")
    return meta, m.group(2)


def set_field(path: Path, key: str, value: str) -> None:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m:
        raise ValueError(f"{path}: no frontmatter")
    lines, done = [], False
    for line in m.group(1).splitlines():
        if line.split(":", 1)[0].strip() == key:
            lines.append(f"{key}: {value}")
            done = True
        else:
            lines.append(line)
    if not done:
        lines.append(f"{key}: {value}")
    path.write_text("---\n" + "\n".join(lines) + "\n---\n" + m.group(2), encoding="utf-8")


def norm(contact: str) -> str:
    """Normalise an email or phone number so the same contact always matches."""
    c = contact.strip().lower()
    if "@" in c:
        return c
    digits = re.sub(r"\D", "", c)
    # compare on the last 10 digits so +91 98765 43210 and 098765 43210 match
    return digits[-10:] if len(digits) >= 10 else (digits or c)


def load_config(root: Path) -> dict:
    cfg = dict(DEFAULTS)
    f = root / "desk.json"
    if f.exists():
        cfg.update(json.loads(f.read_text(encoding="utf-8")))
    return cfg


def load_suppression(root: Path) -> set[str]:
    f = root / "suppression.md"
    out: set[str] = set()
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\s*[-*]\s+(\S+)", line)
            if m:
                out.add(norm(m.group(1)))
    return out


def load_leads(root: Path) -> dict[str, dict[str, str]]:
    return {p.stem: parse(p)[0] for p in sorted((root / "leads").glob("*.md"))
            if p.name != "README.md"}


def load_drafts(root: Path) -> list[tuple[Path, dict[str, str], str]]:
    return [(p, *parse(p)) for p in sorted((root / "outreach" / "drafts").glob("*.md"))
            if p.name != "README.md"]


def is_true(v: str | None) -> bool:
    return str(v).strip().lower() in ("true", "yes", "1")


def check(root: Path) -> list[str]:
    """Every rule here blocks an export. Returns one message per violation."""
    cfg, sup, leads = load_config(root), load_suppression(root), load_leads(root)
    errs: list[str] = []
    if not cfg["sender_identity"].strip():
        errs.append("desk.json: sender_identity is empty; say who the messages are from")
    for slug, lead in leads.items():
        if lead.get("status") not in LEAD_STATUSES:
            errs.append(f"leads/{slug}.md: status '{lead.get('status')}' is not one of {LEAD_STATUSES}")
        if not lead.get("source"):
            errs.append(f"leads/{slug}.md: no source; record where this contact was found")
    for path, d, body in load_drafts(root):
        name = f"outreach/drafts/{path.name}"
        st, ch = d.get("status"), d.get("channel")
        if st not in DRAFT_STATUSES:
            errs.append(f"{name}: status '{st}' is not one of {DRAFT_STATUSES}")
            continue
        if st != "approved":
            continue  # only what is about to leave the building is gated
        lead = leads.get(d.get("lead", ""))
        if lead is None:
            errs.append(f"{name}: lead '{d.get('lead')}' has no file in leads/")
            continue
        if ch not in CHANNELS:
            errs.append(f"{name}: channel '{ch}' is not one of {CHANNELS}")
            continue
        if not d.get("approved_by"):
            errs.append(f"{name}: approved without approved_by; a person has to sign each approval")
        if d.get("review") != "pass":
            errs.append(f"{name}: approved but compliance review is '{d.get('review', 'missing')}', not 'pass'")
        if lead.get("status") in ("do-not-contact", "rejected", "closed"):
            errs.append(f"{name}: lead status is '{lead.get('status')}'")
        contact = lead.get("email") if ch == "email" else lead.get("phone")
        if not contact:
            errs.append(f"{name}: lead has no {'email' if ch == 'email' else 'phone'} for channel {ch}")
        for c in (lead.get("email"), lead.get("phone")):
            if c and norm(c) in sup:
                errs.append(f"{name}: {c} is on the suppression list")
        if ch == "whatsapp" and not is_true(lead.get("whatsapp_opt_in")):
            errs.append(f"{name}: WhatsApp needs whatsapp_opt_in: true on the lead")
        if ch == "email":
            if not d.get("subject"):
                errs.append(f"{name}: email has no subject")
            low = body.lower()
            if not any(p.lower() in low for p in cfg["opt_out_phrases"]):
                errs.append(f"{name}: email has no opt-out line ({', '.join(cfg['opt_out_phrases'])})")
        if not body.strip():
            errs.append(f"{name}: empty body")
    return errs


def status(root: Path) -> dict:
    leads, drafts = load_leads(root), load_drafts(root)
    lc = {s: 0 for s in LEAD_STATUSES}
    for l in leads.values():
        lc[l.get("status", "?")] = lc.get(l.get("status", "?"), 0) + 1
    dc = {s: 0 for s in DRAFT_STATUSES}
    for _, d, _ in drafts:
        dc[d.get("status", "?")] = dc.get(d.get("status", "?"), 0) + 1
    dec = root / "decisions.md"
    open_dec = len(re.findall(r"^- \[ \]", dec.read_text(encoding="utf-8"), re.M)) if dec.exists() else 0
    return {"leads": lc, "drafts": dc, "suppressed": len(load_suppression(root)),
            "open_decisions": open_dec}


def sent_today(root: Path, today: str) -> int:
    f = root / "outreach" / "sent.md"
    if not f.exists():
        return 0
    return sum(1 for line in f.read_text(encoding="utf-8").splitlines()
               if line.startswith(f"- {today} "))


def export(root: Path, today: str) -> tuple[Path | None, int, int]:
    """Write approved drafts to a CSV for the owner's own sending tool.

    Returns (file, exported, held_back_by_cap). Refuses if check() fails.
    """
    errs = check(root)
    if errs:
        raise SystemExit("export refused, fix these first:\n  " + "\n  ".join(errs))
    cfg, leads = load_config(root), load_leads(root)
    approved = [(p, d, b) for p, d, b in load_drafts(root) if d.get("status") == "approved"]
    exported_today = sum(1 for _, d, _ in load_drafts(root)
                         if d.get("status") in ("exported", "sent") and d.get("exported") == today)
    room = max(0, int(cfg["daily_cap"]) - max(exported_today, sent_today(root, today)))
    batch, held = approved[:room], len(approved) - min(room, len(approved))
    if not batch:
        return None, 0, held
    out = root / "outreach" / f"export-{today}.csv"
    new = not out.exists()
    with out.open("a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["draft", "lead", "name", "company", "channel", "to", "subject", "body"])
        for p, d, b in batch:
            lead = leads[d["lead"]]
            to = lead.get("email") if d["channel"] == "email" else lead.get("phone")
            w.writerow([p.name, d["lead"], lead.get("name", ""), lead.get("company", ""),
                        d["channel"], to, d.get("subject", ""), b.strip()])
            set_field(p, "status", "exported")
            set_field(p, "exported", today)
    return out, len(batch), held


def mark_sent(root: Path, names: list[str], today: str) -> int:
    log = root / "outreach" / "sent.md"
    if not log.exists():
        log.write_text("# Sent log\n\n", encoding="utf-8")
    n = 0
    for name in names:
        p = root / "outreach" / "drafts" / Path(name).name
        if not p.exists():
            raise SystemExit(f"no such draft: {name}")
        d, _ = parse(p)
        if d.get("status") != "exported":
            raise SystemExit(f"{p.name}: status is '{d.get('status')}'; only exported drafts can be marked sent")
        set_field(p, "status", "sent")
        set_field(p, "sent", today)
        with log.open("a", encoding="utf-8") as fh:
            fh.write(f"- {today} {d.get('channel')} {d.get('lead')} ({p.name})\n")
        lead = root / "leads" / f"{d.get('lead')}.md"
        if lead.exists() and parse(lead)[0].get("status") in ("new", "qualified", "drafted"):
            set_field(lead, "status", "contacted")
        n += 1
    return n


def suppress(root: Path, contact: str, reason: str, today: str) -> list[str]:
    """Add a contact to the suppression list and stop every lead it belongs to."""
    f = root / "suppression.md"
    if not f.exists():
        f.write_text("# Suppression list\n\n", encoding="utf-8")
    key = norm(contact)
    if key not in load_suppression(root):
        with f.open("a", encoding="utf-8") as fh:
            fh.write(f"- {key} | {today} | {reason}\n")
    stopped = []
    for p in sorted((root / "leads").glob("*.md")):
        m, _ = parse(p)
        if key in {norm(c) for c in (m.get("email"), m.get("phone")) if c}:
            set_field(p, "status", "do-not-contact")
            stopped.append(p.stem)
    for p, d, _ in load_drafts(root):
        if d.get("lead") in stopped and d.get("status") in ("draft", "approved", "exported"):
            set_field(p, "status", "rejected")
    return stopped


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".", help="the lead desk folder (default: current)")
    ap.add_argument("--today", default=dt.date.today().isoformat(), help=argparse.SUPPRESS)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status").add_argument("--json", action="store_true")
    sub.add_parser("check")
    sub.add_parser("export")
    sub.add_parser("mark-sent").add_argument("drafts", nargs="+")
    sp = sub.add_parser("suppress")
    sp.add_argument("contact")
    sp.add_argument("reason")
    a = ap.parse_args(argv)
    root = Path(a.root)
    if not (root / "leads").is_dir():
        raise SystemExit(f"{root} is not a lead desk (no leads/ folder). Run the setup skill first.")

    if a.cmd == "status":
        s = status(root)
        if a.json:
            print(json.dumps(s, indent=2))
        else:
            for label, counts in (("leads ", s["leads"]), ("drafts", s["drafts"])):
                print(label, " ".join(f"{k} {v}" for k, v in counts.items() if v) or "none")
            print(f"suppressed {s['suppressed']}  open decisions {s['open_decisions']}")
    elif a.cmd == "check":
        errs = check(root)
        for e in errs:
            print("FAIL", e)
        print(f"{len(errs)} violation(s)" if errs else "ok: nothing approved breaks a rule")
        return 1 if errs else 0
    elif a.cmd == "export":
        out, n, held = export(root, a.today)
        print(f"exported {n} to {out}" if n else "nothing exported")
        if held:
            print(f"{held} approved draft(s) held back by the daily cap")
    elif a.cmd == "mark-sent":
        print(f"marked {mark_sent(root, a.drafts, a.today)} sent")
    elif a.cmd == "suppress":
        stopped = suppress(root, a.contact, a.reason, a.today)
        print(f"suppressed {norm(a.contact)}; leads stopped: {', '.join(stopped) or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
