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

import cli_version  # type: ignore
import direct_exec_client  # type: ignore
import help_surface  # type: ignore
import unity_puer_exec  # type: ignore
import unity_puer_exec_runtime as runtime  # type: ignore
import unity_puer_exec_surface as surface  # type: ignore
import unity_session  # type: ignore
import unity_session_endpoint  # type: ignore

from tests import version_test_support


PACKAGE_VERSION = json.loads(
    (REPO_ROOT / "packages" / "com.txcombo.unity-puer-exec" / "package.json").read_text(encoding="utf-8")
)["version"]


def _write_package_tree(root, version, exe_name="unity-puer-exec.exe"):
    """Build a `<package>/CLI~/<exe>` layout with a package.json declaring `version`."""
    package_root = Path(root)
    package_root.mkdir(parents=True, exist_ok=True)
    (package_root / "package.json").write_text(
        json.dumps({"name": cli_version.PACKAGE_ID, "version": version}),
        encoding="utf-8",
    )
    cli_dir = package_root / "CLI~"
    cli_dir.mkdir(exist_ok=True)
    exe_path = cli_dir / exe_name
    exe_path.write_bytes(b"")
    return package_root, exe_path


class _NetworkTripwire:
    """Fail loudly if anything reaches the network while it is installed."""

    def __init__(self, test_case):
        self.test_case = test_case

    def __enter__(self):
        def explode(*_args, **_kwargs):
            self.test_case.fail("guard performed network activity")

        self._patch = mock.patch.object(direct_exec_client.HttpTransport, "post_json", explode)
        self._patch.start()
        return self

    def __exit__(self, *_exc):
        self._patch.stop()
        return False


class CliVersionResolutionTests(unittest.TestCase):
    def test_source_invocation_resolves_source_tree_package_version(self):
        with mock.patch.object(cli_version, "is_frozen", return_value=False):
            self.assertEqual(cli_version.resolve_cli_version(), PACKAGE_VERSION)

    def test_frozen_build_resolves_its_stamped_version(self):
        with mock.patch.object(cli_version, "is_frozen", return_value=True), mock.patch.object(
            cli_version, "stamped_version", return_value="9.9.9"
        ):
            self.assertEqual(cli_version.resolve_cli_version(), "9.9.9")

    def test_frozen_build_without_stamp_does_not_read_a_package_json(self):
        source_lookup = mock.Mock(return_value=PACKAGE_VERSION)
        with mock.patch.object(cli_version, "is_frozen", return_value=True), mock.patch.object(
            cli_version, "stamped_version", return_value=None
        ), mock.patch.object(cli_version, "source_tree_version", source_lookup):
            self.assertIsNone(cli_version.resolve_cli_version())
        source_lookup.assert_not_called()

    def test_exit_code_24_is_reserved_and_distinct(self):
        self.assertEqual(direct_exec_client.EXIT_VERSION_MISMATCH, 24)
        for other in (
            1,
            direct_exec_client.EXIT_NOT_AVAILABLE,
            runtime.EXIT_UNITY_NOT_READY,
        ):
            self.assertNotEqual(direct_exec_client.EXIT_VERSION_MISMATCH, other)

    def test_version_mismatch_status_maps_to_exit_24(self):
        self.assertEqual(
            direct_exec_client._status_to_exit_code({"ok": False, "status": "version_mismatch"}),
            24,
        )


class VersionEntryTests(unittest.TestCase):
    def test_bare_version_query_reports_the_version_without_a_command(self):
        exit_code, stdout, stderr = unity_puer_exec.run_cli(["--version"])
        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn(PACKAGE_VERSION, stdout)

    def test_version_query_contacts_no_service(self):
        with _NetworkTripwire(self):
            exit_code, _stdout, _stderr = unity_puer_exec.run_cli(["--version"])
        self.assertEqual(exit_code, 0)

    def test_top_level_help_documents_the_version_entry(self):
        text = help_surface.render_top_level_help()
        self.assertIn("`--version`", text)

    def test_unstamped_frozen_build_reports_unknown_rather_than_refusing(self):
        with mock.patch.object(cli_version, "is_frozen", return_value=True), mock.patch.object(
            cli_version, "stamped_version", return_value=None
        ):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(["--version"])
        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn(cli_version.UNKNOWN_VERSION_TEXT, stdout)

    def test_help_entries_answer_on_an_installation_that_fails_a_guard(self):
        with mock.patch.object(cli_version, "is_frozen", return_value=True), mock.patch.object(
            cli_version, "stamped_version", return_value=None
        ):
            for argv in (["--help"], ["exec", "--help"], ["exec", "--help-args"], ["exec", "--help-status"]):
                exit_code, stdout, stderr = unity_puer_exec.run_cli(argv)
                self.assertEqual(exit_code, 0, argv)
                self.assertEqual(stderr, "", argv)
                self.assertTrue(stdout.strip(), argv)


