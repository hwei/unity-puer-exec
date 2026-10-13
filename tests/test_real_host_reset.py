import ast
import inspect
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import tests.test_real_host_integration as real_host


def _device():
    class Device(real_host._SharedRealHostDevice, unittest.TestCase):
        def setUp(self):
            self.project_path = Path("host")

    device = Device()
    device.setUp()
    return device


def _request_id_segments_built_from_pid(source):
    """Return source segments that build a request id using os.getpid()."""
    tree = ast.parse(source)
    parents = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    flagged = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "getpid"
        ):
            continue
        # Climb to the enclosing expression/statement: the request id is
        # either assigned there or passed as a --request-id argument nearby.
        current = node
        while current is not None:
            segment = ast.get_source_segment(source, current) or ""
            if "request_id" in segment or "request-id" in segment:
                flagged.append(segment)
                break
            current = parents.get(current)
    return flagged


class RealHostReloadProbeTests(unittest.TestCase):
    def test_none_probe_then_ready_endpoint_returns_the_ready_payload(self):
        device = _device()
        ready = {"ok": True, "status": "ready", "refresh": {"pending": "not_pending"}}
        with mock.patch.object(
            real_host.unity_session, "_probe_health", return_value=(None, "dropped")
        ), mock.patch.object(
            real_host,
            "_scan_ready_control_endpoint",
            return_value=("http://127.0.0.1:55240", ready),
        ):
            base_url, payload = device._probe_through_reload_window(
                "http://127.0.0.1:55231", timeout_seconds=1
            )
        self.assertEqual(base_url, "http://127.0.0.1:55240")
        self.assertEqual(payload, ready)

    def test_health_fails_when_the_endpoint_never_returns(self):
        device = _device()
        with mock.patch.object(
            real_host.unity_session, "_probe_health", return_value=(None, "dropped")
        ), mock.patch.object(
            real_host, "_scan_ready_control_endpoint", return_value=(None, None)
        ), mock.patch.object(real_host.time, "sleep"):
            with self.assertRaises(AssertionError) as raised:
                device._health("http://127.0.0.1:55231", timeout_seconds=0)
        self.assertIn("reload window", str(raised.exception))

    def test_pending_wait_survives_a_dropped_endpoint_and_rebinds(self):
        device = _device()
        calls = {"n": 0}

        def scan(project_path, exclude_ports=(), timeout_seconds=1.5):
            calls["n"] += 1
            if calls["n"] < 2:
                return None, None
            return (
                "http://127.0.0.1:55240",
                {"ok": True, "status": "ready", "refresh": {"pending": "pending"}},
            )

        with mock.patch.object(
            real_host.unity_session, "_probe_health", return_value=(None, "WinError 10054")
        ), mock.patch.object(real_host, "_scan_ready_control_endpoint", side_effect=scan), mock.patch.object(
            real_host.time, "sleep"
        ):
            base_url, refresh = device._wait_for_refresh_pending(
                "http://127.0.0.1:55231", timeout_seconds=5
            )
        self.assertEqual(base_url, "http://127.0.0.1:55240")
        self.assertEqual(refresh["pending"], "pending")
        self.assertGreaterEqual(calls["n"], 2)

    def test_each_play_mode_helper_has_one_definition_on_the_shared_device(self):
        source = inspect.getsource(real_host)
        for name in (
            "_health",
            "_wait_for_refresh_pending",
            "_wait_for_refresh_state",
            "_wait_for_play_exit",
            "_exec_raw",
            "_exec_script",
            "_set_play_mode",
            "_write_compile_triggering_probe",
        ):
            self.assertEqual(source.count("def {}(".format(name)), 1, name)
            shared = getattr(real_host._SharedRealHostDevice, name)
            self.assertIs(getattr(real_host.RefreshOnChangeRealHostTests, name), shared, name)
            self.assertIs(getattr(real_host.PlayModeCompileBlockRealHostTests, name), shared, name)


