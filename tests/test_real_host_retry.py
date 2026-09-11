import unittest
from pathlib import Path

from tests.real_host_retry import (
    is_transient_cold_launch_failure,
    record_retry_metadata,
    warm_up_with_retry,
    DEFAULT_MAX_ATTEMPTS,
)


class TestRealHostRetryClassification(unittest.TestCase):
    """Verify task 1.1: Classify transient cold-launch failure vs persistent or non-launch failure."""

    def test_transient_failure_status_classified_as_transient(self):
        self.assertTrue(
            is_transient_cold_launch_failure(
                exit_code=20,
                payload={"status": "unity_start_failed", "error": "Unity could not be launched"},
            )
        )

    def test_unity_exited_before_ready_error_classified_as_transient(self):
        self.assertTrue(
            is_transient_cold_launch_failure(
                exit_code=20,
                payload={"status": "unity_start_failed", "error": "Unity exited before ready with code 0"},
            )
        )
        self.assertTrue(
            is_transient_cold_launch_failure(
                exit_code=1,
                payload={"error": "Unity exited before ready with code 1"},
            )
        )
        self.assertTrue(
            is_transient_cold_launch_failure(
                exit_code=1,
                payload=None,
                stderr="Unity exited before ready with code 0",
            )
        )

    def test_success_never_classified_as_transient(self):
        self.assertFalse(
            is_transient_cold_launch_failure(
                exit_code=0,
                payload={"status": "completed", "result": {"probe": "warmup"}},
            )
        )

    def test_non_launch_failures_never_classified_as_transient(self):
        non_launch_cases = [
            (4, {"status": "compile_error", "error": "CS0246: The type or namespace could not be found"}),
            (2, {"status": "syntax_error", "error": "SyntaxError: unexpected token"}),
            (10, {"status": "modal_blocked", "error": "Editor modal blocker active"}),
            (11, {"status": "busy", "error": "Unity is busy executing another request"}),
            (1, {"status": "failed", "error": "ReferenceError: puer is not defined"}),
            (1, {"status": "unknown_command", "error": "unrecognized command"}),
        ]
        for exit_code, payload in non_launch_cases:
            with self.subTest(status=payload["status"]):
                self.assertFalse(
                    is_transient_cold_launch_failure(exit_code=exit_code, payload=payload),
                    msg=f"status {payload['status']} should not be classified as a transient launch failure",
                )


