#!/usr/bin/env bash
set -euo pipefail

HOOKS="$HOME/.codex/hooks.json"
STAMP="$(date +%Y%m%d_%H%M%S)"

if [ ! -f "$HOOKS" ]; then
  echo "No ~/.codex/hooks.json found."
  exit 0
fi

cp "$HOOKS" "$HOOKS.codexwatch-uninstall.bak.$STAMP"

/usr/bin/python3 - "$HOOKS" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
hooks = data.get("hooks", {})

for event, groups in list(hooks.items()):
    new_groups = []
    for group in groups or []:
        if not isinstance(group, dict):
            new_groups.append(group)
            continue
        kept = [
            hook for hook in group.get("hooks", [])
            if not (isinstance(hook, dict) and "codexwatch.py" in hook.get("command", ""))
        ]
        if kept:
            new_group = dict(group)
            new_group["hooks"] = kept
            new_groups.append(new_group)
    if new_groups:
        hooks[event] = new_groups
    else:
        hooks.pop(event, None)

path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

echo "Removed CodexWatch hooks. Backup: $HOOKS.codexwatch-uninstall.bak.$STAMP"
echo "The ~/.codex/codexwatch directory was left in place so you can keep logs/config."
