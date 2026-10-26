# Schema and view contracts

Working detail for the [command-center specification](specification.md). Notion property names are user-facing defaults and may be renamed safely after IDs are recorded. Logical constraints are validated by the setup/update process and AI operations where Notion has no native required/unique constraint. No user data has been created.

## Common conventions

- Every record uses the Notion page ID as its durable identity. Keys below are additional idempotency keys for period or recurrence lookups.
- A Notion `date` field with time is stored with an explicit timezone or unambiguous instant; day-only fields and planning cutoffs use `America/Vancouver`, including daylight saving transitions.
- Defaults are applied by templates/AI/setup where Notion has no schema-level default. A missing property value is not automatically interpreted as an approved decision.
- `Status` means a Notion Status property when its groups fit the approved lifecycle; otherwise use Select. Display labels remain exactly as approved.
- Conditional required fields are checked when a record enters an active state, and invalid records appear in a Needs attention view rather than disappearing.
- Preserve created and last edited timestamps supplied by Notion. Managed completion/cancellation timestamps are separate Date properties. On Education Plus, test a direct Status-change automation for these timestamps; the canonical action and Needs attention check remain the fallback.

## Property dictionary

### Tasks

| Name | Notion type | Rule |
| --- | --- | --- |
| Name | Title | Required at creation. |
| Record type | Select | Task or Series; default Task. Series records are hidden from ordinary work views. |
| Status | Status | To do, In progress, Waiting, Done, Cancelled; default To do. |
| Commitment | Select | Committed or Someday; default Committed for clear tasks. |
| Priority | Select | High, Normal, Low; default Normal. |
| Due date | Date | Optional real deadline; date with time allowed. |
| Plan date | Date | Optional day-only intended work date. |
| Time block | Date range | Optional confirmed start and end. |
| Project | Relation → Projects | At most one. |
| Standalone Area | Relation → Areas | At most one; used only without Project. |
| Parent Task | Relation → Tasks | At most one, with Children inverse. |
| Blocked by | Relation → Tasks | Zero or more; no cycles. |
| Waiting reason | Rich text | Nonempty when Waiting. |
| Follow-up date | Date | Optional for Waiting. |
| Non-blocking for phase | Checkbox | Default false; relevant to phase-owned Tasks. |
| Series key | Rich text | Optional stable recurrence series ID. |
| Series | Relation → Tasks | Occurrence links to one Series record. |
| Recurrence pattern | Rich text | Human-readable rule on a Series. |
| Recurrence rule | Rich text | Machine-readable deterministic rule on a Series, validated before activation. |
| Generation mode | Select | Native template or Managed local generator; exactly one per Series. |
| Recurrence start / end | Date | Optional boundaries on a Series. |
| Plan / Due offset | Number or structured rule text | Optional rule for occurrence dates; Due date is set only for real recurring deadlines. |
| Occurrence date | Date | Optional day-only occurrence date for recurring Tasks. |
| Occurrence key | Rich text | Unique logical `series key + occurrence date`. |
| Completed at | Date/time | Set by the canonical Done action or AI edit; test a Plus automation for direct manual Status changes. |
| Cancelled at | Date/time | Set by canonical cancellation or AI edit; test a Plus automation for direct manual Status changes. |
| Cancellation reason | Rich text | Optional, recommended for phase gate changes. |
| Change note | Rich text | Last significant AI/user plan or lifecycle change; deeper history remains in page body/log. |

Effective Area is the Project's primary Area when Project exists; otherwise Standalone Area. Show a formula display property if Notion's formula behavior supports it in the chosen views. Do not maintain two conflicting editable Area values. A Task assigned to a child phase follows that phase's Area, which normally matches its parent.

### Projects

| Name | Notion type | Rule |
| --- | --- | --- |
| Name | Title | Required. |
| Status | Status | Planned, Active, Paused, Done, Cancelled. |
| Primary Area | Relation → Areas | Exactly one before Active. |
| Goal | Relation → Goals | At most one direct Goal; parent/phase defaults to parent's Goal. |
| Parent Project | Relation → Projects | At most one, with Children inverse; no cycles. |
| Definition of done | Rich text, extended details in body | Nonempty before Active. |
| Target date | Date | Optional target, distinct from Task Due date. |
| Project kind | Select | Project or Phase; child phases use Phase. |
| Completed at / Cancelled at | Date/time | Lifecycle history. |
| Outcome note | Rich text | Evidence/decision when closing or cancelling. |

