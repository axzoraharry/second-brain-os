# lead-gen

A lead generation desk for Claude Code. Six agents find business leads,
qualify them, draft email and WhatsApp outreach and handle replies. You
approve every message and send it yourself. A script enforces the rules the
agents are not allowed to bend.

```bash
claude plugin marketplace add axzoraharry/second-brain-os
claude plugin install lead-gen@second-brain-os
```

Then, in an empty folder:

```
/lead-gen:setup
```

## The loop

| Step | Invoke as | Who acts | What happens |
|---|---|---|---|
| 1 | `/lead-gen:setup` | you + agent | An interview fills in your offer, ideal customer, rules and sender identity. Once per business |
| 2 | `/lead-gen:run` | agents | Replies processed, new leads qualified, drafts written and reviewed, more leads found if the pipeline is thin |
| 3 | `/lead-gen:approve` | you | You answer the open questions and approve, edit or reject each draft |
| 4 | `/lead-gen:export` | you | Approved drafts become a CSV for your own sending tool, within the daily cap; you confirm what went out |
| 5 | `/lead-gen:reply` | you + agent | Paste a reply: it is classified, the lead updated, a response suggested, and anyone who says stop is suppressed for good |
| | `/lead-gen:call-prep` | agent | A one-page brief for a call you make yourself |

## The team

| Agent | Writes | Job |
|---|---|---|
| [`director`](agents/director.md) | nothing | Reads the pipeline, decides what the team does next, reports to you |
| [`prospector`](agents/prospector.md) | lead files | Finds leads from your lists and public business pages, source recorded |
| [`qualifier`](agents/qualifier.md) | score, status | Scores each lead against your profile, with evidence |
| [`copywriter`](agents/copywriter.md) | drafts | Writes messages from your offer and rules; raises a Pick when two versions are plausible |
| [`compliance-reviewer`](agents/compliance-reviewer.md) | review field | Checks every draft in a clean context; never rewrites |
| [`reply-handler`](agents/reply-handler.md) | lead history, suppression | Classifies replies and stops contact on request |

The writer and the reviewer are separate agents on purpose: a draft is judged
by something that did not write it. No agent can approve.

## The desk

Setup creates a folder of plain markdown you can read end to end:

```
brain/            offer, ideal customer profile, rules, learnings
leads/            one file per lead, with where it was found
outreach/drafts/  one file per message, with review and approval state
outreach/sent.md  the send log
inbox/            replies you paste in
decisions.md      questions waiting for you: Pick, Decide, Review
suppression.md    contacts never to be messaged again
desk.json         sender identity, daily cap, opt-out phrases
tools/pipeline.py the gate
```

## The gate

Prompts ask; [`pipeline.py`](skills/setup/template/tools/pipeline.py) refuses.
`export` will not produce a file while any approved draft:

- goes to a contact on the suppression list, on any channel
- goes to a lead marked rejected, closed or do-not-contact
- is a WhatsApp message to a lead without `whatsapp_opt_in: true`
- is an email with no subject or no opt-out line
- has not passed compliance review, or carries no approver's name
- belongs to a lead with no recorded source

It also stops at the daily cap, and `suppress` halts a contact's lead and all
their unsent drafts in one step. The script is dependency-free and covered by
[12 tests](tests/test_pipeline.py).

## What it does not do

- **It does not send.** No email, WhatsApp or SMS leaves the desk. You load
  the CSV into your own tool. Your accounts, your sending reputation and the
  last look stay with you.
- **It does not call.** There is no AI caller. `call-prep` briefs you for a
  call you make.
- **It does not know your law.** Rules on cold email, WhatsApp and
  telemarketing differ by country. Setup asks you to write yours into
  `brain/rules.md`; confirming them is your responsibility, and nothing here
  is legal advice.
- **It does not harvest personal data.** Business contacts from business
  sources, each with its source. No personal social accounts, no guessed
  addresses, no lists of unknown origin.

## How it maps to the course

| Course idea | Here |
|---|---|
| [Agents or workflows](../../docs/course-0-map/agents-or-workflows.md) | The session order is a fixed workflow; only the work inside each step is agentic |
| [The four places](../../docs/course-1-context/the-four-places.md) | `brain/` is shared context each agent reads first, kept small and owner-edited |
| [The four parts of a loop](../../docs/course-2-loop/the-four-parts.md) | Copywriter and reviewer form a worker and a checker, with one repair round |
| [Cheap decisions](../../docs/course-3-gate/cheap-decisions.md) | The hard rules are a script, not a model call |
| [The four rings](../../docs/course-4-harness/the-four-rings.md) | Read-only director, narrow write access per agent, a person on every outbound action |

The skills are plain `SKILL.md` files and the agents plain markdown, so they
also work copied into `.claude/skills/` and `.claude/agents/`.
