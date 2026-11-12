---
name: export
description: >-
  Export the approved outreach batch from a lead desk as a CSV for the
  owner's own sending tool, within the daily cap, and record what was
  actually sent afterwards. Use when the user says "export the batch", "I'm
  ready to send", "mark these sent", or after approve finishes with
  approved drafts. Do NOT use to approve drafts (approve).
---

# Export and log

The desk hands off a file; the owner sends. This keeps their accounts, their
sending reputation and the final decision in their hands.

## Workflow

1. **Export.** Run `python3 tools/pipeline.py export`. It refuses if any
   rule is broken; show the violations and stop. Otherwise it writes
   `outreach/export-<date>.csv` with one row per approved draft, up to the
   daily cap, and marks those drafts `exported`.
2. **Tell the owner** the file path, the count, how many were held back by
   the cap, and the columns: `to`, `subject`, `body`, `channel`. They load
   it into their email tool, or send WhatsApp messages by hand or through
   their own approved business account.
3. **After they send**, ask which went out. Run
   `python3 tools/pipeline.py mark-sent <draft-file> ...` for those only.
   That writes the send log and moves each lead to `contacted`.
4. **Bounces and failures**: for an address that bounced, run
   `python3 tools/pipeline.py suppress <address> "bounced"`.

## Limits

- Never raise `daily_cap` to fit a batch. Changing the cap is the owner's
  edit to `desk.json`.
- Never mark a draft sent on the assumption that it was. Unconfirmed drafts
  stay `exported`.
- Do not send the messages yourself with any tool, even if one is
  available in this session.