Readiness is a derived display signal: if `Project kind = Phase`, at least one Task belongs to it with `Non-blocking for phase = false`, and all those Tasks have `Status = Done`, show `Ready for review`; otherwise show count of remaining blocking Tasks. A phase's parent Project may show child phase progress, but its Done status still requires user confirmation. A Paused or Cancelled project remains in history.

### Goals

| Name | Notion type | Rule |
| --- | --- | --- |
| Name | Title | Required. |
| Status | Status | Planned, Active, Paused, Achieved, Dropped. |
| Primary Area | Relation → Areas | Exactly one before Active. |
| Review horizon | Date | Required before Active. |
| Evidence definition | Rich text, details in body | Observable success/progress rule required before Active. |
| Evidence summary | Rich text | Updated with review, with historical review in Planning Log. |
| Achieved at / Dropped at | Date/time | Human-confirmed lifecycle. |

Contributing Projects appear through the inverse of Projects.Goal. A Goal may exist without a Project while Planned. No nested Goals.

### Areas

Name (Title); Purpose (Rich text); State (Select: Active, Archived). These seven names are initially seeded: Tech Career, Education, Health, Finances, Relationships, Home & Life Admin, Recreation. The `Archived` state is an ordinary property; the design does not depend on Notion's plan-limited native Archive feature.

### Notes

Name (Title); Body (page content); optional Area, Goal, and Project Relations; optional Source capture Relation → Capture Queue. Blank filing relations are valid. A derived Task must link back or mention the source Note; the source is preserved.

### Capture Queue

Name (Title, short readable excerpt); Original text (full page body or rich-text blocks); Captured at (Created time); Status (Status: New, Needs clarification, Processed); Clarification question (Rich text); Result links (page links in body, supporting more than one result type); Processed at (Date/time). Original text is never replaced by an AI interpretation. An item can yield multiple results but remains one original capture.

### Habits

Name (Title); Primary Area (Relation → Areas, at most one); Cadence type (Select: Daily, Selected weekdays, N per week); Weekdays (Multi-select, only for Selected weekdays); Weekly target (Number, only for N per week); Status (Select: Active, Paused, Archived); Start date (Date); optional End date (Date); optional Numeric target (Number) and Unit (Rich text); optional Replaces Habit (self Relation, single). A cadence change starts a new linked Habit version and archives the prior definition after confirmation. Existing check-ins remain attached to the old version and keep their original denominator rules.

### Habit Check-ins

Name (Title, generated from Habit/date/event); Habit (Relation → Habits, exactly one); Event type (Select: Check-in, Pause started, Pause ended); Occurrence date (Date, for Check-in); Check-in status (Select: Done, Excused, for Check-in); optional Amount (Number), Note (Rich text); Event time (Date/time); Occurrence key (Rich text, unique logical Habit ID + occurrence date for Check-in). Pause event pairs define excluded intervals. Duplicate Check-in keys are surfaced and treated as one opportunity in calculations; never silently delete records.

### Calendar Events (managed display cache)

Kind (Select: Event, Sync health); Name (Title, appointment title or `Calendar sync`); Start (Date/time); End (Date/time); All day (Checkbox); State (Select: Current, Cancelled, Expired); Source calendar key (Rich text, internal); Source occurrence key (Rich text, unique logical identity); Last seen at (Date/time); Last successful sync (Date/time, on the singleton Sync health record); Sync freshness (Formula: stale when last successful sync is more than 30 minutes ago). The sync updates only this managed database, never Tasks or Apple Calendar. No location, attendee, note, description, or invite-link property. Keep the database/page private and do not publish it. The Home view shows only Current Event records in the next seven days from explicitly selected Apple Calendar calendars, with title and time. The singleton Sync health record supplies last-sync and stale status. The sync reads yesterday through the next 14 days, runs at Mac login and about every 15 minutes while awake, and changes missing-event state only after a complete successful fetch.

### Planning Log

