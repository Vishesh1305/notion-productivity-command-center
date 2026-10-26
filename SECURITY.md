# Security and privacy

The repository contains tooling for a private Notion workspace and selected Apple calendars. It must not contain live workspace data.

## Report a security issue

Please do **not** open a public issue with a token, private page link, calendar event, or exploit details. Use GitHub's private vulnerability reporting feature if it is available for this repository, or contact the repository owner privately through their GitHub profile.

If a credential is exposed, revoke or rotate it in the issuing service immediately, remove the credential from local configuration, and inspect Git history before republishing. Deleting a line in a later commit does not remove it from earlier public commits.

## Data boundaries

- The Notion connection token is supplied from the environment or macOS Keychain. It is never committed.
- `manifest.json`, `exports/`, compiled helpers, calendar payloads, and logs are ignored.
- The EventKit helper reads selected calendars only. The mirror copies title, start/end, all-day state, and internal sync metadata into a private Notion database.
- Additive setup uses a dry-run/inspect path and local snapshots before changing populated schema.
