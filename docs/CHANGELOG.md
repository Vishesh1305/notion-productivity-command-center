# Change log

## 2026-10-25 — Vancouver dates and public repository preparation

- Stored mirrored timed appointments with Vancouver-local offsets so Notion's date picker opens at the expected local time. Verified the instant of each existing Event row against a private snapshot and confirmed a repeat sync did not rewrite events.
- Made the Mac job wrapper and LaunchAgent templates independent of one checkout path. Added a fuller ignore policy and public-safe documentation.

## 2026-10-01 — dashboard and selected-calendar read

- Rebuilt the private command-center root as a dashboard-style page with three navigation cards and four filtered live views. Kept the eight pages and ten source databases in a collapsed library; verified their block tags and rendered layout.
- Extended structural discovery into presentation containers so an ID-less setup recovery still finds those child pages and databases without creating duplicates.
- Selected three calendars for the read-only Apple Calendar mirror. A complete approved-window read succeeded and contained no events at the time; a wider local diagnostic read found later events. Recorded the successful empty read in Notion sync health and updated Home's calendar guidance.
- Verified native Task status automations with setup-only Done and Cancelled records; both timestamps were stamped. Added a secure Keychain token-entry helper.
- Added and tested a native `Mark Done` Task button and a native `Check in today` Habit button. The latter wrote a linked check-in with an Event time and Vancouver-local date/key. Matched the local retry key to Notion's compact page ID.
- Applied a compact Task page layout, hiding empty internal fields behind an expandable list. Tested a Focus-template Task from Waiting with a reason through one-click Done with a completion timestamp, and updated the template's action guidance.
- Verified Home sync freshness rendered both `Stale` and `Fresh` after a second complete read-only Apple scan.
- Corrected the local calendar export window to use Vancouver calendar-day boundaries across daylight saving changes.
- Created the scoped Notion internal connection, granted the private root, and stored its API token in Keychain. Direct inspect, calendar sync, recurrence, and metric refresh runs passed. Installed and verified three LaunchAgents; each first run exited successfully.
- Fixed the direct view inventory to hydrate Notion's ID-only list results, so a read-only inspect recognizes the 21 existing saved views and records their IDs without proposing duplicates.
- Python test suite now passes 28 tests.

## 2026-09-30 — local action and review checks

- Configured and fetched the live rolling seven-day Home appointment filter and overdue-or-next-fourteen-days Tasks deadline filter.
- Added the Home sync-health linked view, a singleton health record, and a versioned freshness formula. The Notion UI shows `Never synced` until the first successful Apple read. Added a Home Work dates table and live Notion Calendar web link.
- Added weekly follow-through count fields, a formula label, a Home linked view filtered to This week, and a retry-safe local refresh command. The command uses Vancouver completion dates and flags missing timestamps; a live plan has not yet exercised it.
- Exported and verified the populated Tasks source before adding a formula and saved `Needs attention` view for incomplete direct status edits. Applied and fetched Home's rolling Work dates filter.
- Added explicit cancellation with reason and timestamp, retry-safe daily and weekly confirmation, and separate Sunday and month-end draft review creation.
- Verified that a confirmed day can be retried after a selected Task is completed, while changed choices require a note. Added a failed calendar-write check so sync health advances only after all writes succeed.
- Python tests, shell syntax, plist validation, Objective-C syntax, and Git whitespace checks pass. Apple Calendar access and real appointment mirroring remain pending.
- Added Home's native Quick Add button in Notion. A short test capture was created from the button, read back with New status, and marked Processed with a timestamp; no real Inbox item was routed.
- Added and fetched a native Focus template in Tasks with next-action and checklist blocks. A setup-only Task created during template entry was cancelled with a reason and timestamp.

## 2026-09-29 — local implementation started

- Used the 2026-09-29 Education Plus decision; it supersedes the older Free-plan note.
- Began a Git-tracked implementation without moving or editing the three approved root documents.
- Added schema, additive reconciliation, domain rules, Apple Calendar read bridge/mirror, managed recurrence, starter seeding, and local tests.
- Verified Python tests and Swift syntax parsing. Full Swift type checking encountered a local compiler/SDK mismatch.
- Created one isolated private Notion smoke page, database, record, saved view, and linked page view in the selected private workspace. Connector create/edit/read and both view creation routes passed. IDs are in ignored `manifest.json`.
- Created the private production root, eight navigation pages, ten databases, relations, Home sections, supporting linked views, and saved database views. Configured Tasks, Projects, and Goals Status labels in Notion's desktop editor.
- Seeded seven Areas and the Planned Tech Career → Goal → ATLAS chain. Verified the Goal and Project relations by reading the created pages.
- The first usable release remains pending selected Apple calendars, actual appointments on Home, and live acceptance checks. Claude's write route is unverified.
- Added an Objective-C EventKit exporter to bypass the local Swift toolchain mismatch. It compiled and linked; the first read timed out while waiting for macOS Calendar permission. No appointment data was read or mirrored.
- Completed Capture Queue's New, Needs clarification, and Processed Status choices, with both open states in the To-do group. A live fetch confirmed all twenty named saved views across the ten databases.
