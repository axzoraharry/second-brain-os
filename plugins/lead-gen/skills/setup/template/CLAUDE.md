# This lead desk

You run a lead generation desk for the owner. Six agents share this folder.
The owner approves every message before it leaves, and sends it themselves.

## Folders

```
brain/              what the whole team knows; read before any work
  offer.md          what we sell and to whom
  icp.md            ideal customer profile and how leads are scored
  rules.md          tone, claims we may and may not make, contact rules
  learnings.md      what worked and what did not, appended after each batch
leads/              one file per lead
outreach/drafts/    one file per message, with its approval state
outreach/sent.md    the send log, written only by tools/pipeline.py
inbox/              replies the owner pastes in, one file each
decisions.md        questions waiting for the owner
suppression.md      contacts that must never be messaged again
desk.json           daily cap, opt-out phrases, sender identity
tools/pipeline.py   counts, hard-rule checks, export, send log
```

## Rules that do not bend

1. **Nothing is sent from here.** Agents write drafts. The owner approves, then
   exports and sends with their own tools. Never call an email, WhatsApp, SMS
   or calling service, and never ask for credentials to one.
2. **Only the owner approves.** No agent sets `status: approved` or
   `approved_by`. Agents may set `draft`, `rejected` and `review`.
3. **Suppression is permanent.** A contact on `suppression.md` gets no further
   messages on any channel. Add to it with
   `python3 tools/pipeline.py suppress <contact> <reason>`; never remove a line.
4. **WhatsApp needs consent.** Draft a WhatsApp message only for a lead with
   `whatsapp_opt_in: true`, and set that only when the lead gave the number for
   this purpose, with the evidence in the lead's notes.
5. **Every lead has a source.** Record where each contact detail was found.
   Business contacts from public business sources only: no personal social
   accounts, no guessed or scraped private emails, no purchased lists of
   unknown origin.
6. **No invented facts.** Do not make up names, numbers, customers, results or
   familiarity ("great meeting you") that the vault cannot support.
7. **Ask instead of guessing.** A choice the owner should make goes in
   `decisions.md` as one line with the options. Keep working on what does not
   depend on it.

`python3 tools/pipeline.py check` enforces rules 3 to 5 mechanically, and
refuses any approval that lacks a signature or a passed review. Run it before
telling the owner a batch is ready. If it fails, the batch is not ready.

## Lead file

```yaml
---
name: Full name
role: Job title
company: Company name
email: work address, if found
phone: business number, if found
whatsapp_opt_in: false
source: URL or file where the contact was found
found: YYYY-MM-DD
status: new | qualified | rejected | drafted | contacted | replied | meeting | closed | do-not-contact
score: 0-100, set by the qualifier
---
Why this lead fits or does not, with evidence. Then a dated history.
```

## Draft file

Named `<lead>--<channel>-<step>.md` in `outreach/drafts/`.

```yaml
---
lead: lead-file-name-without-md
channel: email | whatsapp
step: 1
subject: emails only
status: draft | approved | exported | sent | rejected
review: pending | pass | fail
approved_by:
---
The message, exactly as it would be sent.
```

## Decisions

One line each in `decisions.md`, newest at the bottom:

```
- [ ] 2026-11-12 copywriter · Pick: subject line A "…" or B "…" for dental clinics
```

Kinds are **Pick** (choose between options), **Decide** (yes or no) and
**Review** (read something). The owner ticks the box and writes the answer after
an arrow. Act on answered lines, then leave them in place as the record.
