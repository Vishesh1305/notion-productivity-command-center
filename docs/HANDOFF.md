# Operator handoff

This public handoff explains the working system without publishing a private Notion workspace link or local manifest. The exact verification inventory is in [STATUS.md](../STATUS.md).

## Start a day

1. Open the private Productivity Command Center **Home** page in Notion.
2. Check the Daily Top 3, Calendar freshness, and up to two weekly priorities.
3. Use **Quick Add** to capture raw thoughts before deciding where they belong.
4. Work from Tasks. Keep a real **Due date**, a chosen **Plan date**, and an optional **Time block** separate.
5. Mark a Task Done through its canonical action. Enter a reason before moving it to Waiting.

## Local operator commands

From the repository root, run `command-center plan` for an offline structural preview and `command-center inspect` for a read-only comparison with the selected private workspace. `apply` is the explicit additive structural write. `macos/run-job.sh sync-calendar` runs the Keychain-backed mirror on demand; `generate-recurrence` and `refresh-metric` invoke the other Mac jobs.

The ignored `manifest.json` contains the selected private parent, stable Notion IDs, and selected Apple Calendar IDs. Back it up privately. The Notion internal-connection token belongs in macOS Keychain under the `notion-command-center` service, never in the repository or a chat transcript.

## Scope and recovery

- The calendar mirror reads only explicitly selected Apple calendars. It writes a private display cache containing title, time, all-day state, and sync metadata. It cannot edit Apple appointments.
- If Home says **Stale**, consult the separate live Notion Calendar app for current commitments. A Mac that is off or asleep cannot refresh the mirror.
- If a setup write fails ambiguously, inspect the existing Notion record by ID or logical key before retrying. Repeated blind writes can duplicate records.
- Preserve ignored `exports/` snapshots before changing populated schema. They are safekeeping artifacts, not an instant relational restore.
- The shared [AI behavior guide](AI-BEHAVIOR.md) lists routine actions, confirmation gates, and report requirements for each connected client. Check each client's actual write access before relying on it.

See [Setup and recovery](SETUP.md) for the full installation path and [STATUS.md](../STATUS.md) for open checks.
