# Notion Productivity Command Center — working specification

Status: pre-production specification complete, 2026-09-29. This is the product and technical specification; the user subsequently ordered the separate [Codex implementation prompt](codex-implementation-prompt.md). The [decision register](decision-register.md) records approved choices, resolved conflicts, and technical gates. No material product decision remains open.

## 1. Purpose and operating rules

The command center is the first place to understand today's work, upcoming commitments, and how activity contributes to weekly priorities, projects, goals, and life areas. A routine daily visit should take 5–10 minutes. Planning is optional. Natural-language requests to a connected AI client should handle most creation and changes, while direct Notion controls remain usable.

Three layers must stay separate: (1) stable records and relationships, (2) views and workflows, (3) presentation. Redesigning Home must never require rebuilding or copying the data. Never silently delete or overwrite user-created information, move real deadlines, or close Projects/Goals based only on counts.

## 2. Page architecture

| Destination | Role |
| --- | --- |
| Home / Command Center | First-stop overview and quick capture. |
| Tasks | All Tasks, Today, Upcoming deadlines, Waiting, Backlog, Someday, Completed, and recurring-task management views. |
| Projects | Active, Planned, Paused, Completed, and ATLAS/phase views. |
| Goals & Areas | Active Goals, review horizons, and Area pages/views. |
| Notes | Recent notes and unfiled notes; Brain Dump can start here or in Capture Queue. |
| Habits & Reviews | Habit definitions, check-ins, daily/weekly/monthly Planning Logs. |
| Inbox | Full unprocessed Capture Queue; linked directly from Home. |
| Start Here | Short usage guide, direct/manual paths, AI prompt examples, and maintenance links. |

Home order is fixed: (1) **Daily Top 3**, (2) **Calendar**, (3) **up to two weekly priorities**, then (4) **Inbox with a prominent Quick Add**, (5) **Active Projects**, (6) **weekly plan follow-through**. Keep each section short and provide a link to its full view. Focus opens from a Task and shows one task, its project/goal context, next action/checklist, due date, time block if any, and simple Done/Waiting/quick-capture/navigation actions. A capture made during Focus goes to the Inbox without changing the active Task.