Name (Title, generated from period type/key); Period type (Select: Daily, Weekly, Monthly); Period key (Rich text, unique with type); Start and End (Date); State (Select: Draft, Confirmed); Proposed Top 1/2/3 and Confirmed Top 1/2/3 (six single Relations → Tasks, used for Daily); Weekly priority 1/2 proposal and confirmation (Rich text, with optional related Goal/Project links); Summary (Rich text or page body); Review notes (page body); Change note (Rich text); Confirmed at (Date/time); Related week (self Relation, Daily → one Weekly, with Days inverse). Monthly adjustment proposals and accepted decisions live in the page body with clear Draft/Confirmed headings. A log may have its review section incomplete without creating a second record.

The first confirmed Daily Log in a week creates/finds its Weekly Log and links to it. Sunday review updates the ending Weekly Log and creates/finds the following Weekly Log for next week's priorities. `Period key` uses the selected timezone and Monday–Sunday week. A repeated create request must search by type and key before writing.

## Minimum views and filters

| Page / view | Filter | Sort or display |
| --- | --- | --- |
| Home / Daily Top 3 | Today's Daily Log, Confirmed | Three ordered confirmed Task slots; empty state offers Plan my day route. |
| Home / Calendar | Current Calendar Events in next seven days, plus Tasks with Plan date this week and separate Due date soon list | Appointment agenda first (title/time only), then Task dates; last-sync label and full live Notion Calendar link. |
| Home / Weekly priorities | Current Weekly Log, Confirmed choices | Maximum two, ordered. |
| Home / Inbox | Capture Queue Status New or Needs clarification | Pending count and Quick Add; oldest first in full view. |
| Home / Active Projects | Project Status Active, top-level only | Nearest Target date, then name; link phases from project page. |
| Home / Progress Metric | Current Weekly Log | Completed/confirmed Top 3 slots, raw count. |
| Tasks / Today | Record type Task, Committed, open, Plan date today | High priority then Due date, with a separate older Plan date attention group. |
| Tasks / Upcoming deadlines | Record type Task, Committed, open, Due date <=14 days | Overdue first, then Due date ascending. |
| Tasks / Waiting | Status Waiting | Follow-up date ascending; no-date items remain visible. |
| Tasks / Backlog | Record type Task, Committed, To do, no Plan date | Due date then Priority. |
| Tasks / Someday | Record type Task, Commitment Someday, open | Last edited oldest first for monthly reconsideration. |
| Tasks / Completed | Status Done or Cancelled | Lifecycle timestamp descending. |
| Tasks / Recurring series | Record type Series | Active patterns, next generation date, and generation mode. |
| Projects / Active & Phases | Active, with parent/child relation | Parent then phase order/target. |
| Goals & Areas / Active | Active Goals, Active Areas | Review horizon then name. |
| Notes / Recent | All Notes | Last edited descending; optional unfiled filter. |
| Habits & Reviews / Current | Active Habits, current check-ins and Logs | Today/this week; full history linked. |
| Needs attention | Invalid conditional fields, duplicate keys, broken relation/phase mismatch | Error type then oldest first. |

## Derived calculations and validation

1. **Urgency:** real Due date before now/today is overdue; near due is a visual warning, separate from Priority and Top 3. Time-of-day comparison applies only where Due date has a time.
2. **Phase readiness:** count blocking Tasks and blocking Tasks Done; show ready only when denominator > 0 and counts match. Display a warning if a child phase's Area or Goal conflicts with its parent.
3. **Top 3 follow-through:** each confirmed Daily Log contributes its nonempty final confirmed slots to the weekly denominator. A slot contributes to the numerator if the related Task's Completed at falls on or before that local day end and no earlier than the start of that day; earlier completion implies it should not have been selected as an open Task. If Completed at is missing, flag the Task and exclude it pending correction. Weekly Log sums related Daily contributions. Replans preserve the final choices and a change note.
4. **Habit consistency:** count eligible occurrences from cadence/start/end and pause intervals, subtract explicit Excused opportunities, then count unique Done occurrence keys up to the eligible target. For N/week, prorate target by active days, rounded up. Show a recent period (for example 4 weeks) with raw counts; the user can change the display period later without changing records.
5. **Identity checks:** `Period type + Period key`, `Habit ID + occurrence date`, and managed `Series key + Occurrence date` are unique logical keys. Duplicates are reported in Needs attention and not included twice in metrics. Notion itself does not enforce uniqueness; writer logic and validation do.
