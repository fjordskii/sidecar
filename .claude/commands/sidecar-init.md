---
description: Run the Sidecar setup interview and configure this trading loop
---

Configure this repo as the user's trading loop.

Read `INTERVIEW.md` and follow it exactly. It is a conversation, not a form — one topic at a time,
push once on vague answers, reflect back what you heard after each section.

Produce every output listed there: `PROFILE.md` (their answers, in their words), a fully filled-in
`LOOP_PROMPT.md`, a seeded `JOURNAL.md`, filled-in `ops/` files, and — printed in the chat as one
copy-pasteable block — their scheduler prompt with all placeholders resolved, plus the routine config
checklist.

Do not trade, do not run a cycle, and do not touch anything else in the repo during setup.

If the repo is **already** initialized (`PROFILE.md` exists and `LOOP_PROMPT.md` has no `{{` tokens),
don't start over. Say so, summarize the current mandate in a few lines, and ask whether they want to
amend it instead — amendments are edits to `LOOP_PROMPT.md`, dated inline, with superseded reasoning
left visible.
