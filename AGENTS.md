# AGENTS.md

This repository installs CodexWatch Bark, a small global Codex hooks -> Bark notification bridge.

Follow these rules when helping a user install or modify it:

- Read `README.md` and `SECURITY.md` first.
- Never overwrite an existing `~/.codex/hooks.json`; merge only CodexWatch hook entries.
- Back up `~/.codex/hooks.json` before editing it.
- Store Bark keys only in `~/.codex/codexwatch/config.json` with `600` permissions.
- Do not print the full Bark key in logs or final responses.
- Use Bark V2 `/push` JSON API.
- Keep `PermissionRequest` notifications uncooldowned.
- Keep `Stop` notifications cooled down with `done_cooldown_seconds`, default 30 seconds.
- Treat `Stop` notifications as lower-confidence than `PermissionRequest` notifications. Codex Desktop may run internal helper turns that also trigger global `Stop` hooks.
- Do not use the notifier process directory as a fallback context for `Stop` notifications. It can become a low-signal value such as `app`, especially on Windows.
- Preserve filtering for internal title-generation prompts and low-signal completion contexts such as app-only internal events; do not filter a real user workspace just because its folder name is `app`. Filtered events should log `skipped_by_filter: true`, send no Bark push, and not refresh the done cooldown.
- Keep Windows path handling for `.codex\sessions\...` and bare drive-letter paths when filtering internal/session paths.
- After install, run a test push.
- Tell the user that already-running Codex sessions may not hot-load hooks; new/restarted sessions may require hook review/trust.