class PackageLayoutGuardTests(unittest.TestCase):
    def test_matching_versions_pass(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _root, exe = _write_package_tree(Path(temp_dir) / "com.txcombo.unity-puer-exec", "0.7.0")
            with _NetworkTripwire(self):
                self.assertIsNone(cli_version.check_package_layout("0.7.0", exe_path=exe))

    def test_disagreeing_versions_report_a_package_layout_mismatch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root, exe = _write_package_tree(Path(temp_dir) / "com.txcombo.unity-puer-exec", "0.7.0")
            with _NetworkTripwire(self):
                detail = cli_version.check_package_layout("0.6.0", exe_path=exe)
        self.assertIsNotNone(detail)
        self.assertEqual(detail["guard"], cli_version.GUARD_PACKAGE_LAYOUT)
        self.assertEqual(detail["cli_version"], "0.6.0")
        self.assertEqual(detail["observed_version"], "0.7.0")
        self.assertEqual(detail["observed_location"], str(root))

    def test_executable_outside_a_package_tree_skips_the_guard(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            exe = Path(temp_dir) / "standalone" / "unity-puer-exec.exe"
            exe.parent.mkdir(parents=True)
            exe.write_bytes(b"")
            with _NetworkTripwire(self):
                self.assertIsNone(cli_version.check_package_layout("0.6.0", exe_path=exe))

    def test_originating_incident_layout_is_caught(self):
        """A v0.6.0 exe left in CLI~/ beside a package.json declaring 0.7.0.

        This is the configuration that produced the 2026-07-23 misattributed
        feedback: the two runtime halves agreed with each other, so only this
        guard can see the staleness.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            root, exe = _write_package_tree(Path(temp_dir) / "com.txcombo.unity-puer-exec", "0.7.0")
            self.assertEqual(exe.parent.name, "CLI~")
            detail = cli_version.check_package_layout("0.6.0", exe_path=exe)
        self.assertIsNotNone(detail)
        self.assertEqual(detail["guard"], cli_version.GUARD_PACKAGE_LAYOUT)
        self.assertEqual(detail["observed_version"], "0.7.0")
        self.assertIn(str(root), detail["observed_location"])

    def test_guard_refuses_command_work_end_to_end(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _root, exe = _write_package_tree(Path(temp_dir) / "com.txcombo.unity-puer-exec", "0.7.0")
            with mock.patch.object(cli_version, "resolve_cli_version", return_value="0.6.0"), mock.patch.object(
                cli_version, "executable_path", return_value=exe
            ), mock.patch.object(direct_exec_client, "invoke_command") as invoke:
                exit_code, stdout, stderr = unity_puer_exec.run_cli([
                    "exec",
                    "--base-url", "http://127.0.0.1:55231",
                    "--code", "export default function run() { return 1; }",
                ])
        self.assertEqual(exit_code, 24)
        self.assertEqual(stderr, "")
        invoke.assert_not_called()
        body = json.loads(stdout)
        self.assertEqual(body["status"], "version_mismatch")
        self.assertEqual(body["version_mismatch"]["guard"], cli_version.GUARD_PACKAGE_LAYOUT)


class BridgeGuardTests(unittest.TestCase):
    BASE_URL = "http://127.0.0.1:55231"

    def _ready(self, bridge_version):
        payload = {"ok": True, "status": "ready", "project_path": "X:/unity-project"}
        if bridge_version is not None:
            payload["bridge_version"] = bridge_version
        return payload

    def test_matching_bridge_version_passes(self):
        self.assertIsNone(
            cli_version.check_bridge("0.7.0", self.BASE_URL, self._ready("0.7.0"))
        )

    def test_differing_bridge_version_is_a_bridge_mismatch(self):
        detail = cli_version.check_bridge("0.7.0", self.BASE_URL, self._ready("0.6.0"))
        self.assertEqual(detail["guard"], cli_version.GUARD_BRIDGE)
        self.assertEqual(detail["cli_version"], "0.7.0")
        self.assertEqual(detail["observed_version"], "0.6.0")
        self.assertEqual(detail["observed_location"], self.BASE_URL)

    def test_patch_level_difference_is_a_mismatch(self):
        detail = cli_version.check_bridge("0.7.0", self.BASE_URL, self._ready("0.7.1"))
        self.assertEqual(detail["guard"], cli_version.GUARD_BRIDGE)

    def test_absent_bridge_version_is_a_mismatch_with_a_distinct_guard(self):
        detail = cli_version.check_bridge("0.7.0", self.BASE_URL, self._ready(None))
        self.assertEqual(detail["guard"], cli_version.GUARD_BRIDGE_VERSION_UNKNOWN)
        self.assertIsNone(detail["observed_version"])
        self.assertNotEqual(detail["guard"], cli_version.GUARD_BRIDGE)

    def test_pre_ready_payload_without_a_version_is_not_yet_a_mismatch(self):
        compiling = {"ok": False, "status": "compiling", "session_marker": "m"}
        self.assertIsNone(
            cli_version.check_bridge("0.7.0", self.BASE_URL, compiling, require_version=False)
        )

    def test_pre_ready_payload_that_does_carry_a_version_fires_immediately(self):
        compiling = {"ok": False, "status": "compiling", "bridge_version": "0.6.0"}
        detail = cli_version.check_bridge("0.7.0", self.BASE_URL, compiling, require_version=False)
        self.assertEqual(detail["guard"], cli_version.GUARD_BRIDGE)

    def test_owned_endpoint_check_never_runs_on_a_foreign_project(self):
        """The control-port scan walks past other projects; they must not refuse."""
        foreign = {"ok": True, "status": "ready", "project_path": "X:/other-project", "bridge_version": "0.1.0"}
        probe = mock.Mock(return_value=(foreign, None))
        with mock.patch.object(unity_session, "_probe_health", probe):
            base_url, payload, _error, saw_other = unity_session.discover_project_endpoint("X:/unity-project")
        self.assertIsNone(base_url)
        self.assertIsNone(payload)
        self.assertTrue(saw_other)

    def test_base_url_mode_refuses_before_the_command_transport_is_used(self):
        ready = self._ready("0.6.0")
        with mock.patch.object(cli_version, "resolve_cli_version", return_value="0.7.0"), mock.patch.object(
            unity_session, "probe_health_payload", return_value=(ready, None)
        ), mock.patch.object(direct_exec_client, "invoke_command") as invoke:
            exit_code, stdout, stderr = unity_puer_exec.run_cli([
                "exec",
                "--base-url", self.BASE_URL,
                "--code", "export default function run() { return 1; }",
            ])
        self.assertEqual(exit_code, 24)
        self.assertEqual(stderr, "")
        invoke.assert_not_called()
        body = json.loads(stdout)
        self.assertEqual(body["status"], "version_mismatch")
        self.assertEqual(body["version_mismatch"]["guard"], cli_version.GUARD_BRIDGE)
        self.assertEqual(body["version_mismatch"]["observed_location"], self.BASE_URL)

    def test_base_url_mode_passes_a_matched_bridge_through(self):
        ready = self._ready(version_test_support.matching_bridge_version())
        completed = {"ok": True, "status": "completed", "operation": "exec", "request_id": "R-1", "result": 1}
        with mock.patch.object(
            unity_session, "probe_health_payload", return_value=(ready, None)
        ), mock.patch.object(
            direct_exec_client, "invoke_command", return_value=(0, json.dumps(completed), "")
        ):
            exit_code, stdout, _stderr = unity_puer_exec.run_cli([
                "exec",
                "--base-url", self.BASE_URL,
                "--code", "export default function run() { return 1; }",
                "--request-id", "R-1",
            ])
        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout)["status"], "completed")

    def test_unreachable_endpoint_is_not_treated_as_a_guard_failure(self):
        """Nothing answered, so nothing disagreed; the command's own not_available wins."""
        with mock.patch.object(
            unity_session, "probe_health_payload", return_value=(None, "connection refused")
        ), mock.patch.object(
            direct_exec_client,
            "invoke_command",
            return_value=(direct_exec_client.EXIT_NOT_AVAILABLE, json.dumps({"ok": False, "status": "not_available"}), ""),
        ):
            exit_code, stdout, _stderr = unity_puer_exec.run_cli([
                "exec",
                "--base-url", self.BASE_URL,
                "--code", "export default function run() { return 1; }",
            ])
        self.assertEqual(exit_code, direct_exec_client.EXIT_NOT_AVAILABLE)
        self.assertEqual(json.loads(stdout)["status"], "not_available")

    SESSION_MARKER = "cli-version-guard-marker"

    @staticmethod
    def _publish_endpoint(project_dir, session_marker, unity_pid=4242):
        """Give the project a controlled session the way a real Editor would.

        A project-scoped command now reaches its endpoint through the Editor's own
        publication plus a held project lockfile, so a guard test has to establish
        both before the version guard is even reachable.
        """
        publication_path = Path(project_dir) / "Temp" / "UnityPuerExec" / "endpoint.json"
        publication_path.parent.mkdir(parents=True, exist_ok=True)
        publication_path.write_text(
            json.dumps(
                {
                    "port": 55231,
                    "unity_pid": unity_pid,
                    "project_path": project_dir,
                    "session_marker": session_marker,
                }
            ),
            encoding="utf-8",
        )

    def _run_project_scoped_exec(self, bridge_version):
        payload = {
            "ok": True,
            "status": "ready",
            "port": 55231,
            "base_url": self.BASE_URL,
            "session_marker": self.SESSION_MARKER,
            "unity_pid": 4242,
        }
        with tempfile.TemporaryDirectory() as project_dir:
            payload["project_path"] = project_dir
            if bridge_version is not None:
                payload["bridge_version"] = bridge_version
            self._publish_endpoint(project_dir, self.SESSION_MARKER)
            with mock.patch.object(cli_version, "resolve_cli_version", return_value="0.7.0"), mock.patch.object(
                unity_session, "_probe_health", return_value=(payload, None)
            ), mock.patch.object(
                unity_session, "_project_lockfile_is_held", return_value=True
            ), mock.patch.object(direct_exec_client, "invoke_command") as invoke:
                exit_code, stdout, stderr = unity_puer_exec.run_cli([
                    "exec",
                    "--project-path", project_dir,
                    "--code", "export default function run() { return 1; }",
                ])
        return exit_code, stdout, stderr, invoke

    def test_project_scoped_command_refuses_on_a_differing_bridge_version(self):
        exit_code, stdout, stderr, invoke = self._run_project_scoped_exec("0.6.0")
        self.assertEqual(exit_code, 24, stderr)
        invoke.assert_not_called()
        body = json.loads(stdout)
        self.assertEqual(body["status"], "version_mismatch")
        self.assertEqual(body["version_mismatch"]["guard"], cli_version.GUARD_BRIDGE)
        self.assertEqual(body["version_mismatch"]["observed_version"], "0.6.0")

    def test_project_scoped_command_refuses_when_a_ready_bridge_reports_no_version(self):
        """D5: an unversioned bridge is unverifiable, not an implicit pass."""
        exit_code, stdout, stderr, invoke = self._run_project_scoped_exec(None)
        self.assertEqual(exit_code, 24, stderr)
        invoke.assert_not_called()
        body = json.loads(stdout)
        self.assertEqual(body["version_mismatch"]["guard"], cli_version.GUARD_BRIDGE_VERSION_UNKNOWN)
        self.assertIsNone(body["version_mismatch"]["observed_version"])

    def test_project_scoped_command_proceeds_on_a_matched_bridge(self):
        completed = {"ok": True, "status": "completed", "operation": "exec", "request_id": "R-1", "result": 1}
        payload = {
            "ok": True,
            "status": "ready",
            "port": 55231,
            "base_url": self.BASE_URL,
            "bridge_version": "0.7.0",
            "session_marker": self.SESSION_MARKER,
            "unity_pid": 4242,
        }
        with tempfile.TemporaryDirectory() as project_dir:
            payload["project_path"] = project_dir
            self._publish_endpoint(project_dir, self.SESSION_MARKER)
            with mock.patch.object(cli_version, "resolve_cli_version", return_value="0.7.0"), mock.patch.object(
                unity_session, "_probe_health", return_value=(payload, None)
            ), mock.patch.object(
                unity_session, "_project_lockfile_is_held", return_value=True
            ), mock.patch.object(
                direct_exec_client, "invoke_command", return_value=(0, json.dumps(completed), "")
            ):
                exit_code, stdout, _stderr = unity_puer_exec.run_cli([
                    "exec",
                    "--project-path", project_dir,
                    "--code", "export default function run() { return 1; }",
                    "--request-id", "R-1",
                ])
        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout)["status"], "completed")

    def test_launch_path_still_gates_before_the_command_executes_anything(self):
        """A session reached through the launch/recovery path is version-gated too.

        Real-host reproduction: those paths lock onto the project's port through
        pre-`ready` payloads, so an unversioned bridge once slipped past them and a
        script executed against it.
        """
        ready = {
            "ok": True, "status": "ready", "port": 55231,
            "base_url": self.BASE_URL, "project_path": "X:/unity-project",
        }
        launched = unity_session.UnitySession(
            owner="launched", base_url=self.BASE_URL, project_path="X:/unity-project"
        )
        with mock.patch.object(cli_version, "resolve_cli_version", return_value="0.7.0"), mock.patch.object(
            unity_session, "_ensure_session_ready_unguarded", return_value=launched
        ), mock.patch.object(
            unity_session, "_probe_health", return_value=(ready, None)
        ), mock.patch.object(direct_exec_client, "invoke_command") as invoke:
            exit_code, stdout, _stderr = unity_puer_exec.run_cli([
                "exec",
                "--project-path", "X:/unity-project",
                "--code", "export default function run() { return 1; }",
            ])
        self.assertEqual(exit_code, 24)
        invoke.assert_not_called()
        self.assertEqual(
            json.loads(stdout)["version_mismatch"]["guard"],
            cli_version.GUARD_BRIDGE_VERSION_UNKNOWN,
        )

    def test_project_scoped_ready_endpoint_with_a_differing_version_refuses(self):
        mismatched = self._ready("0.6.0")
        with mock.patch.object(unity_session, "_probe_health", return_value=(mismatched, None)):
            with self.assertRaises(unity_session.UnityVersionMismatchError) as caught:
                unity_session.validate_endpoint_identity(self.BASE_URL, "X:/unity-project")
        self.assertEqual(caught.exception.detail["guard"], cli_version.GUARD_BRIDGE)