The Home Calendar section must show actual appointments. Use a compact upcoming agenda from a managed, private Calendar Events mirror, a short Task Plan date/Due date view, a last-sync timestamp, and a prominent link to full live Notion Calendar. The mirror shows only title, start/end time, and all-day state; it excludes notes, attendee lists, and invite details. The custom Notion page cannot natively display live Notion Calendar events [according to Notion](https://www.notion.com/en-gb/help/use-notion-calendar-with-notion). Do not use a public calendar embed to expose private appointments.

## 3. Data architecture and schemas

Use nine central databases: seven baseline databases (Tasks, Projects, Goals, Areas, Notes, Habits, Planning Log) plus Capture Queue and Habit Check-ins. Add one **managed display cache**, Calendar Events, solely because the user requires real Apple Calendar appointments on the custom Home page and Notion cannot display that live feed there. Calendar Events is read-only from the user's perspective and is not a Task, appointment source of truth, or historical productivity database. A view is not a new database. Avoid duplicate per-area or per-timeframe task stores.

### Tasks

| Property | Meaning |
| --- | --- |
| Title | Only unconditional input required at quick creation. |
| Status | To do, In progress, Waiting, Done, Cancelled. Default To do. |
| Commitment | Committed or Someday; default Committed for explicit tasks, while ambiguous captures remain in Capture Queue. |
| Priority | High, Normal, Low; default Normal. This is enduring importance, distinct from daily Top 3. |
| Due date | Real deadline, optional. |
| Plan date | Flexible intended workday, optional. |
| Time block | Optional start/end interval, only after user confirmation. |
| Project | At most one owning Project, optional. |
| Area | Derived from Project when linked; for standalone Tasks, optional direct Area. Validate against contradictory manual overrides. |
| Parent Task / Child Tasks | Self relation for independently tracked subtasks. Tiny steps stay as an in-page checklist. |
| Blocked by | Optional self relation for meaningful dependencies; no automatic date shifts. |
| Waiting reason / Follow-up date | Reason conditionally required for Waiting; follow-up optional. |
| Non-blocking for phase | Checkbox, default false. Phase Tasks block completion unless explicitly marked non-blocking. |
| Recurrence series / Occurrence key | For repeatable Task instances; stable series+occurrence-date key when a managed recurrence engine is used. |
| Completed at / Cancelled at / Change note | Preserve lifecycle and significant replanning history. |

Task views and sort rules: **Today** = committed, not Done/Cancelled, Plan date today plus overdue Plan dates shown in a separate attention group; Top 3 is taken from confirmed Planning Log slots, not from Priority. **Upcoming deadlines** = open committed Tasks with Due date in the next 14 days, sorted soonest first, with overdue at top. **Waiting** = Waiting Tasks sorted by Follow-up date then oldest unresolved; no-date Waiting still appears in Sunday review. **Backlog** = committed To do with no Plan date, with due-soon tasks surfaced. **Someday** = uncommitted, excluded from daily proposals and revisited monthly. **All/Completed** provide full history and search. Filter Cancelled from routine views; preserve it in history.

Terminology shown in Start Here: **urgent** means a real Due date is near or missed; **Priority** means enduring importance; **Top 3** means the Tasks chosen for a specific day. An urgent Task may enter the Top 3, but the labels do different jobs and must not be merged into one property.

Task transitions: the canonical Done button or AI action sets Status and Completed at together; Cancelled records cancellation time/reason where known. On the user's Education Plus plan, test a small native database automation that stamps Completed at or Cancelled at when Status is changed directly. If that action is unavailable or fails, a direct manual status edit without its timestamp is flagged for correction before the time-sensitive Home metric counts it. Deferring changes Plan date but leaves Due date untouched unless the actual deadline changes. Waiting must have a reason. Returning from Waiting retains the prior reason in a status/change note before clearing active Waiting fields. Explicit AI single-record edits may execute and report; changes to deadlines and commitments require confirmation.

### Projects

Fields: Title; Status (Planned, Active, Paused, Done, Cancelled); primary Area; optional Goal; optional parent Project and child Projects; Definition of done; optional Target date; optional description and completion note/date. Primary Area is required before Active, and Definition of done must be clear before Active. A phase is a child Project within this same database. No separate Phases database.

A phase's **ready for review** signal appears when all of its blocking Tasks are Done. A Cancelled blocking Task does not count as Done until the user explicitly marks it non-blocking or replaces it. Zero blocking Tasks does not imply readiness. The user confirms Done, including for phases and parent Projects. ATLAS is not automatically shipped merely because all Task boxes are checked; its final Definition of done must include an explicit shipping criterion.

Project views: Active, Planned, Paused, Completed, and parent/phase hierarchy. Home shows a short Active list with nearest target date and next open gate or milestone where available. Children inherit the parent's Goal and Area by default for display and validation, but the explicit relation is retained for stable reporting.

### Goals and Areas

Goals are flat. Fields: Title; Status (Planned, Active, Paused, Achieved, Dropped); one primary Area; optional description; review horizon/date; observable success or progress evidence; linked contributing Projects; last review note/date. An Active Goal requires a horizon and evidence definition; qualitative evidence is valid. Only user confirmation sets Achieved. Review monthly and by its horizon.

Areas fields: Name; short Purpose; Active/Archived state. Seed Tech Career, Education, Health, Finances, Relationships, Home & Life Admin, and Recreation. Use views to summarize Goals/Projects/Tasks by Area rather than duplicating records. Area taxonomy can change without migrating core records.

### Notes and Capture Queue

Notes fields: Title, body, created/updated time, optional Area/Goal/Project links, optional source capture. No filing required to save. Brain Dump may create a Note directly or start as raw capture. Converting a Note to a Task preserves the Note and requires an explicit request or confirmation of an AI suggestion.

Capture Queue fields: Original text, Captured at, Status (New, Needs clarification, Processed), optional clarification question, optional links to resulting records, Processed at. Quick Add saves raw text here immediately. The Inbox view shows New and Needs clarification and retains processed originals out of view. "Process Inbox" runs only when requested; clear items are routed in a batch, ambiguous ones stay visible. A direct unambiguous AI request can create structured records without visiting Capture Queue.

### Habits and Habit Check-ins

Habits fields: Name, primary Area, cadence (daily, selected weekdays, or N times per week), status (Active, Paused, Archived), optional start/end date, optional numeric target/unit. Default is binary. Do not generate recurring Tasks for habits.

Habit Check-ins fields: Habit relation, occurrence date/week key, Status (Done, Excused), optional amount/unit and note, stable Habit+occurrence identity, recorded time. Check-ins are separate from Planning Log so skipped daily planning never erases habit history. Consistency is completed eligible opportunities over a recent period; paused time and Excused opportunities are excluded. Avoid streak pressure and composite scores.

The same check-in history may hold explicit Pause started and Pause ended events, so past paused intervals remain reconstructable when a Habit is resumed. A missing active-day check-in is simply missed; the system need not precreate empty occurrence pages. A cadence change creates a new Habit definition version linked to the prior one, with the old version archived, so historical opportunities are not recalculated under a new cadence. For an N-times-per-week Habit, the eligible weekly target is prorated by active days and rounded up; Excused occurrences reduce that eligible target, and completed occurrences are capped at the eligible target for consistency. The monthly review can compute the trend from these event records rather than requiring a fragile live formula.

### Planning Log

One record per (Period type, Period key), where type is Daily/Weekly/Monthly and key uses the planning timezone. Fields include period start/end, Draft/Confirmed state, proposed and confirmed choices, summary, review notes, change note, and timestamps. Daily Top 3 uses three ordered Task slots for proposed choices and three ordered slots for confirmed choices, with no duplicate Task in one day. Weekly priorities use two ordered text slots with optional Goal/Project links. Daily records relate to their corresponding Weekly record so Notion formulas/rollups can compute the current-week metric. The Weekly record is created on first confirmed daily plan in that week if it does not yet exist, even if Sunday's review has not happened. The same log holds the plan and later review. Monthly adjustments are written as proposals and only committed after user confirmation. Repeated AI requests update the existing record; separate weekly and monthly records may both exist on a last-day Sunday. A missed review is generated/opened on demand, not as overdue review Tasks.

## 4. Workflows

**Morning:** Home shows confirmed choices if present. The user can simply scan or request "Plan my day." On request, AI considers open committed Tasks, real Due dates, recent unfinished Top 3, active Projects, up to two weekly priorities, Waiting and calendar availability where connected. It proposes up to three Tasks; the user confirms. It does not silently roll over unfinished Tasks. Confirmed choices appear on Home. Intraday replanning is explicit and preserves a short reason/change note.

**During work:** Mark Task In progress/Done, use one-task Focus, or Quick Add raw input. AI can perform clear routine updates on request and report links to affected records. Dependencies and blocked work are visible, but do not cause automatic rescheduling. Time blocks are suggested selectively and confirmed before creation.

**Evening:** Optional brief review; on request AI summarizes Top 3 outcomes and unresolved work from structured records, with optional reflection. A manual review page remains accessible. No mandatory daily log is created by merely opening Home.

**Sunday:** The review is due as a ritual, but AI preparation begins when the user opens or requests it; no unattended background AI run is required. AI prepares a weekly summary covering prior priorities, project movement, Waiting/Inbox, upcoming calendar, and proposed next priorities (maximum two). It writes the review to the closing week's Weekly Log and the confirmed next priorities to the following week's Weekly Log, creating that record if needed. Weekly review can be opened later if missed. The same on-request rule applies to the last-day monthly review.

**Last calendar day:** Separate monthly review, even if it is Sunday. AI summarizes Goal evidence, Area balance, project trajectory, habit trend, and Someday candidates, then proposes adjustments for confirmation. Goals/Projects are never auto-declared complete.

## 5. Calendar and dates

Appointment source of truth: Apple Calendar as used on the user's Mac, with underlying accounts mixed or uncertain. Work source of truth: Notion Tasks. Notion Calendar can connect Apple/iCloud calendars and show Notion date records as a combined live viewing surface [per Notion](https://www.notion.com/en-gb/help/manage-your-calendars-and-events), [database dates](https://www.notion.com/en-gb/help/use-notion-calendar-with-notion). Do not create editable appointment copies as Tasks or mutate Apple Calendar events to resolve work conflicts. Task Due date, Plan date, and confirmed Time block remain distinct. A conflict produces a warning/suggestion, not silent movement. `America/Vancouver` defines day boundaries, Monday–Sunday weeks, month-end reviews, and daylight saving transitions.

To satisfy the custom Home requirement, a local Mac sync reads explicitly selected calendars already available to Apple Calendar and upserts a small, read-only Calendar Events display cache in Notion. Use the macOS EventKit access route or another private local API with explicit user permission; EventKit requires full calendar permission to read events even though this integration's own operations must be read-only [per Apple](https://developer.apple.com/documentation/eventkit/accessing-the-event-store). Do not require a public calendar URL or save an Apple password in the repo. Sync from yesterday through the next 14 days at Mac login and every 15 minutes while awake; show the next seven days on Home. Keep a stable source/occurrence identity; update rescheduled events; mark disappeared, cancelled, or expired mirror items inactive without changing Apple Calendar. Only mark missing events inactive after a complete successful fetch, never after a failed/partial sync. Offer an on-demand local refresh path if practical. Home shows the last successful sync time, marks the summary stale after 30 minutes, and links to live Notion Calendar when the Mac is off or sync is stale. Calendar inclusion is selected explicitly during setup; holiday/birthday subscriptions are not included automatically. The mirror contains only title, start/end time, all-day state, and internal sync metadata; it never copies attendees, descriptions, invite links, or location. AI planning must treat a stale mirror as incomplete calendar context and say so before recommending time blocks.

## 6. Metrics

Home Progress Metric = **weekly plan follow-through**, shown as `completed on planned day / confirmed daily Top 3 slots` for the current Monday–Sunday week. Exclude days without a confirmed daily plan. Use the final confirmed Top 3 after an explicit replan, retaining the change note. Count a slot only if its Task was marked Done by the end of that local planning day. If an unfinished Task is selected again on a later day, each confirmed day is a separate planned slot; completion counts only for the day when it happened. Show raw counts, not only a percentage. This describes adherence to a chosen plan, not overall productivity.

Deeper views may show gate Tasks completed/remaining, phase ready-for-review signal, evidence notes for Goals, recent Habit consistency, and Inbox/Waiting counts. Computed counts never close a Goal or Project. Favor simple formulas/rollups for local properties and a validated aggregation step only where cross-record logic cannot be expressed reliably in Notion.

## 7. AI, buttons, templates, and recurrence

Primary AI entry is both ChatGPT/Codex and Claude, each connected to the user's Notion workspace through its supported integration. Maintain one shared plain-language behavior guide and schema map so the clients apply the same rules. AI use cases: create/edit records, process Inbox, propose daily Top 3, prepare reviews, suggest time blocks, and explain the current system. For explicit routine single-record changes, including Plan date or permanent Priority, apply then report. For daily/weekly/monthly choices, Committed/Someday changes, real Due date changes, ambiguous routing, Project/Goal closure, or broad edits, show the proposed scope and obtain confirmation before applying. After a write, report records changed and links; after partial failure, distinguish completed from pending changes. Each client must pass a live read/write capability check before its action route is marked available; a chat product without writable Notion access must route through the supported coding client instead of claiming it made the change. Notion documents hosted MCP connections for Codex and Claude Code [here](https://developers.notion.com/guides/mcp/get-started-with-mcp). Its authorization can access content the user can access in the selected workspace, so instructions to stay within command-center pages are a behavioral boundary, not a technical permission boundary. At setup, prefer a dedicated private workspace or inspect the selected workspace's accessible content before authorizing either client.

For natural-language **layout or schema** changes, an AI coding client should update the versioned specification/configuration, show a structural dry-run, and apply an additive update after review. Ordinary record-edit prompts use the connected Notion workspace directly. This separates easy daily editing from controlled system changes and lets the user redesign Home without rebuilding data. The chosen ChatGPT/Claude clients must be mapped to whichever of these two capabilities they actually support.

Native Notion quick actions: Quick Add, Task Done, open Focus, Habit check-in, and open review. Waiting needs a reason and must not be a blind one-click status change. "Plan my day" and "Process Inbox" routes must clearly open prompt guidance or the actual connected AI client; do not mislabel a navigation button as an AI execution button. Templates provide short starting structures for Task, Project/phase, Goal, Note, and reviews. The Education Plus plan supports [database automations](https://www.notion.com/help/database-automations), so use a small, tested status-to-timestamp automation if it handles direct manual edits correctly. Do not create automation chains: one database automation cannot trigger another, and repeating-template creations do not trigger them. Keep AI summaries on request and the Mac calendar/recurrence services deterministic.

Database buttons require setup in Notion's interface: the public API can read a Button property's existence but cannot create/configure its actions or press it [per Notion](https://developers.notion.com/reference/property-object). The eventual implementation must perform and verify these UI steps through an available interactive route, or supply a precise manual handoff if the environment cannot access that interface. The metric path must not be declared ready until the Done action and any direct-status automation stamp Completed at correctly. A Habit check-in action should be checked for accidental double clicks; duplicate occurrence keys are surfaced and counted once rather than silently inflating metrics.

Recurring Task series are represented inside the Tasks database as Series records, hidden from ordinary Task views. Each Series has a human-readable pattern, a deterministic recurrence rule, one generation mode, and optional Plan/Due date offsets. Each occurrence is a separate Task linked to its Series and uses a stable series+date key; completed occurrences remain history. A simple series may use exactly one tested Notion repeating template if it correctly produces dated occurrences and can be updated without duplication. Other series use a retry-safe local generator, run at Mac login and daily while awake, to create the next 14 days' occurrences. It never backfills a pile of missed past occurrences after downtime; any missed historical period is recorded only if the user explicitly asks. A repeated run upserts by key and never generates the same occurrence twice. For a recurring activity without a true deadline, set Plan date to the occurrence day and leave Due date empty; a real recurring deadline is explicit in the Series rule. Notion's repeating templates can create independent pages on a schedule [per Notion](https://www.notion.com/help/database-templates). Do not rely on repeating templates to trigger downstream database automations [per Notion](https://www.notion.com/help/database-automations).

The initial experience uses on-request AI. Hosted Notion MCP requires interactive OAuth and currently does not offer non-interactive authorization for scheduled jobs [per Notion](https://developers.notion.com/guides/mcp/get-started-with-mcp). Background AI may be added later only with plan/cost/permission review, using a supported scheduled agent or separate API service. Manual workflows remain available whenever AI is disconnected.

## 8. Visual system

Use native Notion Default font at normal size, modest page width, clear section headings, limited dividers, simple consistent icons, sparse semantic color, and no large Home cover. Neutral = ordinary; blue = planning/navigation; amber = Waiting/attention; red = real deadline urgency; green = confirmed Done. All states also have text labels. Keep the Home vertical order on desktop and phone; deep database pages may be denser on desktop and use simpler list views on phone. Check light/dark mode and accessible contrast. Native Notion supports only Default/Serif/Mono styles, and phone layouts stack columns [per Notion](https://www.notion.com/en-gb/help/customize-and-style-your-content), [mobile columns](https://www.notion.com/help/columns-headings-and-dividers).

## 9. Technical delivery and safety

The build should use versioned declarative schema, view, and workflow definitions, with Notion IDs stored in a separate environment-specific manifest. The setup/update process must discover existing objects, plan changes, offer dry-run by default for structural changes, apply only intended differences, and validate the result. Retrying must not create duplicate databases, pages, views, properties, period logs, or managed occurrences. Use current supported API versions and confirm capabilities before implementation; the Notion Views API can manage linked and filtered views [per Notion](https://developers.notion.com/guides/data-apis/working-with-views).

Use minimum necessary access, environment-based secrets, bounded request queues, `Retry-After` handling, and read-after-write checks on ambiguous failures [per Notion](https://developers.notion.com/reference/request-limits). No secrets or private page bodies in logs. No routine deletion of databases, populated pages, properties, or meaningful content. Destructive migration requires a separate reviewed plan and explicit authorization. Preserve records across layout revisions.

Before changing populated schema, save a schema snapshot and export affected data, then verify the export. Export supports safekeeping but cannot instantly recreate the workspace, and exported relations do not simply reimport [per Notion](https://www.notion.com/help/workspace-settings), [relation export limits](https://www.notion.com/en-gb/help/relations-and-rollups). Keep a monthly export reminder and a recovery runbook. Validate conditional fields, relations, keys, view filters, and sample records after changes. The initial smoke test should be small and isolated. The [individual Education Plan](https://www.notion.com/help/notion-for-education) is Plus-equivalent, with unlimited uploads and 30-day page history, subject to annual education eligibility verification. Keep independent exports because page history is not a full relational backup.

## 10. Rollout and acceptance

Build in reviewable milestones: data model; daily Home with private Apple Calendar summary and AI operations; habits/reviews/metrics/recurrence; validation and handoff. The first usable release includes actual upcoming appointments on Home, natural-language record creation/editing, and the core daily experience. Seed the seven Areas plus the Tech Career Goal and ATLAS parent Project as Planned, linked as agreed. Do not invent ATLAS phases, Tasks, Goal horizon/evidence, or shipping criterion. Start Here explains how to complete those later.

Acceptance: Home order works on desktop and phone; Quick Add is obvious; normal daily use fits 5–10 minutes; confirmed priorities and reviews behave as specified; Waiting reason and follow-up logic work; dates are not conflated; ATLAS phase readiness is advisory and completion is confirmed; no duplicates arise on rerun; metrics match records; AI can complete representative create/edit/triage/review tasks with exact change reports; partial failures are recoverable; mobile/light/dark remain legible; data and secrets are preserved. Record any unmet criterion rather than quietly declaring completion.

See [schema and view contracts](schema-and-views.md) for property types, cardinality, derived signals, and the minimum view/filter definitions.

## Implementation readiness checks

These require the real accounts and device during the eventual build; they do not change the approved product design. Verify that the selected workspace has the individual Education Plus plan, read/write access for both AI clients, Mac Calendar permission and explicitly included calendars, native button/automation/template setup, recurrence behavior, and the current Notion API/view capabilities. [Dashboard views](https://www.notion.com/en-gb/help/dashboards) and [Custom Agents](https://www.notion.com/help/custom-agents) require Business or Enterprise; ongoing [Notion AI access](https://www.notion.com/help/upgrade-or-downgrade-your-plan) is not included with Plus. Stop and report any failed capability instead of silently omitting a required feature. Record all chosen workspace/calendar IDs and granted permissions in the handoff without recording secrets. The user explicitly ordered the Codex implementation prompt on 2026-09-29; its draft is saved beside this specification.
