# CodexWatch Bark

Global Codex hooks that send Bark push notifications to your iPhone / Apple Watch when Codex needs approval or finishes a turn.

This is intentionally small: one Python script, one installer, no dependencies beyond Python 3 and Bark.

## What It Does

- `PermissionRequest` -> Bark notification in the `Codex Approval` group.
- `Stop` -> Bark notification in the `Codex Done` group.
- Uses Bark V2 `/push` JSON API.
- Uses `level=timeSensitive`.
- Adds a Codex icon by default.
- Does not cooldown approval requests, so back-to-back approvals are not missed.
- Applies a 30-second cooldown to `Stop` notifications to reduce noise.

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
