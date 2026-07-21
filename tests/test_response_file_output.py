import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
CLI_DIR = REPO_ROOT / "cli" / "python"
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))

import unity_puer_exec  # type: ignore
import unity_puer_exec_runtime as runtime  # type: ignore


class ProjectResponseFileUnitTests(unittest.TestCase):
    """Direct coverage of the centralized post-normalization projection helper."""

    def test_no_response_file_is_a_passthrough(self):
        result = runtime._project_response_file(None, 0, '{"ok": true}', "")
        self.assertEqual(result, (0, '{"ok": true}', ""))

    def test_successful_projection_writes_exact_envelope_and_hash(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = os.path.join(temp_dir, "out.json")
            body = {"ok": True, "status": "completed", "operation": "exec", "request_id": "R1", "result": {"x": 1}}
            stdout_text = runtime.emit_payload(body)

            exit_code, new_stdout, new_stderr = runtime._project_response_file(dest, 0, stdout_text, "")

            self.assertEqual(exit_code, 0)
            self.assertEqual(new_stderr, "")
            with open(dest, "rb") as handle:
                stored = handle.read()
            self.assertEqual(stored, stdout_text.encode("utf-8"))

            ref = json.loads(new_stdout)
            self.assertEqual(ref["ok"], True)
            self.assertEqual(ref["status"], "completed")
            self.assertEqual(ref["operation"], "exec")
            self.assertEqual(ref["request_id"], "R1")
            self.assertNotIn("result", ref)
            self.assertEqual(ref["response_file"]["path"], os.path.abspath(dest))
            self.assertEqual(ref["response_file"]["encoding"], "utf-8")
            self.assertEqual(ref["response_file"]["byte_count"], len(stored))
            self.assertEqual(ref["response_file"]["sha256"], hashlib.sha256(stored).hexdigest())

    def test_missing_parent_directory_is_created(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = os.path.join(temp_dir, "nested", "deeper", "out.json")
            stdout_text = runtime.emit_payload({"ok": True, "status": "completed"})

            runtime._project_response_file(dest, 0, stdout_text, "")

            self.assertTrue(os.path.isfile(dest))

    def test_existing_destination_is_fully_replaced(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = os.path.join(temp_dir, "out.json")
            with open(dest, "w", encoding="utf-8") as handle:
                handle.write("stale-previous-content")

            stdout_text = runtime.emit_payload({"ok": True, "status": "completed", "result": {"big": "x" * 500}})
            runtime._project_response_file(dest, 0, stdout_text, "")

            with open(dest, "rb") as handle:
                stored = handle.read()
            self.assertEqual(stored, stdout_text.encode("utf-8"))
            self.assertNotIn(b"stale-previous-content", stored)

    def test_stderr_response_preserves_stream_and_exit_code(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = os.path.join(temp_dir, "out.json")
            stderr_text = runtime.emit_payload({"ok": False, "status": "failed", "operation": "exec", "error": "boom"})

            exit_code, new_stdout, new_stderr = runtime._project_response_file(dest, 1, "", stderr_text)

            self.assertEqual(exit_code, 1)
            self.assertEqual(new_stdout, "")
            ref = json.loads(new_stderr)
            self.assertEqual(ref["status"], "failed")
            self.assertIn("response_file", ref)
            with open(dest, "rb") as handle:
                stored = handle.read()
            self.assertEqual(stored, stderr_text.encode("utf-8"))

    def test_write_failure_falls_back_to_original_response_with_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            # A destination that collides with an existing directory can never be
            # opened as a file, forcing a persistence failure.
            blocking_dir = os.path.join(temp_dir, "blocked")
            os.makedirs(blocking_dir)
            dest = blocking_dir  # path itself is a directory, not a file

            stdout_text = runtime.emit_payload({"ok": True, "status": "completed", "operation": "exec", "request_id": "R2"})
            exit_code, new_stdout, new_stderr = runtime._project_response_file(dest, 0, stdout_text, "")

            self.assertEqual(exit_code, 0)
            self.assertEqual(new_stderr, "")
            body = json.loads(new_stdout)
            self.assertTrue(body["ok"])
            self.assertEqual(body["status"], "completed")
            self.assertEqual(body["request_id"], "R2")
            self.assertIn("response_file_error", body)
            self.assertNotIn("response_file", body)

    def test_write_failure_leaves_existing_destination_untouched(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = os.path.join(temp_dir, "out.json")
            with open(dest, "w", encoding="utf-8") as handle:
                handle.write("previous-good-response")

            # Simulate a failure during the atomic replace step itself.
            with mock.patch.object(runtime, "_atomic_write_bytes", side_effect=OSError("disk full")):
                stdout_text = runtime.emit_payload({"ok": True, "status": "completed"})
                exit_code, new_stdout, _ = runtime._project_response_file(dest, 0, stdout_text, "")

            self.assertEqual(exit_code, 0)
            body = json.loads(new_stdout)
            self.assertIn("response_file_error", body)
            with open(dest, "r", encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "previous-good-response")

    def test_non_json_response_is_left_unprojected(self):
        result = runtime._project_response_file("/some/path.json", 2, "", "usage: not json")
        self.assertEqual(result, (2, "", "usage: not json"))


class ResponseFileCliIntegrationTests(unittest.TestCase):
    """End-to-end coverage through unity_puer_exec.run_cli, matching design.md scenarios."""

    def _make_log(self, content):
        f = tempfile.NamedTemporaryFile(mode="wb", suffix=".log", delete=False)
        f.write(content.encode("utf-8"))
        f.close()
        return f.name

    def test_get_log_briefs_response_file_projects_full_result(self):
        content = "First entry\n\n[Error] Second entry\n"
        path = self._make_log(content)
        try:
            size = os.path.getsize(path)
            with tempfile.TemporaryDirectory() as temp_dir:
                dest = os.path.join(temp_dir, "briefs.json")
                exit_code, stdout, stderr = unity_puer_exec.run_cli([
                    "get-log-briefs",
                    "--unity-log-path", path,
                    "--range", "0-{}".format(size),
                    "--response-file", dest,
                ])
                self.assertEqual(exit_code, 0)
                self.assertEqual(stderr, "")
                ref = json.loads(stdout)
                self.assertIn("response_file", ref)
                self.assertNotIn("result", ref)
                with open(dest, "r", encoding="utf-8") as handle:
                    full = json.load(handle)
                self.assertTrue(full["ok"])
                self.assertIsInstance(full["result"], list)
                self.assertEqual(len(full["result"]), 2)
        finally:
            os.unlink(path)

    def test_get_log_briefs_default_invocation_is_unchanged_without_response_file(self):
        content = "First entry\n\n[Error] Second entry\n"
        path = self._make_log(content)
        try:
            size = os.path.getsize(path)
            exit_code, stdout, stderr = unity_puer_exec.run_cli([
                "get-log-briefs",
                "--unity-log-path", path,
                "--range", "0-{}".format(size),
            ])
            self.assertEqual(exit_code, 0)
            body = json.loads(stdout)
            self.assertNotIn("response_file", body)
            self.assertIsInstance(body["result"], list)
        finally:
            os.unlink(path)

    def test_exec_base_url_response_file_projects_large_unicode_result(self):
        large_result = {"payload": "值" * 2000, "n": 12345}
        completed_body = {
            "ok": True,
            "status": "completed",
            "operation": "exec",
            "request_id": "R-large",
            "result": large_result,
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = os.path.join(temp_dir, "exec-response.json")
            with mock.patch.object(
                unity_puer_exec.direct_exec_client,
                "invoke_command",
                return_value=(0, json.dumps(completed_body), ""),
            ):
                exit_code, stdout, stderr = unity_puer_exec.run_cli([
                    "exec",
                    "--base-url", "http://127.0.0.1:55231",
                    "--code", "export default function run(ctx) { return 1; }",
                    "--request-id", "R-large",
                    "--response-file", dest,
                ])

            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr, "")
            ref = json.loads(stdout)
            self.assertEqual(ref["request_id"], "R-large")
            self.assertIn("response_file", ref)
            self.assertEqual(ref["response_file"]["path"], os.path.abspath(dest))
            with open(dest, "rb") as handle:
                stored = handle.read()
            self.assertEqual(ref["response_file"]["byte_count"], len(stored))
            self.assertEqual(ref["response_file"]["sha256"], hashlib.sha256(stored).hexdigest())
            full = json.loads(stored.decode("utf-8"))
            self.assertEqual(full["result"]["n"], 12345)
            self.assertIn("值", full["result"]["payload"])

    def test_wait_for_exec_response_file_recovers_without_reexecuting(self):
        completed_body = {
            "ok": True,
            "status": "completed",
            "operation": "wait-for-exec",
            "request_id": "R-recover",
            "result": {"done": True},
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = os.path.join(temp_dir, "recovered.json")
            with mock.patch.object(
                unity_puer_exec.direct_exec_client,
                "invoke_command",
                return_value=(0, json.dumps(completed_body), ""),
            ) as invoke_command:
                exit_code, stdout, stderr = unity_puer_exec.run_cli([
                    "wait-for-exec",
                    "--base-url", "http://127.0.0.1:55231",
                    "--request-id", "R-recover",
                    "--response-file", dest,
                ])

            self.assertEqual(exit_code, 0)
            self.assertEqual(invoke_command.call_count, 1)
            self.assertEqual(invoke_command.call_args.args[0], "wait-for-exec")
            ref = json.loads(stdout)
            self.assertEqual(ref["request_id"], "R-recover")
            self.assertIn("response_file", ref)
            with open(dest, "r", encoding="utf-8") as handle:
                full = json.load(handle)
            self.assertEqual(full["result"], {"done": True})

    def test_exec_structured_stderr_failure_preserves_exit_code_and_stream(self):
        failure_body = {
            "ok": False,
            "status": "failed",
            "operation": "exec",
            "request_id": "R-fail",
            "error": "boom",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = os.path.join(temp_dir, "failure.json")
            with mock.patch.object(
                unity_puer_exec.direct_exec_client,
                "invoke_command",
                return_value=(1, "", json.dumps(failure_body)),
            ):
                exit_code, stdout, stderr = unity_puer_exec.run_cli([
                    "exec",
                    "--base-url", "http://127.0.0.1:55231",
                    "--code", "export default function run(ctx) { return 1; }",
                    "--request-id", "R-fail",
                    "--response-file", dest,
                ])

            self.assertEqual(exit_code, 1)
            self.assertEqual(stdout, "")
            ref = json.loads(stderr)
            self.assertEqual(ref["status"], "failed")
            self.assertEqual(ref["request_id"], "R-fail")
            self.assertIn("response_file", ref)
            with open(dest, "r", encoding="utf-8") as handle:
                full = json.load(handle)
            self.assertEqual(full["error"], "boom")


if __name__ == "__main__":
    unittest.main()