class CliVersionOnResponsesTests(unittest.TestCase):
    def _log_file(self, content):
        handle = tempfile.NamedTemporaryFile("w", suffix=".log", delete=False, encoding="utf-8")
        handle.write(content)
        handle.close()
        return handle.name

    def test_success_payload_carries_the_acting_build(self):
        path = self._log_file("First entry\n")
        try:
            size = os.path.getsize(path)
            _exit_code, stdout, _stderr = unity_puer_exec.run_cli([
                "get-log-briefs", "--unity-log-path", path, "--range", "0-{}".format(size),
            ])
        finally:
            os.unlink(path)
        version_test_support.assert_carries_cli_version(self, json.loads(stdout))

    def test_expected_failure_payload_carries_the_acting_build(self):
        with mock.patch.object(cli_version, "resolve_cli_version", return_value="0.7.0"), mock.patch.object(
            unity_session, "probe_health_payload", return_value=({"ok": True, "status": "ready", "bridge_version": "0.6.0"}, None)
        ):
            _exit_code, stdout, _stderr = unity_puer_exec.run_cli([
                "exec", "--base-url", "http://127.0.0.1:55231", "--code", "export default function run() { return 1; }",
            ])
        version_test_support.assert_carries_cli_version(self, json.loads(stdout))

    def test_unexpected_failure_payload_carries_the_acting_build(self):
        failure = {"ok": False, "status": "failed", "operation": "exec", "error": "boom"}
        with mock.patch.object(
            unity_session, "probe_health_payload", return_value=(None, "no service")
        ), mock.patch.object(
            direct_exec_client, "invoke_command", return_value=(1, "", json.dumps(failure))
        ):
            _exit_code, _stdout, stderr = unity_puer_exec.run_cli([
                "exec", "--base-url", "http://127.0.0.1:55231", "--code", "export default function run() { return 1; }",
            ])
        version_test_support.assert_carries_cli_version(self, json.loads(stderr))

    def test_usage_error_payload_carries_the_acting_build(self):
        # address_conflict is the usage error that routes to stdout.
        exit_code, stdout, _stderr = unity_puer_exec.run_cli([
            "exec",
            "--project-path", "X:/unity-project",
            "--base-url", "http://127.0.0.1:55231",
            "--code", "export default function run() { return 1; }",
        ])
        self.assertEqual(exit_code, 2)
        version_test_support.assert_carries_cli_version(self, json.loads(stdout))

    def test_response_file_reference_retains_the_acting_build(self):
        self.assertIn("cli_version", runtime._RESPONSE_FILE_ROUTING_FIELDS)
        path = self._log_file("First entry\n")
        try:
            size = os.path.getsize(path)
            with tempfile.TemporaryDirectory() as temp_dir:
                dest = os.path.join(temp_dir, "briefs.json")
                _exit_code, stdout, _stderr = unity_puer_exec.run_cli([
                    "get-log-briefs", "--unity-log-path", path, "--range", "0-{}".format(size),
                    "--response-file", dest,
                ])
                reference = json.loads(stdout)
                with open(dest, "r", encoding="utf-8") as handle:
                    full = json.load(handle)
        finally:
            os.unlink(path)
        version_test_support.assert_carries_cli_version(self, reference)
        self.assertIn("response_file", reference)
        self.assertEqual(reference["cli_version"], full["cli_version"])

    def test_strip_helper_leaves_the_rest_of_a_payload_untouched(self):
        body = {"ok": True, "status": "completed", "cli_version": "0.7.0"}
        self.assertEqual(
            version_test_support.strip_cli_version(body),
            {"ok": True, "status": "completed"},
        )


