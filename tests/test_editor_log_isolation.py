"""Coverage for editor-log-isolation.

The product used to locate the Unity Editor log by guessing a platform path, which
is the wrong file whenever a second Editor is open -- the normal state of a
development machine. These tests pin the three halves of the fix: the bridge
states its own log path, the CLI ranks that statement above the guess, and an
Editor the CLI launches gets a log no other Editor can share.
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
CLI_DIR = REPO_ROOT / "cli" / "python"
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))

import help_surface  # type: ignore
import unity_puer_exec_runtime  # type: ignore
import unity_session  # type: ignore
import unity_session_logs  # type: ignore
import unity_session_process  # type: ignore


EDITOR_SOURCE_DIR = REPO_ROOT / "packages" / "com.txcombo.unity-puer-exec" / "Editor"

ARTIFACT_PATH = "X:/artifact/Editor.log"
EXPLICIT_PATH = "X:/explicit/Editor.log"
REPORTED_PATH = "X:/reported/Editor.log"
DEFAULT_PATH = "X:/default/Editor.log"


def _resolve(artifact=None, explicit=None, reported=None):
    """Resolve with every dependency injected, so only precedence is under test."""
    return unity_session_logs.resolve_effective_log_path_with_tier(
        "X:/unity-project",
        unity_log_path=explicit,
        session_data={},
        health_console_log_path=reported,
        session_artifact_log_path_fn=lambda _session_data: Path(artifact) if artifact else None,
        default_editor_log_path_fn=lambda: Path(DEFAULT_PATH),
    )


class BridgeConsoleLogPathContractTests(unittest.TestCase):
    """The Editor half's side of the contract, asserted on source."""

    def test_health_response_emits_console_log_path(self):
        protocol = (EDITOR_SOURCE_DIR / "UnityPuerExecProtocol.cs").read_text(encoding="utf-8")
        self.assertIn('\\"console_log_path\\":', protocol)
        self.assertIn("string consoleLogPath", protocol)

    def test_console_log_path_is_omitted_rather_than_guessed_when_unresolvable(self):
        protocol = (EDITOR_SOURCE_DIR / "UnityPuerExecProtocol.cs").read_text(encoding="utf-8")
        self.assertIn('string.IsNullOrEmpty(consoleLogPath)', protocol)
        # The empty case contributes an empty fragment, so the rest of the ready
        # payload stays well-formed instead of carrying a platform-default guess.
        self.assertIn('var consoleLogPathJson = string.IsNullOrEmpty(consoleLogPath)\n                    ? ""', protocol)

    def test_health_reports_the_editors_own_cached_console_log_path(self):
        server = (EDITOR_SOURCE_DIR / "UnityPuerExecServer.cs").read_text(encoding="utf-8")
        self.assertIn("consoleLogPath: cachedConsoleLogPath", server)
        # The cache is filled from the running Editor's own runtime, not a convention.
        self.assertIn("Application.consoleLogPath", server)


class LogPathPrecedenceTests(unittest.TestCase):
    def test_session_artifact_outranks_every_other_tier(self):
        path, tier = _resolve(artifact=ARTIFACT_PATH, explicit=EXPLICIT_PATH, reported=REPORTED_PATH)
        self.assertEqual(path, Path(ARTIFACT_PATH))
        self.assertEqual(tier, unity_session_logs.LOG_SOURCE_TIER_SESSION_ARTIFACT)

    def test_explicit_flag_outranks_the_reported_path(self):
        path, tier = _resolve(explicit=EXPLICIT_PATH, reported=REPORTED_PATH)
        self.assertEqual(path, Path(EXPLICIT_PATH))
        self.assertEqual(tier, unity_session_logs.LOG_SOURCE_TIER_EXPLICIT_FLAG)

    def test_reported_path_outranks_the_platform_default(self):
        path, tier = _resolve(reported=REPORTED_PATH)
        self.assertEqual(path, Path(REPORTED_PATH))
        self.assertEqual(tier, unity_session_logs.LOG_SOURCE_TIER_CONTROL_SERVICE)

    def test_platform_default_is_the_last_resort(self):
        path, tier = _resolve()
        self.assertEqual(path, Path(DEFAULT_PATH))
        self.assertEqual(tier, unity_session_logs.LOG_SOURCE_TIER_PLATFORM_DEFAULT)

    def test_unreachable_control_service_falls_through_to_the_default(self):
        # An unreachable service reports nothing, which must degrade to the guess
        # rather than fail: locating a log is not allowed to depend on reachability.
        path, tier = _resolve(reported=None)
        self.assertEqual(path, Path(DEFAULT_PATH))
        self.assertEqual(tier, unity_session_logs.LOG_SOURCE_TIER_PLATFORM_DEFAULT)

    def test_session_artifact_still_wins_when_the_control_service_is_unreachable(self):
        path, tier = _resolve(artifact=ARTIFACT_PATH, reported=None)
        self.assertEqual(path, Path(ARTIFACT_PATH))
        self.assertEqual(tier, unity_session_logs.LOG_SOURCE_TIER_SESSION_ARTIFACT)

    def test_health_console_log_path_reads_only_a_non_empty_string(self):
        self.assertEqual(unity_session_logs.health_console_log_path({"console_log_path": REPORTED_PATH}), REPORTED_PATH)
        self.assertIsNone(unity_session_logs.health_console_log_path({"console_log_path": ""}))
        self.assertIsNone(unity_session_logs.health_console_log_path({}))
        self.assertIsNone(unity_session_logs.health_console_log_path(None))


