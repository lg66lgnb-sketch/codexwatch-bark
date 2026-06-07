# Security

## Secrets

Your Bark key is stored locally in:

```text
~/.codex/codexwatch/config.json
```

The installer writes this file with user-only permissions (`600`). Do not commit this file or share it publicly.

## Data Sent To Bark

CodexWatch sends only notification title/body/group/icon metadata to the configured Bark server.

For approval notifications, the body may include a short command, file path, URL, or tool summary from the Codex hook payload.

For completion notifications, CodexWatch filters internal IDs, `.codex/sessions/...` paths, `rollout-*.jsonl`, and bare filesystem paths.

## Local Files

CodexWatch writes:

- `~/.codex/codexwatch/config.json`
- `~/.codex/codexwatch/state.json`
- `~/.codex/codexwatch/events.jsonl`

It modifies:

- `~/.codex/hooks.json`

The installer backs up an existing hooks file before merging changes.
