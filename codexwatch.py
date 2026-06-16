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
SESSION_PATH_PATTERN = re.compile(
    r"(?:~|/|[A-Za-z]:[\\/])[^\s\"']*\.codex[\\/]sessions[\\/][^\s\"']+?\.jsonl"
)
LOW_SIGNAL_DONE_CONTEXTS = {"app"}
IGNORED_CONTEXT_LABELS = {
    "router",
    "codex",
    "openai",
    "assistant",
    "system",
    "macos",
}
INTERNAL_PROMPT_MARKERS = (
    "short title for a task",
    "generate a concise ui title",
)
PATH_CONTEXT_KEYS = [
    "cwd",
    "workdir",
    "working_directory",
    "workspace",
    "workspace_root",
    "project_path",
    "directory",
]
APP_PATH_CONTEXT_KEYS = PATH_CONTEXT_KEYS + [
    "process_cwd",
    "current_directory",
]
SESSION_PATH_KEYS = [
    "session_path",
    "transcript_path",
    "conversation_path",
    "rollout_path",
    "log_path",
]

DEFAULT_CONFIG = {
    "bark_server": "https://api.day.app",
    "bark_key": "",
    "group": "CodexWatch",
    "permission_group": "Codex Approval",
    "done_group": "Codex Done",
    "level": "timeSensitive",
    "icon_url": "https://cdn.jsdelivr.net/npm/@lobehub/icons-static-png@latest/light/codex-color.png",
    "done_cooldown_seconds": 30,
    "done_session_fresh_seconds": 600,
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
    normalized = value.replace("\\", "/")
    if not value:
        return True
    if re.fullmatch(r"[0-9a-fA-F]{8,}(?:-[0-9a-fA-F]{4,}){2,}", value):
        return True
    if re.fullmatch(r"[0-9a-fA-F]{24,}", value):
        return True
    if re.fullmatch(r"[A-Za-z0-9_]{24,}", value) and any(ch.isdigit() for ch in value):
        return True
    if ".codex/sessions/" in normalized or "/codex/sessions/" in normalized:
        return True
    if re.search(r"/rollout-[^/\s]+\.jsonl$", normalized):
        return True
    if value.startswith("/") and " " not in value:
        return True
    if value.startswith("~") and " " not in value:
        return True
    if re.match(r"^[A-Za-z]:/", normalized) and " " not in value:
        return True
    return False


def clean_label(value: str, limit: int = 80) -> str:
    value = " ".join(str(value).strip().split())
    value = value.strip(" -:|")
    if not value or looks_like_internal(value):
        return ""
    if value.casefold() in IGNORED_CONTEXT_LABELS:
        return ""
    if value.startswith("{") or value.startswith("[") or value.startswith("<"):
        return ""
    return short_text(value, limit)


def is_internal_prompt_text(value: str) -> bool:
    text = " ".join(str(value).lower().split())
    return any(marker in text for marker in INTERNAL_PROMPT_MARKERS)


def is_low_signal_done_context(value: str) -> bool:
    return value.strip().casefold() in LOW_SIGNAL_DONE_CONTEXTS


def looks_like_codex_app_path(value: str) -> bool:
    normalized = str(value).replace("\\", "/").casefold().rstrip("/")
    return (
        "/appdata/local/programs/codex/app" in normalized
        or ("/windowsapps/openai.codex_" in normalized and normalized.endswith("/app"))
        or "/applications/codex.app" in normalized
        or normalized.endswith("/codex.app/contents/macos")
    )


def has_non_internal_path_context(payload: dict[str, Any], stdin_text: str) -> bool:
    for key in PATH_CONTEXT_KEYS:
        value = nested_value(payload, key)
        if isinstance(value, str) and basename_label(value) and not looks_like_codex_app_path(value):
            return True

    for path in extract_session_paths(payload, stdin_text):
        user_label, cwd_label = session_context_from_file(path)
        if user_label or cwd_label:
            return True

    return False


def has_codex_app_path_context(payload: dict[str, Any]) -> bool:
    for key in APP_PATH_CONTEXT_KEYS:
        value = nested_value(payload, key)
        if isinstance(value, str) and looks_like_codex_app_path(value):
            return True
    return False


def session_path_age_seconds(path: Path, now: float | None = None) -> float | None:
    try:
        modified = path.expanduser().stat().st_mtime
    except OSError:
        return None
    return max(0.0, (time.time() if now is None else now) - modified)


def has_fresh_session_path(paths: list[Path], max_age_seconds: int, now: float | None = None) -> bool:
    if max_age_seconds <= 0:
        return True
    return any(
        age is not None and age <= max_age_seconds
        for age in (session_path_age_seconds(path, now=now) for path in paths)
    )


def count_fresh_session_paths(paths: list[Path], max_age_seconds: int, now: float | None = None) -> int:
    if max_age_seconds <= 0:
        return len(paths)
    return sum(
        1
        for age in (session_path_age_seconds(path, now=now) for path in paths)
        if age is not None and age <= max_age_seconds
    )


def basename_label(value: str) -> str:
    value = str(value).strip()
    if not value:
        return ""
    try:
        path = Path(value).expanduser()
    except Exception:
        return ""
    name = path.name
    if not name and path.parent != path:
        name = path.parent.name
    return clean_label(name, limit=80)


def nested_value(data: dict[str, Any], key: str) -> Any:
    value: Any = data
    for part in key.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def first_string(data: dict[str, Any], keys: list[str]) -> str:
    for key in keys:
        value = nested_value(data, key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def first_path_basename(data: dict[str, Any], keys: list[str]) -> str:
    for key in keys:
        value = nested_value(data, key)
        if isinstance(value, str):
            label = basename_label(value)
            if label:
                return label
    return ""


def extract_session_paths_from_keys(payload: dict[str, Any]) -> list[Path]:
    paths: list[Path] = []
    seen: set[str] = set()
    for key in SESSION_PATH_KEYS:
        value = nested_value(payload, key)
        if not isinstance(value, str):
            continue
        for match in SESSION_PATH_PATTERN.findall(value):
            path = Path(match).expanduser()
            path_key = str(path)
            if path_key not in seen:
                paths.append(path)
                seen.add(path_key)
    return paths


def extract_session_paths(payload: dict[str, Any], stdin_text: str) -> list[Path]:
    candidates: list[str] = []
    for key in SESSION_PATH_KEYS + ["reason", "status", "message"]:
        value = nested_value(payload, key)
        if isinstance(value, str):
            candidates.append(value)
    candidates.extend(flatten_strings(payload))
    if stdin_text:
        candidates.append(stdin_text)

    paths: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        for match in SESSION_PATH_PATTERN.findall(candidate):
            path = Path(match).expanduser()
            key = str(path)
            if key not in seen:
                paths.append(path)
                seen.add(key)
    return paths


def label_from_user_message(message: str) -> str:
    text = message.strip()
    marker = "## My request for Codex:"
    if marker in text:
        text = text.split(marker, 1)[1]
    for notification_marker in ["Codex finished:", "Codex needs you:", "Thread:", "Status:"]:
        index = text.find(notification_marker)
        if index > 0:
            text = text[:index].strip()
            break
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("# Files mentioned"):
            continue
        if line.startswith("## ") or line.startswith("<image ") or line.startswith("</image"):
            continue
        if line.startswith("![") or line.startswith("<environment_context"):
            continue
        if line.startswith("/") and " " not in line:
            continue
        if re.match(r"^[A-Za-z]:[\\/]", line) and " " not in line:
            continue
        lines.append(line)
    return clean_label(lines[0] if lines else text, limit=80)


def session_context_from_file(path: Path) -> tuple[str, str]:
    if not path.exists() or not path.is_file():
        return "", ""

    cwd_label = ""
    latest_user_label = ""
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if (
                    '"session_meta"' not in line
                    and '"turn_context"' not in line
                    and '"user_message"' not in line
                    and '"role":"user"' not in line
                    and '"role": "user"' not in line
                ):
                    continue
                try:
                    item = json.loads(line)
                except Exception:
                    continue

                payload = item.get("payload") if isinstance(item, dict) else None
                if not isinstance(payload, dict):
                    continue

                if item.get("type") in {"session_meta", "turn_context"}:
                    cwd = payload.get("cwd")
                    if isinstance(cwd, str) and not cwd_label:
                        cwd_label = basename_label(cwd)
                    continue

                if payload.get("type") == "user_message":
                    label = label_from_user_message(str(payload.get("message", "")))
                    if label:
                        latest_user_label = label
                    continue

                if payload.get("role") == "user":
                    content = payload.get("content")
                    if isinstance(content, list):
                        parts = []
                        for part in content:
                            if isinstance(part, dict) and isinstance(part.get("text"), str):
                                parts.append(part["text"])
                        label = label_from_user_message("\n".join(parts))
                        if label:
                            latest_user_label = label
    except Exception:
        return "", ""
    return latest_user_label, cwd_label


def extract_context_label(
    payload: dict[str, Any],
    stdin_text: str,
    allow_process_cwd_fallback: bool = True,
    max_session_age_seconds: int | None = None,
) -> str:
    explicit = first_string(
        payload,
        [
            "conversation_title",
            "thread_title",
            "chat_title",
            "session_title",
            "project_name",
            "workspace_name",
            "title",
        ],
    )
    label = clean_label(explicit)
    if label:
        return label

    for path in extract_session_paths(payload, stdin_text):
        if max_session_age_seconds is not None and not has_fresh_session_path([path], max_session_age_seconds):
            continue
        user_label, cwd_label = session_context_from_file(path)
        if user_label:
            return user_label
        if cwd_label:
            return cwd_label

    label = first_path_basename(
        payload,
        PATH_CONTEXT_KEYS,
    )
    if label:
        return label

    if allow_process_cwd_fallback:
        return basename_label(str(Path.cwd()))
    return ""


def title_with_context(base: str, context: str) -> str:
    if not context:
        return base
    return short_text(f"{base}: {context}", 90)


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


def done_body(summary: str) -> str:
    if summary == "ready for review":
        return "Ready for review."
    return f"Summary: {summary}"


def build_message(event: str, stdin_text: str, config: dict[str, Any] | None = None) -> tuple[str, str]:
    payload = parse_stdin_payload(stdin_text)
    max_session_age = None
    if event == "done":
        max_session_age = int((config or DEFAULT_CONFIG).get("done_session_fresh_seconds", 600) or 0)
    context = extract_context_label(
        payload,
        stdin_text,
        allow_process_cwd_fallback=event != "done",
        max_session_age_seconds=max_session_age,
    )
    if event == "permission":
        summary = extract_tool_summary(payload)
        return (
            title_with_context("Codex needs you", context),
            f"Approval: {summary}\nOpen Codex to allow or deny.",
        )
    if event == "done":
        summary = extract_done_summary(payload)
        return (
            title_with_context("Codex finished", context),
            done_body(summary),
        )
    if event == "test":
        return ("CodexWatch test", "If this appears on your iPhone or Apple Watch, the Bark bridge is working.")
    summary = "Codex needs attention."
    if stdin_text:
        one_line = " ".join(stdin_text.split())
        if one_line:
            summary = one_line[:180]
    return ("Codex needs attention", summary)


def notification_filter_reason(
    event: str,
    title: str,
    payload: dict[str, Any],
    stdin_text: str,
    config: dict[str, Any] | None = None,
) -> str:
    if event != "done":
        return ""
    if any(is_internal_prompt_text(value) for value in flatten_strings(payload)):
        return "internal_prompt"
    if has_codex_app_path_context(payload):
        return "codex_app_path"

    session_paths = extract_session_paths_from_keys(payload)
    max_age = int((config or DEFAULT_CONFIG).get("done_session_fresh_seconds", 600) or 0)
    if session_paths and not has_fresh_session_path(session_paths, max_age):
        return "stale_session_path"

    context = extract_context_label(
        payload,
        stdin_text,
        allow_process_cwd_fallback=False,
        max_session_age_seconds=max_age,
    )
    if not context:
        return "missing_context"
    if is_low_signal_done_context(context) and not has_non_internal_path_context(payload, stdin_text):
        return "low_signal_context"
    return ""


def should_filter_notification(
    event: str,
    title: str,
    payload: dict[str, Any],
    stdin_text: str,
    config: dict[str, Any] | None = None,
) -> bool:
    return bool(notification_filter_reason(event, title, payload, stdin_text, config=config))


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
    payload = parse_stdin_payload(stdin_text)
    title, body = build_message(args.event, stdin_text, config=config)
    filter_reason = notification_filter_reason(args.event, title, payload, stdin_text, config=config)
    filtered = bool(filter_reason)
    skipped = (not filtered) and args.event != "test" and should_cooldown(args.event, config)
    group = event_group(args.event, config)
    session_paths = extract_session_paths_from_keys(payload) if args.event == "done" else []
    max_session_age = int(config.get("done_session_fresh_seconds", 600) or 0)
    ok = False if skipped or filtered else send_bark(title, body, config, group=group)
    log_event(
        {
            "timestamp": now_iso(),
            "event": args.event,
            "group": group,
            "title": title,
            "body": body,
            "skipped_by_filter": filtered,
            "filter_reason": filter_reason,
            "session_path_count": len(session_paths),
            "fresh_session_path_count": count_fresh_session_paths(session_paths, max_session_age),
            "skipped_by_cooldown": skipped,
            "sent": ok,
        }
    )
    if filtered:
        print(f"Skipped by filter: {title}")
    elif skipped:
        print(f"Skipped by cooldown: {args.event}")
    elif ok:
        print(f"Sent: {title}")
    else:
        print(f"Not sent: {title}", file=sys.stderr)
    return 0 if ok or skipped or filtered else 1


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
