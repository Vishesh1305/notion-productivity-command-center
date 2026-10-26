# Shared AI behavior and schema guide

Use these instructions with both ChatGPT/Codex and Claude after each client has an authenticated, tested Notion read/write path. The connected client must report the exact page links it changed. A client that can only read should say so and route the request to the writable client.

## Boundaries

- Work within the Productivity Command Center pages and ten databases. Notion's authorization can expose other accessible pages, so check the target before every write.
- Read the current record, ID, and logical key before writing. Search by ID first, then by scoped key/name. If there are duplicates or an ambiguous write failure, stop and report the conflict; do not blindly retry.
- Clear routine single-record edits, including Plan date, Priority, Waiting reason, and a canonical Done action, may be applied on explicit request and then reported.
- Propose and wait for confirmation before daily Top 3, weekly priorities, monthly adjustments, commitments, real Due date changes, time blocks, ambiguous Inbox routing, broad edits, or Project/Goal closure.
- Keep Due date, Plan date, and Time block distinct. Never move a real deadline to make the schedule look tidy. Never write to Apple Calendar.
- A Task in Waiting needs a reason. Done sets Completed at; Cancelled sets Cancelled at. A direct status edit lacking a timestamp goes to Needs attention and is not counted in the weekly metric.
- A Phase is a child Project. At least one blocking Task and all blocking Tasks Done means Ready for review; only the user confirms Done. Do not invent ATLAS phases, success evidence, or a shipping criterion.
- Planning and reviews use `America/Vancouver`: Monday–Sunday weeks and separate Sunday/month-end logs. An unconfirmed proposal never appears as an adopted choice.
- When asked to refresh weekly plan follow-through, read the final confirmed Top 3 slots from each confirmed Daily Log in the Vancouver Monday–Sunday week. Count a slot only when its Task is Done and `Completed at` falls on that Vancouver day. Write the raw completed and confirmed counts to that week's Weekly Log; flag missing Tasks or completion timestamps in `Metric needs attention`. Read the current values before writing and report the resulting count. Never create a Daily Log merely to calculate this metric.
- On a stale Calendar mirror (over 30 minutes), say appointment context is incomplete before suggesting time blocks.
- Report completed changes, pending changes, ambiguities, and partial failures separately. Preserve capture originals, Notes, and historical Done/Cancelled records.
- Schema or layout requests use the versioned local definitions, visible dry-run, and controlled additive update. Daily record edits use the connected Notion client.

## Data map

Tasks owns all work, including Someday and recurrence occurrences. Projects includes phases as child Projects. Goals are flat. Areas is the life taxonomy. Notes stores durable writing. Capture Queue stores raw Inbox text. Habits defines cadence versions. Habit Check-ins stores dated Done/Excused/pause events. Planning Log stores one Daily/Weekly/Monthly entry per period key. Calendar Events is a private, managed display cache of title and time only.

Logical keys: Planning Log `(Period type, Period key)`; managed Task occurrence `(Series key, Occurrence date)`; Habit Check-in `(Habit ID, Occurrence date)`; Calendar Event `(Source calendar key, Source occurrence key)`. The Notion page ID is the durable record identity.

## Prompt examples

- “Quick add: ask a colleague about the prototype.” Save my exact text to Capture Queue now; leave routing for later.
- “Create a committed Task to review the portfolio on Thursday. Plan date is Thursday; there is no real Due date.”
- “Mark the portfolio review Done and record the completion time.”
- “Move the Plan date of the portfolio review to Friday. Leave its Due date alone.”
- “Process Inbox. Route clear items, preserve each original, and ask me about ambiguous ones.”
- “Plan my day. Propose at most three open Tasks using my current weekly priorities and calendar; wait for confirmation.”
- “Prepare the Sunday review for the closing week. Propose at most two priorities for next week; wait before confirming.”
- “Prepare the separate monthly review for this month; show Goal evidence, Area balance, Project movement, habits, and Someday.”
- “Refresh this week's plan follow-through from confirmed Top 3 choices and completion timestamps; show the raw count and any records needing attention.”
- “Show ATLAS and ask me for the phase names, Goal horizon/evidence, Definition of done, and shipping criterion before activating it.”

## Client capability check

For each of ChatGPT/Codex and Claude, test: read a command-center Area; create a disposable Capture Queue item with exact raw text; edit that item to Needs clarification; read it back; and move it to Processed. Record links and outcomes in the handoff inventory. Do this in an isolated test page first. Do not call either route usable until the client actually performs these writes.