class VersionMismatchGuidanceTests(unittest.TestCase):
    def _refusal(self, guard, leading_argv=()):
        detail = {
            "guard": guard,
            "cli_version": "0.7.0",
            "observed_version": None if "unknown" in guard else "0.6.0",
            "observed_location": "http://127.0.0.1:55231",
        }
        with mock.patch.object(cli_version, "check_package_layout", return_value=detail):
            exit_code, stdout, stderr = unity_puer_exec.run_cli(
                list(leading_argv) + ["get-log-source", "--project-path", "X:/unity-project"]
            )
        self.assertEqual(exit_code, 24, stderr)
        return json.loads(stdout)

    def test_bridge_situation_explains_the_mixed_installation(self):
        body = self._refusal(cli_version.GUARD_BRIDGE)
        self.assertIn("one release", body["situation"])
        self.assertIn("mixed installation", body["situation"])

    def test_package_layout_situation_explains_the_stale_binary(self):
        body = self._refusal(cli_version.GUARD_PACKAGE_LAYOUT)
        self.assertIn("package tree it is installed in", body["situation"])

    def test_unknown_counterpart_situation_explains_the_unverifiable_half(self):
        body = self._refusal(cli_version.GUARD_BRIDGE_VERSION_UNKNOWN)
        self.assertIn("predates version reporting", body["situation"])

    def test_next_steps_offer_verification_and_never_a_rerun_or_bypass(self):
        body = self._refusal(cli_version.GUARD_BRIDGE)
        commands = [step["command"] for step in body["next_steps"]]
        self.assertIn("--version", commands)
        self.assertNotIn("get-log-source", commands)
        blob = json.dumps(body)
        for forbidden in ("--allow-version-mismatch", "--force", "bypass", "override"):
            self.assertNotIn(forbidden, blob)

    def test_suppress_guidance_keeps_the_structured_detail(self):
        body = self._refusal(cli_version.GUARD_BRIDGE, leading_argv=["--suppress-guidance"])
        self.assertNotIn("next_steps", body)
        self.assertNotIn("situation", body)
        detail = body["version_mismatch"]
        self.assertEqual(detail["guard"], cli_version.GUARD_BRIDGE)
        self.assertEqual(detail["cli_version"], "0.7.0")
        self.assertEqual(detail["observed_version"], "0.6.0")
        self.assertEqual(detail["observed_location"], "http://127.0.0.1:55231")

    def test_every_command_has_a_guidance_entry_and_documents_the_status(self):
        for command in help_surface.COMMANDS:
            entry = help_surface.GUIDANCE_MATRIX.get((command, "version_mismatch"))
            self.assertIsNotNone(entry, command)
            self.assertTrue(entry.get("situation") or entry.get("next_steps"), command)
            status_help = help_surface.render_command_status_help(command)
            self.assertIn("`version_mismatch` -> exit 24", status_help)

    def test_help_documents_no_bypass(self):
        blob = help_surface.render_top_level_help() + "".join(
            help_surface.render_command_status_help(command) for command in help_surface.COMMANDS
        )
        self.assertIn("no bypass", blob.lower())
        self.assertNotIn("--allow-version-mismatch", blob)


