---
name: call-prep
description: >-
  Prepare a one-page brief for a sales call the owner will make themselves
  with a lead from the desk: who they are, what was said so far, questions
  to ask, likely objections and the next step. Use when the user says "prep
  me for the call with", "call brief", "what do I say to", or a lead moves
  to meeting. Do NOT use to place calls or to script an automated caller.
---

# Call brief

Calls are made by a person. This skill makes that person ready in two
minutes of reading.

## Workflow

1. **Gather.** Read the lead file and its history, every draft sent to them,
   their replies in `inbox/`, `brain/offer.md` and `brain/learnings.md`.
2. **Check they may be called.** If the lead is on `suppression.md` or
   `do-not-contact`, say so and stop. If the phone number has no source, or
   `brain/rules.md` lists a calling rule that applies (a do-not-call
   registry, permitted hours), put that at the top of the brief.
3. **Write `outreach/call-<lead>.md`**, one page:
   - **Who**: name, role, company, and the evidence they fit.
   - **So far**: what we sent, what they said, in dates.
   - **Goal of this call**: one outcome.
   - **Open with**: one sentence that is true and specific to them.
   - **Ask**: three to five questions, most important first.
   - **They may say**: likely objections, each with the honest answer from
     the offer, or "no good answer yet".
   - **Next step**: what to propose, and what to log afterwards.
4. **After the call**, if the owner reports back, add a dated line to the
   lead's history and update `status` (`meeting`, `closed`, or
   `do-not-contact` through the `suppress` command if they asked).

## Limits

- No invented facts about the lead or their company. Unknown is written as
  unknown.
- This skill does not dial, synthesise a voice or script an AI caller.