class GetLogSourceTierReportingTests(unittest.TestCase):
    def test_explicit_path_is_reported_as_the_explicit_tier(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session, result = unity_session.get_log_source(
                project_path=Path(temp_dir),
                unity_log_path=EXPLICIT_PATH,
            )

        self.assertEqual(result["path"], str(Path(EXPLICIT_PATH)))
        self.assertEqual(result["resolution_tier"], unity_session_logs.LOG_SOURCE_TIER_EXPLICIT_FLAG)
        self.assertEqual(Path(session.effective_log_path), Path(EXPLICIT_PATH))

    def test_artifact_path_is_reported_as_the_artifact_tier(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            unity_session.write_session_artifact(
                project_path,
                {
                    "base_url": "http://127.0.0.1:55231",
                    "unity_pid": 1234,
                    "session_marker": "marker-1",
                    "effective_log_path": ARTIFACT_PATH,
                },
            )
            with mock.patch.object(unity_session, "_is_pid_running", return_value=True):
                session, result = unity_session.get_log_source(project_path=project_path)

        self.assertEqual(result["resolution_tier"], unity_session_logs.LOG_SOURCE_TIER_SESSION_ARTIFACT)

    def test_reported_path_is_distinguishable_from_the_platform_default(self):
        ready = {"ok": True, "status": "ready", "project_path": None, "console_log_path": REPORTED_PATH}
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            ready["project_path"] = str(project_path)
            with mock.patch.object(unity_session, "_probe_health", return_value=(ready, None)):
                session, result = unity_session.get_log_source(project_path=project_path)

        self.assertEqual(result["path"], str(Path(REPORTED_PATH)))
        self.assertEqual(result["resolution_tier"], unity_session_logs.LOG_SOURCE_TIER_CONTROL_SERVICE)

    def test_an_endpoint_owned_by_another_project_is_never_adopted(self):
        # Adopting a foreign Editor's log path would name the wrong file, which is
        # precisely the defect this capability exists to remove.
        foreign = {"ok": True, "status": "ready", "project_path": "X:/some-other-project", "console_log_path": REPORTED_PATH}
        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch.object(unity_session, "_probe_health", return_value=(foreign, None)):
                result = unity_session.get_log_source(project_path=Path(temp_dir))

        # Falls through to the platform default, which does not exist under the
        # temp project, so there is no observation target rather than a wrong one.
        if result is not None:
            self.assertEqual(result[1]["resolution_tier"], unity_session_logs.LOG_SOURCE_TIER_PLATFORM_DEFAULT)


class ProjectPrivateLaunchLogTests(unittest.TestCase):
    def test_default_launch_log_is_project_local_and_not_the_per_user_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            resolved = unity_session_logs.prepare_launch_log_path(project_path)

        self.assertEqual(resolved, project_path / "Temp" / "UnityPuerExec" / "Editor.log")
        self.assertNotEqual(resolved, unity_session_logs.default_editor_log_path())

    def test_launch_log_directory_is_created_before_launch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            resolved = unity_session_logs.prepare_launch_log_path(project_path)
            self.assertTrue(resolved.parent.is_dir())

    def test_an_uncreatable_directory_does_not_fail_the_launch(self):
        resolved = unity_session_logs.prepare_launch_log_path("X:/no-such-drive/project")
        self.assertEqual(resolved, Path("X:/no-such-drive/project/Temp/UnityPuerExec/Editor.log"))

    def test_explicit_path_overrides_the_project_private_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            resolved = unity_session_logs.prepare_launch_log_path(Path(temp_dir), unity_log_path=EXPLICIT_PATH)

        self.assertEqual(resolved, Path(EXPLICIT_PATH))

    def test_launch_argv_carries_log_file_with_a_project_local_path_by_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            log_path = unity_session_logs.prepare_launch_log_path(project_path)
            with mock.patch.object(unity_session_process.subprocess, "Popen") as popen:
                unity_session_process.launch_unity(project_path, "X:/Unity/Unity.exe", unity_log_path=log_path)

        args = popen.call_args.args[0]
        self.assertIn("-logFile", args)
        self.assertEqual(args[args.index("-logFile") + 1], str(project_path / "Temp" / "UnityPuerExec" / "Editor.log"))

    def test_launch_argv_carries_the_caller_supplied_path_when_one_is_given(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            log_path = unity_session_logs.prepare_launch_log_path(project_path, unity_log_path=EXPLICIT_PATH)
            with mock.patch.object(unity_session_process.subprocess, "Popen") as popen:
                unity_session_process.launch_unity(project_path, "X:/Unity/Unity.exe", unity_log_path=log_path)

        args = popen.call_args.args[0]
        self.assertEqual(args[args.index("-logFile") + 1], str(Path(EXPLICIT_PATH)))


class InvalidatedOffsetReportingTests(unittest.TestCase):
    def _log_file(self, temp_dir, size):
        path = Path(temp_dir) / "Editor.log"
        path.write_bytes(b"x" * size)
        return path

    def test_offset_beyond_end_of_file_is_surfaced_and_names_the_log(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = self._log_file(temp_dir, 100)
            detail = unity_puer_exec_runtime._detect_offset_invalidation(log_path, 500)

        self.assertIsNotNone(detail)
        self.assertEqual(detail["log_path"], str(log_path))
        self.assertEqual(detail["supplied_start"], 500)
        self.assertEqual(detail["observed_end"], 100)
        self.assertEqual(detail["reason"], "log_rotated_or_truncated")

    def test_an_observation_with_no_offset_cannot_trip_the_signal(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = self._log_file(temp_dir, 100)
            self.assertIsNone(unity_puer_exec_runtime._detect_offset_invalidation(log_path, None))

    def test_a_normal_offset_inside_the_file_reports_nothing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = self._log_file(temp_dir, 100)
            self.assertIsNone(unity_puer_exec_runtime._detect_offset_invalidation(log_path, 40))
            # End-of-file exactly is the ordinary "resume where I stopped" case.
            self.assertIsNone(unity_puer_exec_runtime._detect_offset_invalidation(log_path, 100))

    def test_a_missing_log_reports_nothing_rather_than_a_false_invalidation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "absent.log"
            self.assertIsNone(unity_puer_exec_runtime._detect_offset_invalidation(missing, 500))

    def test_reading_still_proceeds_when_offsets_are_invalidated(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = self._log_file(temp_dir, 100)
            end, chunk = unity_session_logs.read_editor_log_chunk(log_path, 500)

        self.assertEqual(end, 100)
        self.assertEqual(len(chunk), 100)

    def test_the_indication_travels_next_to_log_range_in_the_response(self):
        container = {}
        detail = {"log_path": "X:/log/Editor.log", "reason": "log_rotated_or_truncated"}
        with mock.patch.object(unity_puer_exec_runtime.unity_log_brief, "parse_log_briefs", return_value=[]):
            unity_puer_exec_runtime._apply_log_range_and_brief_sequence(
                container,
                "X:/log/Editor.log",
                500,
                100,
                offsets_invalidated=detail,
            )

        self.assertEqual(container["log_range"], {"start": 500, "end": 100})
        self.assertEqual(container["log_offsets_invalidated"], detail)

    def test_nothing_is_added_when_offsets_are_valid(self):
        container = {}
        with mock.patch.object(unity_puer_exec_runtime.unity_log_brief, "parse_log_briefs", return_value=[]):
            unity_puer_exec_runtime._apply_log_range_and_brief_sequence(container, "X:/log/Editor.log", 0, 100)

        self.assertNotIn("log_offsets_invalidated", container)


class OffsetInvalidationGuidanceTests(unittest.TestCase):
    def test_offset_taking_commands_explain_what_invalidated_the_offsets(self):
        for command in help_surface.LOG_OFFSET_AWARE_COMMANDS:
            blob = help_surface.render_command_status_help(command)
            self.assertIn("log_offsets_invalidated", blob, command)
            self.assertIn("rotated or truncated", blob, command)
            self.assertIn("get-log-source", blob, command)

    def test_commands_without_a_caller_offset_do_not_carry_the_section(self):
        self.assertNotIn("log_offsets_invalidated", help_surface.render_command_status_help("get-blocker-state"))

    def test_get_log_source_help_explains_every_resolution_tier(self):
        blob = help_surface.render_command_args_help("get-log-source")
        for tier in (
            unity_session_logs.LOG_SOURCE_TIER_SESSION_ARTIFACT,
            unity_session_logs.LOG_SOURCE_TIER_EXPLICIT_FLAG,
            unity_session_logs.LOG_SOURCE_TIER_CONTROL_SERVICE,
            unity_session_logs.LOG_SOURCE_TIER_PLATFORM_DEFAULT,
        ):
            self.assertIn(tier, blob)


if __name__ == "__main__":
    unittest.main()