class RealHostRequestIdUniquenessTests(unittest.TestCase):
    def test_helper_changes_value_on_each_call(self):
        first = real_host._unique_request_id("probe")
        second = real_host._unique_request_id("probe")
        self.assertTrue(first.startswith("probe-"))
        self.assertNotEqual(first, second)

    def test_no_exec_request_id_is_built_from_the_process_id_alone(self):
        flagged = _request_id_segments_built_from_pid(
            inspect.getsource(real_host)
        )
        self.assertEqual(
            flagged,
            [],
            "exec request ids must not be built from os.getpid(): {}".format(flagged),
        )


class RealHostResetTests(unittest.TestCase):
    def test_unknown_modal_is_cleared_before_the_next_case(self):
        device = _device()
        reads = {"n": 0}

        def run_cli(argv):
            if argv[0] == "get-blocker-state":
                reads["n"] += 1
                if reads["n"] == 1:
                    return (
                        0,
                        {
                            "result": {
                                "status": "modal_blocked",
                                "blocker": {
                                    "type": "unknown_modal_dialog",
                                    "hwnd": 42,
                                    "title": "Codex Validation Prompt",
                                    "buttons": [{"label": "OK"}, {"label": "Cancel"}],
                                },
                            }
                        },
                        "",
                        "",
                    )
                return 0, {"result": {"status": "clear"}}, "", ""
            self.assertEqual(argv[0], "resolve-blocker")
            self.assertIn("Cancel", argv)
            self.assertIn("42", argv)
            return 0, {"result": {"status": "resolved"}}, "", ""

        with mock.patch.object(real_host, "_run_cli", side_effect=run_cli), mock.patch.object(
            real_host.time, "sleep"
        ):
            device._clear_residual_modal_blocker()
        self.assertEqual(reads["n"], 2)

    def test_scene_restore_opens_the_baseline_scene(self):
        device = _device()
        seen = {}

        def exec_settled(base_url, code, wait_ms=None):
            seen["code"] = code
            return 0, {
                "result": {
                    "path": "Assets/__codex_host_reset/Baseline.unity",
                    "dirty": False,
                    "cleared": True,
                }
            }

        with mock.patch.object(device, "_ensure_shared_host_ready", return_value="http://127.0.0.1:55231"), \
                mock.patch.object(device, "_exec_settled", side_effect=exec_settled):
            device._restore_active_scene()
        self.assertIn("ClearSceneDirtiness", seen["code"])
        self.assertIn("SceneManager.GetActiveScene", seen["code"])
        self.assertNotIn("EditorSceneManager.GetActiveScene", seen["code"])
        self.assertIn("Assets/__codex_host_reset/Baseline.unity", seen["code"])
        self.assertNotIn("GetActiveScene().path", seen["code"])
        self.assertNotIn("SaveCurrentModifiedScenesIfUserWantsTo", seen["code"])

    def test_latched_temp_compile_error_retries_after_a_new_script(self):
        device = _device()
        calls = {"n": 0}

        def exec_settled(base_url, code, wait_ms=None):
            calls["n"] += 1
            if calls["n"] == 1:
                return 23, {
                    "status": "unity_compile_error",
                    "compile_messages": [
                        {
                            "message": "Assets/__codex_validation_temp/BrokenCompileErrorTest.cs(4,9): error CS0246",
                        }
                    ],
                }
            return 0, {
                "result": {
                    "path": "Assets/__codex_host_reset/Baseline.unity",
                    "dirty": False,
                    "cleared": True,
                }
            }

        with tempfile.TemporaryDirectory() as tmp:
            device.project_path = Path(tmp)
            broken = device.project_path / "Assets" / "__codex_validation_temp" / "BrokenCompileErrorTest.cs"
            broken.parent.mkdir(parents=True)
            broken.write_text("broken\n", encoding="utf-8")
            with mock.patch.object(device, "_ensure_shared_host_ready", return_value="http://127.0.0.1:55231"), \
                    mock.patch.object(device, "_exec_settled", side_effect=exec_settled):
                device._restore_active_scene()
            self.assertFalse(broken.exists())
            probe = device.project_path / "Assets" / "__codex_validation_temp" / real_host.COMPILE_RECOVERY_PROBE_NAME
            self.assertTrue(probe.exists())
        self.assertEqual(calls["n"], 2)

    def test_missing_exec_record_retries_after_the_endpoint_returns(self):
        device = _device()
        calls = {"n": 0}

        def exec_settled(base_url, code, wait_ms=None):
            calls["n"] += 1
            if calls["n"] == 1:
                return 1, {"status": "missing", "error": "no recoverable record exists for request_id"}
            return 0, {
                "result": {
                    "path": "Assets/__codex_host_reset/Baseline.unity",
                    "dirty": False,
                    "cleared": True,
                }
            }

        with mock.patch.object(device, "_ensure_shared_host_ready", return_value="http://127.0.0.1:55231"), \
                mock.patch.object(device, "_exec_settled", side_effect=exec_settled), \
                mock.patch.object(
                    device,
                    "_probe_through_reload_window",
                    return_value=("http://127.0.0.1:55240", {"status": "ready"}),
                ):
            device._restore_active_scene()
        self.assertEqual(calls["n"], 2)

    def test_change_signal_is_reset_before_scene_restore(self):
        source = inspect.getsource(real_host._SharedRealHostDevice._reset_shared_host_state)
        self.assertLess(
            source.index("_drop_unimported_compile_probes"),
            source.index("_ensure_shared_host_ready"),
        )
        self.assertLess(
            source.index("_reset_change_signal_state"),
            source.index("_restore_active_scene"),
        )

    def test_unimported_compile_probe_is_removed_before_the_signal_health_read(self):
        device = _device()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            device.project_path = root
            hidden = root / "Assets" / "__codex_validation_temp" / ".not_imported"
            hidden.mkdir(parents=True)
            hidden_cs = hidden / "BaselineWalkProbe.cs"
            hidden_cs.write_text("internal static class BaselineWalkProbe {}\n", encoding="utf-8")
            hidden_scene = hidden / "Probe.unity"
            hidden_scene.write_text("%YAML\n", encoding="utf-8")
            imported = root / "Assets" / "__codex_validation_temp" / "Keep.cs"
            imported.write_text("internal static class Keep {}\n", encoding="utf-8")
            outside = root / "Assets" / "Game" / ".hidden" / "Keep.cs"
            outside.parent.mkdir(parents=True)
            outside.write_text("internal static class Outside {}\n", encoding="utf-8")

            def ensure():
                if hidden_cs.exists():
                    raise AssertionError("health read before the unimported probe was removed")
                device._last_host_health = {
                    "refresh": {"pending": "not_pending", "suppressed": False}
                }
                return "http://127.0.0.1:55231"

            with mock.patch.object(device, "_ensure_shared_host_ready", side_effect=ensure), \
                    mock.patch.object(device, "_exec_settled") as exec_settled, \
                    mock.patch.object(device, "_touch_compile_probe") as touch:
                device._reset_change_signal_state()
            self.assertFalse(hidden_cs.exists())
            self.assertTrue(hidden_scene.exists())
            self.assertTrue(imported.exists())
            self.assertTrue(outside.exists())
            exec_settled.assert_not_called()
            touch.assert_not_called()

    def test_pending_signal_reset_writes_a_compilable_probe(self):
        device = _device()
        with tempfile.TemporaryDirectory() as tmp:
            device.project_path = Path(tmp)

            def ensure():
                device._last_host_health = {
                    "refresh": {"pending": "pending", "suppressed": False}
                }
                return "http://127.0.0.1:55231"

            with mock.patch.object(device, "_ensure_shared_host_ready", side_effect=ensure), \
                    mock.patch.object(
                        device,
                        "_exec_settled",
                        return_value=(0, {"result": {"pending": "NotPending"}}),
                    ), \
                    mock.patch.object(device, "_touch_compile_probe") as touch:
                device._reset_change_signal_state()
            touch.assert_called_once()

    def test_save_scene_cases_stage_their_own_scene(self):
        modified = inspect.getsource(real_host.RealHostIntegrationTests.test_resolve_blocker_cancel_is_rejected_for_save_scene_against_real_host)
        untitled = inspect.getsource(real_host.RealHostIntegrationTests.test_get_blocker_state_reports_save_scene_dialog_against_real_host)
        self.assertIn("_code_saved_scene_modified_prompt", modified)
        self.assertNotIn("GetActiveScene", modified)
        self.assertIn("_code_untitled_scene_save_dialog", untitled)
        self.assertIn("NewScene", inspect.getsource(real_host._SharedRealHostDevice._code_untitled_scene_save_dialog))
        self.assertIn("SaveScene", inspect.getsource(real_host._SharedRealHostDevice._code_saved_scene_modified_prompt))

    def test_script_updater_skip_path_uses_the_shared_removal(self):
        source = inspect.getsource(
            real_host.RealHostIntegrationTests.test_script_updater_consent_dialog_recovery_against_real_host
        )
        self.assertIn("_remove_script_updater_fixture", source)
        self.assertNotIn("fixture_path.unlink", source)
        device = _device()
        fixture = device.project_path / "Assets" / "__codex_validation_temp" / "ScriptUpdaterTriggerFixture.cs"
        with mock.patch.object(device, "_cleanup_temp_assets", return_value={"residue": []}) as cleanup, \
                mock.patch.object(real_host, "_scan_ready_control_endpoint", return_value=(None, None)):
            device._remove_script_updater_fixture(fixture)
        cleanup.assert_called_once_with(wait_for_editor=True)


