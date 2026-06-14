# CodexWatch Bark

Global Codex hooks that send Bark push notifications to your iPhone / Apple Watch when Codex needs approval or finishes a turn.

This is intentionally small: one Python script, one installer, no dependencies beyond Python 3 and Bark.

## What It Does

- `PermissionRequest` -> Bark notification in the `Codex Approval` group.
- `Stop` -> Bark notification in the `Codex Done` group.
- Uses Bark V2 `/push` JSON API.
- Uses `level=timeSensitive`.
- Adds a Codex icon by default.
- Adds a short thread/context label to approval and completion notifications when available.
- Does not cooldown approval requests, so back-to-back approvals are not missed.
- Applies a 30-second cooldown to `Stop` notifications to reduce noise.
- Filters low-signal or internal `Stop` events so Codex Desktop helper tasks do not produce misleading completion pushes.
- Filters stale `Stop` events that point at old session files instead of the task that just finished.

## Install

1. Install Bark on your iPhone.
2. In the Bark app, copy a sample URL from the home screen. The `Icon` or `Notification Grouping` examples are ideal.
3. Run:

```bash
git clone https://github.com/lg66lgnb-sketch/codexwatch-bark.git
cd codexwatch-bark
bash install.sh 'https://api.day.app/YOUR_BARK_KEY/Notification%20Grouping?group=CodexWatch'
```

You can also run `bash install.sh` and paste the Bark URL when prompted.

The installer:

- copies `codexwatch.py` to `~/.codex/codexwatch/codexwatch.py`
- stores your Bark key in `~/.codex/codexwatch/config.json`
- backs up `~/.codex/hooks.json`
- merges CodexWatch entries into global Codex hooks
- sends a test Bark notification

New or restarted Codex sessions may ask you to review/trust hooks before they run.

## Troubleshooting

### Extra `Codex finished: app` Notifications

Codex Desktop can run internal helper turns, such as UI title generation, that may also fire global `Stop` hooks. On some Windows installs those internal stops can expose only a low-signal context like `app`; older CodexWatch versions used the current process directory as a fallback and could send misleading `Codex finished: app` pushes.

This is more likely in projectless or file-mentioned Codex Desktop conversations, where internal app-level turns may run with a Codex installation cwd such as `C:\Program Files\WindowsApps\OpenAI.Codex_...\app`.

CodexWatch now treats `Stop` notifications more strictly than approval notifications:

- `Stop` notifications must have a real thread/session/workspace context.
- Internal title-generation prompts are filtered.
- Low-signal completion contexts such as `app` are filtered only when they are not backed by a real non-internal workspace or session path.
- Filtered notifications are logged with `skipped_by_filter: true`, do not send Bark pushes, and do not refresh the done cooldown.

If this bug reappears, inspect `~/.codex/codexwatch/events.jsonl` first. A correct filtered event should have `"sent": false` and `"skipped_by_filter": true`.

### Extra `Codex finished: Other Project` Notifications

If a completion notification appears during a different active task and names an unrelated old project, the hook payload may have referenced a stale `.codex/sessions/...` transcript. This can happen even when that other project is not running.

CodexWatch now treats session paths in `Stop` payloads as time-sensitive:

- `done_session_fresh_seconds` defaults to `600`.
- A `Stop` notification with one or more session paths is sent only if at least one referenced session file was modified within that freshness window.
- Stale session-path events are logged with `filter_reason: "stale_session_path"`, `skipped_by_filter: true`, and `"sent": false`.
- Done events also log `session_path_count` and `fresh_session_path_count` without storing full session paths.
- Filtered stale events do not refresh the done cooldown, so the real completion notification can still be sent normally.

If you intentionally need a larger window for unusually delayed hooks, raise `done_session_fresh_seconds` in `~/.codex/codexwatch/config.json`.

## Changelog

### 2026-06-14

- Added stale session-path filtering for `Stop` notifications to prevent cross-thread completion pushes such as `Codex finished: Router VPN` during unrelated work.
- Added `filter_reason` to local event logs for filtered notifications.
- Added `done_session_fresh_seconds`, default `600`, to control how fresh a referenced session file must be for completion pushes.
- Recognized Windows packaged Codex install paths such as `C:\Program Files\WindowsApps\OpenAI.Codex_...\app` as internal app contexts.

### 2026-06-12

- Added Windows-aware `.codex/sessions/...` path detection and filtering.
- Stopped using the notifier process directory as the fallback context for `Stop` notifications.
- Filtered internal Codex Desktop helper `Stop` events, including low-signal `Codex finished: app` notifications.

## Test A Real Approval

Start a new interactive Codex session with approval prompts enabled, then ask it to run a harmless command:

```bash
codex --ask-for-approval untrusted --sandbox read-only
```

Prompt:

```text
For this approval test, try to run exactly this shell command: mkdir -p /tmp/codexwatch-approval-test. Do not do anything else.
```

When Codex shows the approval prompt, you should also receive a Bark notification.

## Uninstall

```bash
bash uninstall.sh
```

This removes only CodexWatch hook entries from `~/.codex/hooks.json`. It leaves `~/.codex/codexwatch/` in place so you can keep logs/config or delete it manually.

## Ask Another Agent To Install It

Use this short prompt:

```text
Please read https://github.com/lg66lgnb-sketch/codexwatch-bark and give me instructions to set it up. Before making changes, check README.md, AGENTS.md, and SECURITY.md. Do not overwrite my existing ~/.codex/hooks.json; merge the CodexWatch hooks only.
```
