# Changelog

This file preserves maintenance context and past notification-filter incidents. Keep the README focused on installation and daily use.

## 2026-06-16

- Required `Stop` notifications to include a session/transcript path by default with `require_done_session_path: true`.
- Filtered no-session completion events with `filter_reason: "missing_session_path"`.
- Kept cwd-only events filtered as `missing_context` when the session-path requirement is explicitly disabled.
- Added tests covering cwd-only events, strong-title opt-out, stale sessions, Windows Codex paths, and real workspaces named `app`.
- Fixed false completion pushes such as `Codex finished: Router`, `Codex finished: Stock`, and unrelated project names emitted while another task was still running.

## 2026-06-14

- Added `done_session_fresh_seconds`, default `600`, to reject stale session references.
- Added `filter_reason`, `session_path_count`, and `fresh_session_path_count` to local event logs without storing full session paths.
- Recognized packaged Windows Codex paths such as `C:\Program Files\WindowsApps\OpenAI.Codex_...\app` as internal contexts.
- Ensured filtered events do not refresh the completion cooldown.

## 2026-06-12

- Added Windows-aware `.codex\sessions\...` path handling.
- Stopped using the notifier process directory as a fallback for `Stop` notifications.
- Filtered internal title-generation prompts and low-signal Codex Desktop helper events.

## 2026-06-10

- Added thread/context labels to approval and completion notifications.
- Separated Bark groups for approvals and completions.
- Kept approval notifications uncooldowned and completion notifications on a 30-second cooldown.
- Compact notification bodies replaced repeated thread and status text.

## Filter Invariants

- `PermissionRequest` is high-confidence and must not be cooldowned.
- `Stop` is lower-confidence because Codex Desktop helper turns can trigger global hooks.
- A cwd or workspace path alone is not proof that a user task finished.
- Session paths must be recent before a completion notification is sent.
- Internal app paths and title-generation prompts must not produce Bark pushes.
- Filtered events must log `skipped_by_filter: true`, send no push, and leave the done cooldown unchanged.