class RealHostCompileTriggeringProbeTests(unittest.TestCase):
    def test_watched_extensions_are_read_from_the_exec_help_statement(self):
        watched = real_host._watched_compile_triggering_extensions()
        self.assertEqual(watched, (".cs", ".asmdef", ".asmref", ".rsp"))

    def test_probe_without_a_watched_extension_is_rejected_before_writing(self):
        device = _device()
        with tempfile.TemporaryDirectory() as tmp:
            device.project_path = Path(tmp)
            with self.assertRaises(AssertionError) as raised:
                device._write_compile_triggering_probe("BaseUrlRefreshContinuationProbe")
            message = str(raised.exception)
            for extension in real_host._watched_compile_triggering_extensions():
                self.assertIn(extension, message)
            # Rejected before any validation-host write.
            self.assertEqual(list(Path(tmp).rglob("*")), [])

    def test_probe_with_a_watched_extension_still_stages(self):
        device = _device()
        with tempfile.TemporaryDirectory() as tmp:
            device.project_path = Path(tmp)
            probe = device._write_compile_triggering_probe("AutomaticRefreshProbe.cs")
            self.assertTrue(probe.exists())
            self.assertEqual(probe.suffix, ".cs")

    def test_pending_wait_failure_names_watched_extensions_and_skipped_reason(self):
        device = _device()
        health = {
            "ok": True,
            "status": "ready",
            "refresh": {"pending": "not_pending", "skipped_reason": "play_mode"},
        }
        with mock.patch.object(
            real_host.unity_session, "_probe_health", return_value=(None, "dropped")
        ), mock.patch.object(
            real_host, "_scan_ready_control_endpoint", return_value=("http://127.0.0.1:55240", health)
        ), mock.patch.object(real_host.time, "sleep"):
            with self.assertRaises(AssertionError) as raised:
                device._wait_for_refresh_pending("http://127.0.0.1:55231", timeout_seconds=0.3)
        message = str(raised.exception)
        self.assertIn("watched extensions", message)
        self.assertIn(".cs", message)
        self.assertIn("play_mode", message)

    def test_pending_wait_dropped_endpoint_keeps_its_own_message(self):
        device = _device()
        with mock.patch.object(
            real_host.unity_session, "_probe_health", return_value=(None, "dropped")
        ), mock.patch.object(
            real_host, "_scan_ready_control_endpoint", return_value=(None, None)
        ), mock.patch.object(real_host.time, "sleep"):
            with self.assertRaises(AssertionError) as raised:
                device._wait_for_refresh_pending("http://127.0.0.1:55231", timeout_seconds=0.3)
        message = str(raised.exception)
        self.assertIn("endpoint did not return", message)
        self.assertNotIn("change signal did not become pending", message)
