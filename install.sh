#!/usr/bin/env bash
set -euo pipefail

DEST="$HOME/.codex/codexwatch"
HOOKS="$HOME/.codex/hooks.json"
STAMP="$(date +%Y%m%d_%H%M%S)"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BARK_INPUT="${1:-}"

mkdir -p "$DEST" "$HOME/.codex"
install -m 755 "$SCRIPT_DIR/codexwatch.py" "$DEST/codexwatch.py"

if [ ! -f "$DEST/config.json" ]; then
  install -m 600 "$SCRIPT_DIR/config.example.json" "$DEST/config.json"
fi

if [ -z "$BARK_INPUT" ]; then
  echo "Paste a Bark app sample URL or Bark key."
  echo "Example: https://api.day.app/MY_BARK_KEY/Notification%20Grouping?group=CodexWatch"
  read -r -p "> " BARK_INPUT
fi

/usr/bin/python3 "$DEST/codexwatch.py" config-bark "$BARK_INPUT"

if [ -f "$HOOKS" ]; then
  cp "$HOOKS" "$HOOKS.codexwatch.bak.$STAMP"
  echo "Backed up existing hooks to $HOOKS.codexwatch.bak.$STAMP"
fi

/usr/bin/python3 - "$HOOKS" "$DEST/codexwatch.py" <<'PY'
import json
import sys
from pathlib import Path

hooks_path = Path(sys.argv[1])
script = sys.argv[2]

if hooks_path.exists():
    try:
        data = json.loads(hooks_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raise SystemExit(f"Could not parse existing hooks file: {hooks_path}")
else:
    data = {}

hooks = data.setdefault("hooks", {})

def without_codexwatch(groups):
    cleaned = []
    for group in groups or []:
        if not isinstance(group, dict):
            cleaned.append(group)
            continue
        inner = group.get("hooks", [])
        kept = []
        for hook in inner:
            if isinstance(hook, dict) and "codexwatch.py" in hook.get("command", ""):
                continue
            kept.append(hook)
        if kept:
            new_group = dict(group)
            new_group["hooks"] = kept
            cleaned.append(new_group)
    return cleaned

def add_hook(event, command, status, matcher=None):
    groups = without_codexwatch(hooks.get(event, []))
    group = {
        "hooks": [{
            "type": "command",
            "command": command,
            "timeout": 10,
            "statusMessage": status,
        }]
    }
    if matcher is not None:
        group["matcher"] = matcher
    groups.append(group)
    hooks[event] = groups

add_hook(
    "PermissionRequest",
    f"/usr/bin/python3 {script} notify permission",
    "Sending CodexWatch approval notification",
    matcher="*",
)
add_hook(
    "Stop",
    f"/usr/bin/python3 {script} notify done",
    "Sending CodexWatch completion notification",
)

hooks_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

/usr/bin/python3 -m py_compile "$DEST/codexwatch.py"
/usr/bin/python3 -m json.tool "$HOOKS" >/dev/null
/usr/bin/python3 "$DEST/codexwatch.py" test

echo
echo "CodexWatch installed."
echo "Open a new Codex session and trust/review hooks if prompted."
