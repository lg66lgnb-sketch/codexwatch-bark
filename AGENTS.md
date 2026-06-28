# AGENTS.md

This repository installs CodexWatch Bark, a small global Codex hooks -> Bark notification bridge.

Follow these rules when helping a user install or modify it:

- Read `README.md`, `SECURITY.md`, and `CHANGELOG.md` first.
- Never overwrite an existing `~/.codex/hooks.json`; merge only CodexWatch hook entries.
- Back up `~/.codex/hooks.json` before editing it.
- Store Bark keys only in `~/.codex/codexwatch/config.json` with `600` permissions.
- Do not print the full Bark key in logs or final responses.
- Use Bark V2 `/push` JSON API.
- Keep `PermissionRequest` notifications uncooldowned.
- Keep `Stop` notifications cooled down with `done_cooldown_seconds`, default 30 seconds.
- Treat `Stop` notifications as lower-confidence than `PermissionRequest` notifications. Codex Desktop may run internal helper turns that also trigger global `Stop` hooks.
- Do not use the notifier process directory as a fallback context for `Stop` notifications. It can become a low-signal value such as `app`, especially on Windows.
- Treat Codex install directories as internal app contexts, including Windows packaged paths like `C:\Program Files\WindowsApps\OpenAI.Codex_...\app`.
- Preserve filtering for internal title-generation prompts and low-signal completion contexts such as app-only internal events; do not filter a real user workspace just because its folder name is `app`. Filtered events should log `skipped_by_filter: true`, send no Bark push, and not refresh the done cooldown.
- Keep Windows path handling for `.codex\sessions\...` and bare drive-letter paths when filtering internal/session paths.
- Keep `require_done_session_path` enabled by default. A cwd/workspace path alone is not enough proof for a `Stop` push because Codex Desktop helper stops can expose stale inactive project paths such as `Router VPN`.
- If `require_done_session_path` is disabled for an environment with no session paths, still require a strong thread/session/automation title. Do not re-enable cwd/workspace path fallback for `Stop` notifications.
- Treat session paths in `Stop` payloads as stale unless at least one referenced session file was modified within `done_session_fresh_seconds`, default 600 seconds. This prevents old project names from being pushed during unrelated active work.
- Preserve `filter_reason`, `session_path_count`, and `fresh_session_path_count` logging so future agents can distinguish `internal_prompt`, `codex_app_path`, `missing_session_path`, `stale_session_path`, `missing_context`, and `low_signal_context` without logging full session paths.
- After install, run a test push.
- Tell the user that already-running Codex sessions may not hot-load hooks; new/restarted sessions may require hook review/trust.
