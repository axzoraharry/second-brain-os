---
name: run
description: >-
  Work one session on a lead desk: process replies, qualify new leads, draft
  outreach, review the drafts and find more leads if the pipeline is thin,
  then report what is waiting for the owner. Use when the user says "run the
  desk", "work the pipeline", "find me leads", "draft outreach", or asks
  what the lead desk should do next. Do NOT use before setup has been run,
  or to approve or export (approve, export).
---

# Run a session

One session moves every item in the pipeline one step and stops at the
owner. The order matters: replies first, because a person who answered
should not receive another automated-looking message while their reply sits
unread.

## Workflow

1. **Check the desk is ready.** `brain/offer.md`, `brain/icp.md` and
   `sender_identity` in `desk.json` must be filled. If not, say what is
   missing and stop; do not draft against an empty offer.
2. **Read the state.** Run `python3 tools/pipeline.py status` and read
   `decisions.md` for answers the owner has given since last time. Apply
   them.
3. **Delegate in this order**, skipping a step with nothing to do. Use the
   plugin's agents where the harness supports subagents; otherwise do each
   step yourself, following that agent's file to the letter.
   1. `reply-handler` for unprocessed files in `inbox/`
   2. `qualifier` for leads with `status: new`
   3. `copywriter` for qualified leads with no current draft
   4. `compliance-reviewer` for drafts with `review: pending`, always in a
      separate context from the copywriter
   5. `prospector` only if fewer than 20 leads are `new` or `qualified`, or
      the user asked for leads; default 10 per session
4. **One repair round.** For drafts that failed review, have the copywriter
   fix the numbered defects once and the reviewer look again. A draft that
   fails twice is set to `rejected` with the reason, not retried.
5. **Gate.** Run `python3 tools/pipeline.py check`. Report any violation
   verbatim.
6. **Report** what was done with counts, what waits on the owner (open
   decisions, drafts with `review: pass` awaiting approval), and the check
   result. Suggest `approve` if drafts are waiting.

## Limits

- Never set `status: approved` or `approved_by`. Never export. Never send.
- Web research uses business sources only, and every lead records its
  source. If no web tool is available, say so and ask the owner for a list
  to work from instead of inventing companies.
- Stop after one pass. The pipeline moves again when the owner has answered.