class BridgeVersionContractTests(unittest.TestCase):
    """The Editor half's side of the same contract, asserted on source."""

    EDITOR = REPO_ROOT / "packages" / "com.txcombo.unity-puer-exec" / "Editor"

    def test_health_response_emits_bridge_version(self):
        protocol = (self.EDITOR / "UnityPuerExecProtocol.cs").read_text(encoding="utf-8")
        self.assertIn('\\"bridge_version\\":', protocol)
        self.assertIn("string bridgeVersion", protocol)

    def test_bridge_version_is_resolved_from_package_metadata(self):
        server = (self.EDITOR / "UnityPuerExecServer.cs").read_text(encoding="utf-8")
        self.assertIn("PackageManager.PackageInfo.FindForAssembly", server)
        self.assertIn("bridgeVersion: bridgeVersion", server)
        # Null PackageInfo means "not package-installed"; it must not be guessed.
        self.assertIn('info == null ? "" :', server)


class EditorNotUnderControlStatusTests(unittest.TestCase):
    """Task 6.5: the not-under-control status, its guidance, and the version-mismatch
    distinction, at the runtime boundary."""

    def _run_exec(self, project_dir):
        return unity_puer_exec.run_cli([
            "exec",
            "--project-path", project_dir,
            "--code", "export default function run(){ return 1; }",
            "--request-id", "R-nc",
        ])

    def test_running_editor_without_control_service_reports_a_distinct_status(self):
        with tempfile.TemporaryDirectory() as project_dir:
            with mock.patch.object(
                unity_session, "classify_session_state",
                return_value=(unity_session_endpoint.SESSION_STATE_NOT_UNDER_CONTROL, None, None),
            ), mock.patch.object(
                unity_session, "_project_lockfile_is_held", return_value=True
            ), mock.patch.object(
                unity_session, "discover_project_endpoint", return_value=(None, None, None, False)
            ):
                exit_code, stdout, _stderr = self._run_exec(project_dir)

        body = json.loads(stdout)
        # Its own exit code, distinct from launch (20) and readiness (21) failures.
        self.assertEqual(exit_code, 17)
        self.assertEqual(body["status"], "editor_not_under_cli_control")
        # The guidance is actionable, not just a failure notice.
        self.assertTrue(body["ways_forward"])
        self.assertTrue(any("launch the Editor" in step for step in body["ways_forward"]))

    def test_a_version_mismatched_discovered_service_reports_version_mismatch(self):
        # The error-path scan finds a service that owns the project but disagrees on
        # version. That must be reported as version_mismatch pointing at the
        # installation, not as a missing opt-in pointing at an activation menu the
        # older bridge does not have.
        detail = cli_version.check_bridge(
            "0.7.0",
            "http://127.0.0.1:55231",
            {"ok": True, "status": "ready", "bridge_version": "0.6.0", "project_path": "x", "session_marker": "m"},
            require_version=True,
        )
        self.assertIsNotNone(detail)
        mismatch = unity_session.UnityVersionMismatchError(detail, message=cli_version.mismatch_message(detail))

        with tempfile.TemporaryDirectory() as project_dir:
            with mock.patch.object(
                unity_session, "classify_session_state",
                return_value=(unity_session_endpoint.SESSION_STATE_NOT_UNDER_CONTROL, None, None),
            ), mock.patch.object(
                unity_session, "_project_lockfile_is_held", return_value=True
            ), mock.patch.object(
                unity_session, "discover_project_endpoint", side_effect=mismatch
            ):
                exit_code, stdout, _stderr = self._run_exec(project_dir)

        body = json.loads(stdout)
        self.assertEqual(body["status"], "version_mismatch")
        self.assertNotEqual(body["status"], "editor_not_under_cli_control")


if __name__ == "__main__":
    unittest.main()
