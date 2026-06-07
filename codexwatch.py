#!/usr/bin/env python3
"""Codex hooks -> Bark notifications for iPhone / Apple Watch."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
CONFIG_FILE = ROOT / "config.json"
STATE_FILE = ROOT / "state.json"
LOG_FILE = ROOT / "events.jsonl"

DEFAULT_CONFIG = {
    "bark_server": "https://api.day.app",
    "bark_key": "",
    "group": "CodexWatch",
    "permission_group": "Codex Approval",
    "done_group": "Codex Done",
    "level": "timeSensitive",
    "icon_url": "https://cdn.jsdelivr.net/npm/@lobehub/icons-static-png@latest/light/codex-color.png",
    "done_cooldown_seconds": 30,
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data: Any, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    if mode is not None:
        path.chmod(mode)


def load_config() -> dict[str, Any]:
    config = dict(DEFAULT_CONFIG)
    config.update(load_json(CONFIG_FILE, {}))
    return config


def log_event(entry: dict[str, Any]) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def parse_bark_input(value: str) -> tuple[str | None, str]:
    value = value.strip()
    if value.startswith("http://") or value.startswith("https://"):
        parsed = urllib.parse.urlparse(value)
        path = parsed.path.strip("/")
        if not path:
            raise ValueError("Bark URL has no key in its path.")
        return f"{parsed.scheme}://{parsed.netloc}", path.split("/")[0]
    if len(value) < 8:
        raise ValueError("Bark key looks too short.")
    return None, value


def cmd_init(_args: argparse.Namespace) -> int:
    if CONFIG_FILE.exists():
        print(f"Config already exists: {CONFIG_FILE}")
        return 0
    save_json(CONFIG_FILE, DEFAULT_CONFIG, mode=0o600)
    print(f"Created config: {CONFIG_FILE}")
    return 0


def cmd_config_bark(args: argparse.Namespace) -> int:
    value = args.value.strip()
    if not value:
        print("Paste a Bark app sample URL or your Bark key:")
        value = input("> ").strip()
    server, key = parse_bark_input(value)
    config = load_config()
    if server:
        config["bark_server"] = server
    config["bark_key"] = key
    save_json(CONFIG_FILE, config, mode=0o600)
    masked = key[:4] + "*" * max(0, len(key) - 8) + key[-4:]
    print(f"Bark key saved: {masked}")
    return 0


def cmd_config_icon(args: argparse.Namespace) -> int:
    value = args.value.strip()
    if not (value.startswith("https://") or value.startswith("http://")):
        raise ValueError("Icon must be an HTTP(S) URL.")
    config = load_config()
    config["icon_url"] = value
    save_json(CONFIG_FILE, config, mode=0o600)
    print(f"Icon URL saved: {value}")
    return 0


def should_cooldown(event: str, config: dict[str, Any]) -> bool:
    if event == "permission":
        return False
    cooldown = int(config.get(f"{event}_cooldown_seconds", config.get("cooldown_seconds", 30)) or 0)
    if cooldown <= 0:
        return False
    state = load_json(STATE_FILE, {})
    now = time.time()
    last = float(state.get("last_sent", {}).get(event, 0) or 0)
    if now - last < cooldown:
        return True
    state.setdefault("last_sent", {})[event] = now
    save_json(STATE_FILE, state)
    return False


def read_stdin_text() -> str:
    if sys.stdin.isatty():
        return ""
    try:
        return sys.stdin.read()
    except Exception:
        return ""


def flatten_strings(obj: Any, acc: list[str] | None = None) -> list[str]:
    if acc is None:
        acc = []
    if isinstance(obj, str):
        acc.append(obj)
    elif isinstance(obj, dict):
        for value in obj.values():
            flatten_strings(value, acc)
    elif isinstance(obj, list):
        for value in obj:
            flatten_strings(value, acc)
    return acc


def parse_stdin_payload(stdin_text: str) -> dict[str, Any]:
    if not stdin_text.strip():
        return {}
    try:
        data = json.loads(stdin_text)
        return data if isinstance(data, dict) else {"value": data}
    except Exception:
        return {"raw_text": stdin_text}


def short_text(value: str, limit: int = 180) -> str:
    value = " ".join(str(value).split())
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


def looks_like_internal(value: str) -> bool:
    value = value.strip()
    if not value:
        return True
    if re.fullmatch(r"[0-9a-fA-F]{8,}(?:-[0-9a-fA-F]{4,}){2,}", value):
        return True
    if re.fullmatch(r"[0-9a-fA-F]{24,}", value):
        return True
    if re.fullmatch(r"[A-Za-z0-9_-]{24,}", value) and not any(ch.isspace() for ch in value):
        return True
    if ".codex/sessions/" in value or "/codex/sessions/" in value:
        return True
    if re.search(r"/rollout-[^/\s]+\.jsonl$", value):
        return True
    if value.startswith("/") and " " not in value:
        return True
    if value.startswith("~") and " " not in value:
        return True
    return False


def first_string(data: dict[str, Any], keys: list[str]) -> str:
    for key in keys:
        value: Any = data
        for part in key.split("."):
            if not isinstance(value, dict) or part not in value:
                value = None
                break
            value = value[part]
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def extract_tool_summary(payload: dict[str, Any]) -> str:
    tool_name = first_string(payload, ["tool_name", "tool", "tool_use.name", "name"])
    tool_input = payload.get("tool_input") or payload.get("input") or {}
    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except Exception:
            tool_input = {"raw": tool_input}
    if not isinstance(tool_input, dict):
        tool_input = {}
    detail = first_string(
        tool_input,
        ["command", "cmd", "file_path", "path", "notebook_path", "url", "description", "query"],
    )
    if not detail:
        detail = first_string(payload, ["command", "file_path", "path", "url", "message", "reason"])
    if not detail:
        strings = [s for s in flatten_strings(payload) if s.strip()]
        detail = strings[0] if strings else ""
    if tool_name and detail:
        return short_text(f"{tool_name}: {detail}")
    if tool_name:
        return short_text(tool_name)
    if detail:
        return short_text(detail)
    return "approval required"


def extract_done_summary(payload: dict[str, Any]) -> str:
    reason = first_string(payload, ["reason", "stop_reason", "message", "summary", "status"])
    if reason and not looks_like_internal(reason):
        return short_text(reason)
    return "ready for review"


def build_message(event: str, stdin_text: str) -> tuple[str, str]:
    payload = parse_stdin_payload(stdin_text)
    if event == "permission":
        summary = extract_tool_summary(payload)
        return ("Codex needs you", f"Waiting for approval: {summary}\nCome back and choose Allow / Yes.")
    if event == "done":
        summary = extract_done_summary(payload)
        return ("Codex finished", f"Codex is ready for review.\nStatus: {summary}")
    if event == "test":
        return ("CodexWatch test", "If this appears on your iPhone or Apple Watch, the Bark bridge is working.")
    summary = "Codex needs attention."
    if stdin_text:
        one_line = " ".join(stdin_text.split())
        if one_line:
            summary = one_line[:180]
    return ("Codex needs attention", summary)


def event_group(event: str, config: dict[str, Any]) -> str:
    if event == "permission":
        return str(config.get("permission_group", "Codex Approval"))
    if event == "done":
        return str(config.get("done_group", "Codex Done"))
    return str(config.get("group", "CodexWatch"))


def send_bark(title: str, body: str, config: dict[str, Any], group: str | None = None) -> bool:
    key = str(config.get("bark_key", "")).strip()
    if not key:
        print(f"Missing Bark key. Run: {Path(__file__).resolve()} config-bark '<Bark URL or key>'", file=sys.stderr)
        return False
    server = str(config.get("bark_server", "https://api.day.app")).rstrip("/")
    group = group or str(config.get("group", "CodexWatch"))
    level = str(config.get("level", "timeSensitive"))
    icon_url = str(config.get("icon_url", "")).strip()
    payload = {"device_key": key, "title": title, "body": body, "group": group, "level": level}
    if icon_url:
        payload["icon"] = icon_url
    try:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            f"{server}/push",
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            response = json.loads(resp.read().decode("utf-8"))
        return response.get("code") == 200
    except urllib.error.HTTPError as exc:
        print(f"Bark HTTP error {exc.code}: {exc.reason}", file=sys.stderr)
    except Exception as exc:
        print(f"Bark push failed: {exc}", file=sys.stderr)
    return False


def cmd_notify(args: argparse.Namespace) -> int:
    config = load_config()
    stdin_text = read_stdin_text()
    title, body = build_message(args.event, stdin_text)
    skipped = args.event != "test" and should_cooldown(args.event, config)
    group = event_group(args.event, config)
    ok = False if skipped else send_bark(title, body, config, group=group)
    log_event(
        {
            "timestamp": now_iso(),
            "event": args.event,
            "group": group,
            "title": title,
            "body": body,
            "skipped_by_cooldown": skipped,
            "sent": ok,
        }
    )
    if skipped:
        print(f"Skipped by cooldown: {args.event}")
    elif ok:
        print(f"Sent: {title}")
    else:
        print(f"Not sent: {title}", file=sys.stderr)
    return 0 if ok or skipped else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CodexWatch Bark notifier")
    sub = parser.add_subparsers(dest="cmd", required=True)
    init = sub.add_parser("init", help="Create config.json")
    init.set_defaults(func=cmd_init)
    cfg = sub.add_parser("config-bark", help="Save Bark URL or key")
    cfg.add_argument("value", nargs="?", default="")
    cfg.set_defaults(func=cmd_config_bark)
    icon = sub.add_parser("config-icon", help="Save notification icon URL")
    icon.add_argument("value")
    icon.set_defaults(func=cmd_config_icon)
    test = sub.add_parser("test", help="Send a test notification")
    test.set_defaults(func=lambda args: cmd_notify(argparse.Namespace(event="test")))
    notify = sub.add_parser("notify", help="Send a Codex event notification")
    notify.add_argument("event", choices=["permission", "done", "attention", "test"])
    notify.set_defaults(func=cmd_notify)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.func(args) or 0)
    except Exception as exc:
        print(f"CodexWatch error: {exc}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
