# Contributing

This project combines public implementation code with a private live Notion workspace. Contributions should be reviewable without access to that workspace.

1. Start with `python -m unittest discover -s tests -q` and `python -m command_center.cli plan` (or install the package and use `command-center plan`).
2. Keep behavior changes in `src/command_center/` and update the versioned contract and docs when data-model behavior changes.
3. Add focused offline tests for logic that could change records, date interpretation, duplicate detection, or recovery. Do not commit real Notion exports as fixtures.
4. For macOS scripts, run `zsh -n macos/*.sh` one file at a time and `plutil -lint` on each LaunchAgent example. The EventKit bridge must remain read-only.
5. Explain any required Notion UI step, since native buttons, automations, and some view filters cannot be fully represented by the local CLI.

Never include API tokens, `manifest.json`, page or calendar IDs from a real workspace, appointment content, logs, or export snapshots in a commit, issue, screenshot, or test. If a change needs a live check, record only the outcome and a sanitized description.