class TestRealHostBoundedRetry(unittest.TestCase):
    """Verify task 1.2, 2.1, and 2.2: Bounded retry, metadata recording, and guardrails."""

    def setUp(self):
        self.dummy_project = Path("dummy/project")
        self.dummy_exe = Path("dummy/Unity.exe")

    def test_success_on_first_attempt_does_not_retry(self):
        calls = []
        boundaries = []

        def warm_up(project_path, unity_exe_path, include_diagnostics=False):
            calls.append(len(calls) + 1)
            return 0, {"ok": True, "status": "completed", "result": {"probe": "warmup"}}, "", ""

        def ensure_boundary(project_path):
            boundaries.append(len(boundaries) + 1)
            return {"ok": True, "status": "stopped", "attempts": 1}

        exit_code, payload, stdout, stderr = warm_up_with_retry(
            warm_up_fn=warm_up,
            project_path=self.dummy_project,
            unity_exe_path=self.dummy_exe,
            ensure_clean_boundary_fn=ensure_boundary,
            max_attempts=3,
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(boundaries), 1)
        self.assertEqual(payload["attempt_count"], 1)
        self.assertEqual(payload["last_launch_status"], "completed")
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(len(payload["attempts"]), 1)
        self.assertEqual(payload["attempts"][0]["status"], "completed")

    def test_transient_failure_retries_and_succeeds_recording_observability(self):
        """Verify flake recovery: attempt 1 fails transiently, boundary re-confirmed, attempt 2 succeeds."""
        calls = []
        boundaries = []

        def warm_up(project_path, unity_exe_path, include_diagnostics=False):
            attempt_num = len(calls) + 1
            calls.append(attempt_num)
            if attempt_num == 1:
                return (
                    20,
                    {
                        "ok": False,
                        "status": "unity_start_failed",
                        "error": "Unity exited before ready with code 0",
                    },
                    "",
                    "",
                )
            return 0, {"ok": True, "status": "completed", "result": {"probe": "warmup"}}, "", ""

        def ensure_boundary(project_path):
            count = len(boundaries) + 1
            boundaries.append(count)
            return {"ok": True, "status": "stopped", "boundary_attempt": count}

        exit_code, payload, stdout, stderr = warm_up_with_retry(
            warm_up_fn=warm_up,
            project_path=self.dummy_project,
            unity_exe_path=self.dummy_exe,
            ensure_clean_boundary_fn=ensure_boundary,
            max_attempts=3,
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(calls), 2, "should have retried exactly once after transient failure")
        self.assertEqual(len(boundaries), 2, "should re-confirm clean boundary before attempt 2")
        self.assertEqual(payload["attempt_count"], 2)
        self.assertEqual(payload["last_launch_status"], "completed")
        self.assertEqual(len(payload["attempts"]), 2)
        self.assertEqual(payload["attempts"][0]["status"], "unity_start_failed")
        self.assertEqual(payload["attempts"][0]["error"], "Unity exited before ready with code 0")
        self.assertEqual(payload["attempts"][1]["status"], "completed")
        self.assertIsNotNone(payload["boundary_result"])

    def test_persistent_failure_distinguishable_from_transient_flake(self):
        """Verify task 2.1: When every launch attempt fails, all attempts are recorded without masking."""
        calls = []
        boundaries = []

        def warm_up(project_path, unity_exe_path, include_diagnostics=False):
            attempt_num = len(calls) + 1
            calls.append(attempt_num)
            return (
                20,
                {
                    "ok": False,
                    "status": "unity_start_failed",
                    "error": f"Unity exited before ready on attempt {attempt_num}",
                },
                "",
                "",
            )

        def ensure_boundary(project_path):
            count = len(boundaries) + 1
            boundaries.append(count)
            return {"ok": True, "status": "stopped", "boundary_attempt": count}

        exit_code, payload, stdout, stderr = warm_up_with_retry(
            warm_up_fn=warm_up,
            project_path=self.dummy_project,
            unity_exe_path=self.dummy_exe,
            ensure_clean_boundary_fn=ensure_boundary,
            max_attempts=3,
        )

        self.assertEqual(exit_code, 20)
        self.assertEqual(len(calls), 3, "should have attempted exactly max_attempts (3)")
        self.assertEqual(len(boundaries), 3, "should have re-confirmed boundary before each attempt")
        self.assertEqual(payload["attempt_count"], 3)
        self.assertEqual(payload["last_launch_status"], "unity_start_failed")
        self.assertEqual(len(payload["attempts"]), 3)
        for i, entry in enumerate(payload["attempts"]):
            self.assertEqual(entry["attempt"], i + 1)
            self.assertEqual(entry["status"], "unity_start_failed")

    def test_non_launch_failures_never_retried(self):
        """Verify task 2.2: Non-launch failures (compile_error, syntax_error, etc.) stop on attempt 1."""
        for error_status, exit_val in [("compile_error", 4), ("syntax_error", 2), ("failed", 1), ("modal_blocked", 10)]:
            with self.subTest(status=error_status):
                calls = []
                boundaries = []

                def warm_up(project_path, unity_exe_path, include_diagnostics=False):
                    calls.append(len(calls) + 1)
                    return exit_val, {"ok": False, "status": error_status, "error": f"{error_status} occurred"}, "", ""

                def ensure_boundary(project_path):
                    boundaries.append(len(boundaries) + 1)
                    return {"ok": True, "status": "stopped"}

                exit_code, payload, stdout, stderr = warm_up_with_retry(
                    warm_up_fn=warm_up,
                    project_path=self.dummy_project,
                    unity_exe_path=self.dummy_exe,
                    ensure_clean_boundary_fn=ensure_boundary,
                    max_attempts=3,
                )

                self.assertEqual(exit_code, exit_val)
                self.assertEqual(len(calls), 1, f"{error_status} must NOT be retried")
                self.assertEqual(payload["attempt_count"], 1)
                self.assertEqual(payload["last_launch_status"], error_status)
                self.assertEqual(len(payload["attempts"]), 1)

    def test_editor_already_ready_skips_clean_boundary(self):
        """Repeat warmup when Editor is already ready must NOT kill the Editor."""
        boundaries = []

        def warm_up(project_path, unity_exe_path, include_diagnostics=False):
            return 0, {"ok": True, "status": "completed", "result": {"probe": "warmup"}}, "", ""

        def ensure_boundary(project_path):
            boundaries.append(1)
            return {"ok": True}

        def is_ready(project_path):
            return True

        exit_code, payload, stdout, stderr = warm_up_with_retry(
            warm_up_fn=warm_up,
            project_path=self.dummy_project,
            unity_exe_path=self.dummy_exe,
            ensure_clean_boundary_fn=ensure_boundary,
            is_editor_ready_fn=is_ready,
            max_attempts=3,
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(boundaries), 0, "must not wipe boundary when editor is already ready")
        self.assertEqual(payload["attempt_count"], 1)


if __name__ == "__main__":
    unittest.main()
