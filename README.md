# CodexWatch Bark

> [中文版见下方 / Chinese version below](#chinese-version)

## Ask Another Agent To Install It

Send this prompt to your agent:

```text
Please read https://github.com/lg66lgnb-sketch/codexwatch-bark and help me set it up. Before making changes, check README.md, AGENTS.md, SECURITY.md, and CHANGELOG.md. Do not overwrite my existing ~/.codex/hooks.json; merge the CodexWatch hooks only.
```

CodexWatch Bark sends Codex approval and completion events to Bark, so they can appear on your iPhone and Apple Watch.

It uses one Python script, one installer, and no third-party Python packages.

## What It Does

| Codex event | Bark notification |
| --- | --- |
| `PermissionRequest` | Immediate alert in `Codex Approval`; no cooldown |
| `Stop` | Completion alert in `Codex Done`; 30-second cooldown |

Notifications use Bark's V2 API, `timeSensitive` level, a Codex icon, and a short thread label when available.

Completion events are filtered more strictly because Codex Desktop can emit internal or stale `Stop` events. By default, a completion push requires a recent session/transcript path. Cwd-only, stale, internal-app, and low-signal events are logged but not pushed.

## Requirements

- Codex with global hooks support
- macOS with Bash and `/usr/bin/python3`
- Bark installed on your iPhone

The filter also recognizes Windows Codex and session paths, but `install.sh` targets macOS.

## Install

1. Install Bark on your iPhone.
2. From Bark's home screen, copy a sample URL. The `Icon` or `Notification Grouping` example is ideal.
3. Run:

```bash
git clone https://github.com/lg66lgnb-sketch/codexwatch-bark.git
cd codexwatch-bark
bash install.sh 'https://api.day.app/YOUR_BARK_KEY/Notification%20Grouping?group=CodexWatch'
```

You can also run `bash install.sh` without an argument and paste the URL when prompted.

The installer:

- installs the notifier in `~/.codex/codexwatch/`
- stores the Bark key in `config.json` with `600` permissions
- backs up and merges `~/.codex/hooks.json`
- sends a test notification

Restart Codex after installation. A new session may ask you to review or trust the hooks.

## Test

Send a test push:

```bash
/usr/bin/python3 ~/.codex/codexwatch/codexwatch.py test
```

To test a real approval, start Codex with approval prompts:

```bash
codex --ask-for-approval untrusted --sandbox read-only
```

Then ask it:

```text
For this approval test, try to run exactly this shell command: mkdir -p /tmp/codexwatch-approval-test. Do not do anything else.
```

## Troubleshooting

Check:

```text
~/.codex/codexwatch/events.jsonl
```

A filtered event has `"skipped_by_filter": true` and `"sent": false`. Common reasons are `missing_session_path`, `stale_session_path`, `missing_context`, `internal_prompt`, and `codex_app_path`.

Relevant settings in `~/.codex/codexwatch/config.json`:

| Setting | Default | Purpose |
| --- | ---: | --- |
| `done_cooldown_seconds` | `30` | Reduces duplicate completion pushes |
| `done_session_fresh_seconds` | `600` | Rejects old session references |
| `require_done_session_path` | `true` | Rejects cwd-only completion events |

Keep `require_done_session_path` enabled unless your Codex environment cannot provide session paths. Disabling it still requires a strong thread, session, or automation title.

Implementation history and past false-notification incidents are documented in [CHANGELOG.md](CHANGELOG.md).

## Uninstall

```bash
bash uninstall.sh
```

This removes only CodexWatch entries from `~/.codex/hooks.json`. Local config and logs remain in `~/.codex/codexwatch/`.

## Security

Your Bark key stays in `~/.codex/codexwatch/config.json`. Notification title and body are sent to your configured Bark server; approval alerts may include a short command, path, URL, or tool summary. See [SECURITY.md](SECURITY.md).

---

## Chinese Version

### 让另一个 Agent 帮你安装

把这段指令发给你的 Agent：

```text
请阅读 https://github.com/lg66lgnb-sketch/codexwatch-bark 并帮我完成配置。修改前先检查 README.md、AGENTS.md、SECURITY.md 和 CHANGELOG.md。不要覆盖我现有的 ~/.codex/hooks.json，只合并 CodexWatch 的 hooks。
```

CodexWatch Bark 会把 Codex 的权限审批和任务完成事件发送到 Bark，让通知显示在 iPhone 和 Apple Watch 上。

项目只有一个 Python 脚本和一个安装器，不依赖第三方 Python 包。

### 功能

| Codex 事件 | Bark 通知 |
| --- | --- |
| `PermissionRequest` | 立即发送到 `Codex Approval`，不设冷却 |
| `Stop` | 发送到 `Codex Done`，冷却 30 秒 |

通知使用 Bark V2 API、`timeSensitive` 级别、Codex 图标，并在可用时显示简短的会话名称。

Codex Desktop 可能产生内部或过期的 `Stop` 事件，因此完成通知会严格过滤。默认只有带近期 session/transcript 路径的完成事件才会推送；仅有 cwd、过期 session、Codex 内部任务和低信息事件只记日志，不推送。

### 环境要求

- 支持全局 hooks 的 Codex
- 带有 Bash 和 `/usr/bin/python3` 的 macOS
- iPhone 已安装 Bark

过滤器也能识别 Windows 的 Codex 和 session 路径，但 `install.sh` 面向 macOS。

### 安装

1. 在 iPhone 上安装 Bark。
2. 从 Bark 首页复制一条示例 URL，推荐 `Icon` 或 `Notification Grouping`。
3. 运行：

```bash
git clone https://github.com/lg66lgnb-sketch/codexwatch-bark.git
cd codexwatch-bark
bash install.sh 'https://api.day.app/YOUR_BARK_KEY/Notification%20Grouping?group=CodexWatch'
```

也可以直接运行 `bash install.sh`，再按提示粘贴 URL。

安装器会：

- 把通知脚本安装到 `~/.codex/codexwatch/`
- 以 `600` 权限保存 Bark key
- 备份并合并 `~/.codex/hooks.json`
- 发送一条测试通知

安装后重启 Codex。新会话可能会要求你检查或信任 hooks。

### 测试

发送测试通知：

```bash
/usr/bin/python3 ~/.codex/codexwatch/codexwatch.py test
```

测试真实权限审批：

```bash
codex --ask-for-approval untrusted --sandbox read-only
```

然后输入：

```text
For this approval test, try to run exactly this shell command: mkdir -p /tmp/codexwatch-approval-test. Do not do anything else.
```

### 排查

查看日志：

```text
~/.codex/codexwatch/events.jsonl
```

被过滤的事件会显示 `"skipped_by_filter": true` 和 `"sent": false`。常见原因包括 `missing_session_path`、`stale_session_path`、`missing_context`、`internal_prompt` 和 `codex_app_path`。

`~/.codex/codexwatch/config.json` 中的相关配置：

| 配置 | 默认值 | 作用 |
| --- | ---: | --- |
| `done_cooldown_seconds` | `30` | 减少重复的完成通知 |
| `done_session_fresh_seconds` | `600` | 拒绝过期的 session 引用 |
| `require_done_session_path` | `true` | 拒绝只有 cwd 的完成事件 |

除非你的 Codex 环境无法提供 session 路径，否则应保持 `require_done_session_path` 开启。关闭后，事件仍需提供可靠的 thread、session 或 automation 标题。

过滤逻辑的历史和过往误报记录见 [CHANGELOG.md](CHANGELOG.md)。

### 卸载

```bash
bash uninstall.sh
```

它只会移除 `~/.codex/hooks.json` 中的 CodexWatch 条目，本地配置和日志仍保留在 `~/.codex/codexwatch/`。

### 安全

Bark key 保存在 `~/.codex/codexwatch/config.json`。通知标题和正文会发送到你配置的 Bark 服务器；权限通知可能包含简短的命令、路径、URL 或工具摘要。详见 [SECURITY.md](SECURITY.md)。
