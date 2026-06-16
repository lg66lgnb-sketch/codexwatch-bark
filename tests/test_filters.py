import importlib.util
import json
import os
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


MODULE_PATH = Path(__file__).resolve().parents[1] / "codexwatch.py"
SPEC = importlib.util.spec_from_file_location("codexwatch", MODULE_PATH)
codexwatch = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(codexwatch)


def write_session(root: Path, *, cwd: str = r"C:\work\project", message: str = "Finish this task") -> Path:
    path = root / ".codex" / "sessions" / "2026" / "06" / "16" / "rollout-test.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {"type": "session_meta", "payload": {"cwd": cwd}},
        {"payload": {"type": "user_message", "message": message}},
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    return path


class DoneFilterTests(unittest.TestCase):
    def test_cwd_only_done_is_filtered_by_default(self) -> None:
        payload = {"cwd": r"C:\Users\lg66l\Documents\Router VPN"}

        reason = codexwatch.notification_filter_reason(
            "done",
            "Codex finished: Router VPN",
            payload,
            "",
            config=codexwatch.DEFAULT_CONFIG,
        )

        self.assertEqual(reason, "missing_session_path")

    def test_cwd_only_done_can_be_opted_back_in(self) -> None:
        payload = {"cwd": r"C:\Users\lg66l\Documents\Router VPN"}
        config = dict(codexwatch.DEFAULT_CONFIG, require_done_session_path=False)

        reason = codexwatch.notification_filter_reason(
            "done",
            "Codex finished: Router VPN",
            payload,
            "",
            config=config,
        )

        self.assertEqual(reason, "")

    def test_codex_app_path_is_filtered_before_missing_session_path(self) -> None:
        payload = {"cwd": r"C:\Program Files\WindowsApps\OpenAI.Codex_1.0.0.0_x64__abc\app"}

        reason = codexwatch.notification_filter_reason(
            "done",
            "Codex finished: app",
            payload,
            "",
            config=codexwatch.DEFAULT_CONFIG,
        )

        self.assertEqual(reason, "codex_app_path")

    def test_fresh_session_path_allows_real_workspace_named_app(self) -> None:
        with TemporaryDirectory() as tmp:
            session_path = write_session(
                Path(tmp),
                cwd=r"C:\Users\lg66l\Documents\app",
                message="Keep working in the app workspace",
            )
            payload = {"session_path": str(session_path)}

            reason = codexwatch.notification_filter_reason(
                "done",
                "Codex finished: app",
                payload,
                "",
                config=codexwatch.DEFAULT_CONFIG,
            )

        self.assertEqual(reason, "")

    def test_stale_session_path_is_filtered(self) -> None:
        with TemporaryDirectory() as tmp:
            session_path = write_session(Path(tmp), cwd=r"C:\Users\lg66l\Documents\Router VPN")
            old_time = time.time() - 3600
            os.utime(session_path, (old_time, old_time))
            payload = {"session_path": str(session_path)}

            reason = codexwatch.notification_filter_reason(
                "done",
                "Codex finished: Router VPN",
                payload,
                "",
                config=codexwatch.DEFAULT_CONFIG,
            )

        self.assertEqual(reason, "stale_session_path")


if __name__ == "__main__":
    unittest.main()
