# Implementation status

This file records the state of the **implementation**, not a public copy of a live Notion workspace. Private page IDs, calendar IDs, exports, and appointment content are intentionally absent.

## Built and checked

| Area | State | Evidence |
| --- | --- | --- |
| Data model | Built | Ten source databases, relations, formulas, and 21 declared saved views are versioned in `definitions.py`. |
| Setup/reconciliation | Built | Offline plan, read-only live inspect, explicit additive apply, ID manifest, duplicate stops, and pre-change exports for populated schema. |
| Dashboard | Built in a private workspace | Root dashboard with navigation cards and filtered live views; Home has the six planned sections. |
| Task flow | Checked with setup-only records | Quick Add, Focus template, Done/Cancelled timestamps, Waiting reason, and Needs attention. |
| Calendar mirror | Checked with real selected-calendar events | Read-only EventKit export, bounded private Notion mirror, freshness record, and Vancouver-local date picker format. A migration preserved all existing event instants. |
| Local background jobs | Installed and checked on macOS | Calendar sync about every 15 minutes, recurrence generation daily, and follow-through metric refresh hourly. |
| Habits | Checked with setup-only records | Native check-in button and local duplicate-aware check-in/report logic. |
| Test suite | Passing | `python -m unittest discover -s tests -q` passed 31 tests on 2026-10-25. |

The latest calendar check compared every current and older mirrored Event row against a local pre-change snapshot. All Start and End instants were preserved while their stored values changed from UTC display to Vancouver local offsets. A second sync made zero event updates. The macOS calendar LaunchAgent was restarted and exited successfully.

## Work still to verify

- A separate Claude client must pass its own Notion read/write smoke test before its action route can be called available.
- Review Home on a real phone and in light mode. A narrow desktop browser viewport is not a substitute for a native phone check.
- Check Notion's relative **This week** filter at a Vancouver Sunday/Monday boundary.
- Exercise weekly follow-through against a real confirmed plan and run the actual Sunday/month-end review flow.
- Connect desired accounts in the separate Notion Calendar app if a combined live calendar view is wanted. The Home mirror reads Apple Calendar independently.

The live workspace is private. This public repository is an implementation reference and does not contain a Notion template export or a user's records.
