---
name: setup
description: >-
  Create a lead desk: the shared folder a team of lead generation agents
  works in, with the offer, ideal customer profile, outreach rules,
  suppression list and the pipeline script. Use when the user wants to set up
  lead generation or outreach agents, start a lead desk, or says "set up
  lead gen". Run once per business. Do NOT use to run a working session on an
  existing desk (run) or to approve drafts (approve).
---

# Set up a lead desk

The desk is a folder of plain markdown that six agents share and the owner
can read end to end. Nothing in it sends messages: the agents draft, the
owner approves and sends. Setup is mostly an interview, because agents that
start without a clear offer and customer profile produce confident spam.

## Workflow

1. **Pick the folder.** Use the current directory if it is empty or the user
   says so; otherwise ask where. Refuse to set up inside a folder that
   already has `leads/` and `desk.json`; that desk exists.
2. **Copy the template.** Copy everything inside the `template/` folder next
   to this file into the desk folder, keeping the structure, including
   `tools/pipeline.py` and the empty `leads/`, `inbox/` and
   `outreach/drafts/` folders.
3. **Interview the owner**, one topic at a time, and write the answers in
   their words:
   - `brain/offer.md`: what they sell, to whom, the problem, proof they can
     cite truthfully and where it comes from, the ask.
   - `brain/icp.md`: industry, size, region, roles, fit signals,
     disqualifiers. Adjust the scoring table only if they ask.
   - `desk.json`: `sender_identity` (the name and business every message is
     from) and `daily_cap`. Keep the default cap of 30 unless they choose
     another; suggest starting lower for a new sending domain.
   - `brain/rules.md`: tone edits, and under **Law** the rules for their
     country and channels. Say plainly that you cannot give legal advice and
     that the rules on cold email, WhatsApp and calls are theirs to confirm.
4. **Do not invent answers.** A field the owner skipped stays empty with a
   line in `decisions.md` asking for it. Proof points especially: leave the
   list empty rather than fill it with plausible numbers.
5. **Verify.** Run `python3 tools/pipeline.py status` and
   `python3 tools/pipeline.py check` in the desk folder. Both must run.
6. **Tell the owner the loop**: `run` to work a session, `approve` to go
   through drafts, `export` to get the approved batch for sending, `reply`
   when someone answers.

## What this desk will not do

It does not send email or WhatsApp messages and does not place calls. That
is deliberate: sending needs the owner's own accounts and their judgement on
each message. If asked to wire in a sending or calling service, explain this
and offer the CSV from `export` as the handoff to whatever tool they use.
