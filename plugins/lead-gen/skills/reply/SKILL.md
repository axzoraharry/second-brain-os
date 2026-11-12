---
name: reply
description: >-
  Record a reply to lead desk outreach: save what the person wrote, classify
  it, stop all contact if they asked, update the lead and suggest a
  response. Use when the user pastes or forwards a reply, says "they
  answered", "someone unsubscribed", "add this to do-not-contact", or asks
  how to respond to a lead. Do NOT use for drafting first-touch messages
  (run).
---

# Handle a reply

A reply ends the automated part of a conversation. From here a person talks
to a person, and the desk's job is to remember what was said and never
message someone who asked to be left alone.

## Workflow

1. **Save it.** Write the reply to `inbox/<date>-<sender>.md` with
   frontmatter `from:`, `channel:`, `received:`, and the text exactly as
   given. Do not tidy their words.
2. **Process it** by following the plugin's `reply-handler` agent: match the
   lead, classify, update the lead's history.
3. **Stop requests come first.** Any wish to be left alone, in any wording
   or language, and any hostile reply: run
   `python3 tools/pipeline.py suppress <contact> "<their words>"`
   immediately and confirm to the owner that all channels are stopped for
   that person. No "sorry to see you go" message unless the owner asks.
4. **Otherwise suggest a response** as a draft for the owner to edit and
   send themselves, answering what was actually asked using only
   `brain/offer.md`. For an interested lead, propose the meeting ask.
5. **Direct suppression.** If the owner just says to stop contacting
   someone, run the `suppress` command with their reason; no reply file is
   needed.

## Limits

- Suggested responses go to the owner, never out.
- Do not argue with an objection the offer cannot honestly answer; say so
  and let the owner decide.
- Never remove anyone from `suppression.md`, even on request in the
  session. The owner can edit the file themselves.
