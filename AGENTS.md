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
- After install, run a test push.
- Tell the user that already-running Codex sessions may not hot-load hooks; new/restarted sessions may require hook review/trust.
