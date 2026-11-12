---
name: approve
description: >-
  Walk the owner through the lead desk's approval queue: open decisions,
  then each reviewed draft, recording approve, edit or reject for every one.
  Use when the user says "review drafts", "approve outreach", "what needs my
  decision", or after a run reports drafts waiting. Do NOT use to write or
  review drafts (run) or to export approved ones (export).
---

# Approve

This is the step where a person decides. The agents never take it. Your job
is to make each decision quick and honest: show the real message, the real
lead and anything the reviewer flagged, then record exactly what the owner
said.

## Workflow

1. **Decisions first.** Show each unticked line in `decisions.md`, one at a
   time, with the options. Tick it and write the owner's answer after an
   arrow. Do not answer for them.
2. **Then drafts** with `status: draft` and `review: pass`, grouped by
   segment so similar messages are judged together. For each, show: who the
   lead is and why they qualified (two lines), the channel, the subject and
   the full message.
3. **Record the owner's call**:
   - **Approve**: set `status: approved` and `approved_by:` to the owner's
     name as they gave it.
   - **Edit**: apply their wording, set `review: pending`, and leave it for
     the next review. An edited message is a new message.
   - **Reject**: set `status: rejected` and note the reason in the draft. If
     the reason is about the lead, set the lead to `rejected` too.
4. **Batch approval** is allowed only when the owner asks for it after
   seeing at least one full message from the batch, and only for drafts
   that differ by lead details. Say how many that covers before doing it.
5. **Finish** with `python3 tools/pipeline.py check` and the count approved,
   edited and rejected. Suggest `export` if anything was approved.

## Limits

- Approve nothing the owner has not seen or explicitly covered in a batch.
  "Looks good" about one draft is not approval of the rest.
- A draft with `review: fail` or `pending` cannot be approved. Show the
  defects instead.
- Reasons for rejection that would apply again go into
  `brain/learnings.md`.
