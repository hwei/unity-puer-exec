import json
import os
import sys
import unittest
from unittest import mock


SKILL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if SKILL_DIR not in sys.path:
    sys.path.insert(0, SKILL_DIR)

import unity_session  # type: ignore
import unity_session_cli  # type: ignore


SAMPLE_PROJECT_PATH = "X:/unity-project"


def _make_session():
    session = unity_session.UnitySession(
        owner="launched",
        base_url="http://127.0.0.1:55231",
        project_path=SAMPLE_PROJECT_PATH,
        unity_pid=1234,
        launched=True,
    )
    session.diagnostics = {"phase": "test"}
    return session


class UnitySessionCliTests(unittest.TestCase):
    def test_project_path_argument_defaults_to_none(self):
        parser = unity_session_cli._build_parser()
        args = parser.parse_args(["ensure-ready"])
        self.assertIsNone(args.project_path)

    def test_ensure_ready_prefers_explicit_project_path(self):
        with mock.patch.dict(os.environ, {unity_session.UNITY_PROJECT_PATH_ENV: "X:/from-env"}, clear=False), mock.patch.object(
            unity_session, "ensure_session_ready", return_value=_make_session()
        ) as ensure_session_ready:
            unity_session_cli.run_cli(["ensure-ready", "--project-path", "X:/from-arg"])

        self.assertEqual(ensure_session_ready.call_args.kwargs["project_path"], "X:/from-arg")

    def test_ensure_ready_leaves_project_path_unset_for_runtime_resolution(self):
        with mock.patch.dict(os.environ, {unity_session.UNITY_PROJECT_PATH_ENV: "X:/from-env"}, clear=False), mock.patch.object(
            unity_session, "ensure_session_ready", return_value=_make_session()
        ) as ensure_session_ready:
            unity_session_cli.run_cli(["ensure-ready"])

        self.assertIsNone(ensure_session_ready.call_args.kwargs["project_path"])

    def test_ensure_ready_returns_success_payload(self):
        session = _make_session()

        with mock.patch.object(unity_session, "ensure_session_ready", return_value=session), mock.patch.object(
            unity_session, "close_session", return_value={"attempted": True, "closed": True, "kept": False}
        ):
            exit_code, stdout, stderr = unity_session_cli.run_cli(["ensure-ready"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["operation"], "ensure-ready")
        self.assertEqual(payload["result"]["status"], "ready")
        self.assertEqual(payload["session"]["unity_pid"], 1234)
        self.assertEqual(payload["cleanup"]["closed"], True)

    def test_wait_until_recovered_returns_success_payload(self):
        session = _make_session()
        session.diagnostics["recovery_observed"] = True

        with mock.patch.object(unity_session, "ensure_session_ready", return_value=session), mock.patch.object(
            unity_session, "wait_until_recovered", return_value=session
        ), mock.patch.object(
            unity_session, "close_session", return_value={"attempted": True, "closed": True, "kept": False}
        ):
            exit_code, stdout, stderr = unity_session_cli.run_cli(["wait-until-recovered", "--timeout-seconds", "5"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["operation"], "wait-until-recovered")
        self.assertEqual(payload["result"]["status"], "recovered")
        self.assertEqual(payload["result"]["diagnostics"]["recovery_observed"], True)

    def test_wait_for_log_pattern_returns_success_payload(self):
        session = _make_session()
        session.diagnostics["matched_log_text"] = "[Build] complete"

        with mock.patch.object(unity_session, "ensure_session_ready", return_value=session), mock.patch.object(
            unity_session, "wait_for_log_pattern", return_value=session
        ), mock.patch.object(
            unity_session, "close_session", return_value={"attempted": True, "closed": True, "kept": False}
        ):
            exit_code, stdout, stderr = unity_session_cli.run_cli(
                ["wait-for-log-pattern", "--pattern", r"\[Build\] complete", "--timeout-seconds", "5"]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["operation"], "wait-for-log-pattern")
        self.assertEqual(payload["result"]["status"], "log_pattern_matched")
        self.assertEqual(payload["result"]["diagnostics"]["matched_log_text"], "[Build] complete")

    def test_launch_error_maps_to_exit_code_20(self):
        session = _make_session()
        error = unity_session.UnityLaunchError("failed to launch", session=session)

        with mock.patch.object(unity_session, "ensure_session_ready", side_effect=error), mock.patch.object(
            unity_session, "close_session", return_value={"attempted": True, "closed": True, "kept": False}
        ):
            exit_code, stdout, stderr = unity_session_cli.run_cli(["ensure-ready"])

        self.assertEqual(exit_code, unity_session_cli.EXIT_UNITY_START_FAILED)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["status"], "unity_start_failed")
        self.assertEqual(payload["session"]["unity_pid"], 1234)

    def test_stalled_error_maps_to_exit_code_21(self):
        session = _make_session()
        error = unity_session.UnityStalledError("stalled", session=session)

        with mock.patch.object(unity_session, "ensure_session_ready", side_effect=error), mock.patch.object(
            unity_session, "close_session", return_value={"attempted": True, "closed": True, "kept": False}
        ):
            exit_code, stdout, stderr = unity_session_cli.run_cli(["ensure-ready"])

        self.assertEqual(exit_code, unity_session_cli.EXIT_UNITY_NOT_READY)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["status"], "unity_stalled")

    def test_not_ready_error_maps_to_exit_code_21(self):
        session = _make_session()
        error = unity_session.UnityNotReadyError("not ready", session=session)

        with mock.patch.object(unity_session, "ensure_session_ready", side_effect=error), mock.patch.object(
            unity_session, "close_session", return_value={"attempted": True, "closed": True, "kept": False}
        ):
            exit_code, stdout, stderr = unity_session_cli.run_cli(["ensure-ready"])

        self.assertEqual(exit_code, unity_session_cli.EXIT_UNITY_NOT_READY)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["status"], "unity_not_ready")


if __name__ == "__main__":
    unittest.main()
