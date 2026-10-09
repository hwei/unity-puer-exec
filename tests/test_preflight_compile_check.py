import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import preflight_compile_check  # type: ignore
import unity_session  # type: ignore


TWO_ERROR_LOG = (
    "[Unity] batch preamble\r\n"
    "Assets/Foo.cs(12,25): error CS0103: The name `Bar' does not exist in the current context\r\n"
    "Assets/Bar.cs(3,9): error CS1002: ; expected\r\n"
    "Assets/Foo.cs(1,1): warning CS0168: variable declared but never used\r\n"
)


class ParseCompileErrorsTests(unittest.TestCase):
    def test_returns_both_diagnostics_from_a_synthetic_log(self):
        diagnostics = preflight_compile_check.parse_compile_errors(TWO_ERROR_LOG)
        self.assertEqual([entry["code"] for entry in diagnostics], ["CS0103", "CS1002"])
        self.assertEqual(diagnostics[0]["file"], "Assets/Foo.cs")
        self.assertEqual(diagnostics[0]["line"], 12)
        self.assertEqual(diagnostics[0]["column"], 25)
        self.assertEqual(diagnostics[0]["message"], "The name `Bar' does not exist in the current context")
        self.assertEqual(diagnostics[1]["file"], "Assets/Bar.cs")
        self.assertEqual(diagnostics[1]["line"], 3)
        self.assertEqual(diagnostics[1]["column"], 9)

    def test_reports_an_error_without_a_source_location(self):
        diagnostics = preflight_compile_check.parse_compile_errors(
            "error CS2001: Source file 'missing.cs' could not be found.\n"
        )
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(diagnostics[0]["code"], "CS2001")
        self.assertIsNone(diagnostics[0]["file"])
        self.assertIsNone(diagnostics[0]["line"])
        self.assertIsNone(diagnostics[0]["column"])

    def test_ignores_warnings_and_a_clean_log(self):
        self.assertEqual(preflight_compile_check.parse_compile_errors("all good\n"), [])
        self.assertEqual(
            preflight_compile_check.parse_compile_errors(
                "Assets/Foo.cs(1,1): warning CS0168: unused\n"
            ),
            [],
        )

    def test_failure_detail_names_file_and_error_code(self):
        detail = preflight_compile_check.format_failure_detail(
            {"diagnostics": preflight_compile_check.parse_compile_errors(TWO_ERROR_LOG)}
        )
        self.assertIn("Assets/Foo.cs(12,25): error CS0103", detail)
        self.assertIn("Assets/Bar.cs(3,9): error CS1002", detail)


class RunPreflightTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.project_path = Path(self._tmp.name) / "Project"
        (self.project_path / "Packages").mkdir(parents=True)
        (self.project_path / "Packages" / "manifest.json").write_text("{}\n", encoding="utf-8")
        self.log_path = Path(self._tmp.name) / "preflight.log"

    def _run(self, run_fn, read_log_fn=None, env=None, **kwargs):
        return preflight_compile_check.run_preflight(
            project_path=self.project_path,
            unity_exe_path="C:/Unity/Unity.exe",
            log_path=self.log_path,
            resolve_project_path_fn=lambda project_path: self.project_path,
            resolve_unity_exe_path_fn=lambda project_path, unity_exe_path: "C:/Unity/Unity.exe",
            run_fn=run_fn,
            read_log_fn=read_log_fn,
            env={} if env is None else env,
            **kwargs,
        )

    def test_runs_the_batch_command_and_returns_exit_code_and_log_path(self):
        captured = {}

        def fake_run(argv, **kwargs):
            captured["argv"] = argv
            captured["kwargs"] = kwargs
            return types.SimpleNamespace(returncode=0)

        result = self._run(fake_run, read_log_fn=lambda path: "")

        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["log_path"], str(self.log_path))
        self.assertEqual(result["diagnostics"], [])
        argv = captured["argv"]
        self.assertEqual(argv[0], "C:/Unity/Unity.exe")
        for switch in ("-batchMode", "-quit", "-nographics"):
            self.assertIn(switch, argv)
        self.assertEqual(argv[argv.index("-projectPath") + 1], str(self.project_path))
        self.assertEqual(argv[argv.index("-logFile") + 1], str(self.log_path))
        self.assertEqual(captured["kwargs"]["timeout"], preflight_compile_check.DEFAULT_TIMEOUT_SECONDS)

    def test_appends_env_launch_arguments(self):
        captured = {}

        def fake_run(argv, **kwargs):
            captured["argv"] = argv
            return types.SimpleNamespace(returncode=0)

        result = self._run(
            fake_run,
            read_log_fn=lambda path: "",
            env={"UNITY_PUER_EXEC_UNITY_LAUNCH_ARGS": '["-force-gles30"]'},
        )

        self.assertEqual(result["status"], "passed")
        self.assertIn("-force-gles30", captured["argv"])

    def test_non_zero_exit_returns_parsed_diagnostics(self):
        result = self._run(
            lambda argv, **kwargs: types.SimpleNamespace(returncode=1),
            read_log_fn=lambda path: TWO_ERROR_LOG,
        )
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["kind"], preflight_compile_check.KIND_COMPILE_FAILURE)
        self.assertEqual([entry["code"] for entry in result["diagnostics"]], ["CS0103", "CS1002"])

    def test_non_zero_exit_without_compile_errors_reports_exit_code_and_log_path(self):
        result = self._run(
            lambda argv, **kwargs: types.SimpleNamespace(returncode=7),
            read_log_fn=lambda path: "Fatal error: license checkout failed\n",
        )
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["kind"], preflight_compile_check.KIND_LAUNCH_FAILURE)
        self.assertEqual(result["exit_code"], 7)
        self.assertEqual(result["diagnostics"], [])
        detail = preflight_compile_check.format_failure_detail(result)
        self.assertIn("7", detail)
        self.assertIn(str(self.log_path), detail)

    def test_compile_errors_fail_even_on_a_zero_exit(self):
        result = self._run(
            lambda argv, **kwargs: types.SimpleNamespace(returncode=0),
            read_log_fn=lambda path: TWO_ERROR_LOG,
        )
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["kind"], preflight_compile_check.KIND_COMPILE_FAILURE)

    def test_timeout_is_a_failure(self):
        def fake_run(argv, **kwargs):
            raise subprocess.TimeoutExpired(argv, kwargs.get("timeout"))

        result = self._run(fake_run, read_log_fn=lambda path: "")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["kind"], preflight_compile_check.KIND_TIMEOUT)


class PreflightSkipTests(unittest.TestCase):
    def test_skips_when_project_path_is_unavailable(self):
        def raise_value_error(project_path):
            raise ValueError("UNITY_PROJECT_PATH is not set")

        run_fn = mock.Mock()
        result = preflight_compile_check.run_preflight(
            resolve_project_path_fn=raise_value_error,
            run_fn=run_fn,
            env={},
        )
        self.assertEqual(result["status"], "skipped")
        self.assertIn("unavailable", result["reason"])
        run_fn.assert_not_called()

    def test_skips_when_project_path_does_not_exist(self):
        missing = Path(tempfile.gettempdir()) / "definitely-not-a-real-host-7f3a"
        run_fn = mock.Mock()
        result = preflight_compile_check.run_preflight(
            resolve_project_path_fn=lambda project_path: missing,
            run_fn=run_fn,
            env={},
        )
        self.assertEqual(result["status"], "skipped")
        self.assertIn("does not exist", result["reason"])
        run_fn.assert_not_called()

    def test_skips_when_manifest_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "Project"
            (project / "Packages").mkdir(parents=True)
            run_fn = mock.Mock()
            result = preflight_compile_check.run_preflight(
                resolve_project_path_fn=lambda project_path: project,
                run_fn=run_fn,
                env={},
            )
        self.assertEqual(result["status"], "skipped")
        self.assertIn("manifest", result["reason"])
        run_fn.assert_not_called()

    def test_skips_when_unity_executable_is_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "Project"
            (project / "Packages").mkdir(parents=True)
            (project / "Packages" / "manifest.json").write_text("{}\n", encoding="utf-8")

            def raise_launch_error(project_path, unity_exe_path):
                raise unity_session.UnityLaunchError("Unity not found")

            run_fn = mock.Mock()
            result = preflight_compile_check.run_preflight(
                resolve_project_path_fn=lambda project_path: project,
                resolve_unity_exe_path_fn=raise_launch_error,
                run_fn=run_fn,
                env={},
            )
        self.assertEqual(result["status"], "skipped")
        self.assertIn("Unity executable unavailable", result["reason"])
        run_fn.assert_not_called()

    def test_skip_never_calls_the_batch_runner(self):
        run_fn = mock.Mock()
        preflight_compile_check.run_preflight(
            resolve_project_path_fn=lambda project_path: (_ for _ in ()).throw(ValueError("nope")),
            run_fn=run_fn,
            env={},
        )
        self.assertEqual(run_fn.call_count, 0)


class PreflightOnceGuardTests(unittest.TestCase):
    def setUp(self):
        preflight_compile_check.reset_preflight_cache()
        self.addCleanup(preflight_compile_check.reset_preflight_cache)

    def test_runs_the_batch_preflight_once_per_process(self):
        calls = []

        def fake_run_preflight(project_path=None, unity_exe_path=None, **kwargs):
            calls.append((project_path, unity_exe_path))
            return {"status": "passed", "diagnostics": []}

        with mock.patch.object(
            preflight_compile_check, "run_preflight", side_effect=fake_run_preflight
        ):
            first = preflight_compile_check.run_preflight_once("host", "unity")
            second = preflight_compile_check.run_preflight_once("host", "unity")
            third = preflight_compile_check.run_preflight_once("host", "unity")

        self.assertEqual(len(calls), 1)
        self.assertIs(first, second)
        self.assertIs(second, third)

    def test_reset_preflight_cache_forces_a_new_run(self):
        calls = []

        def fake_run_preflight(project_path=None, unity_exe_path=None, **kwargs):
            calls.append(project_path)
            return {"status": "passed", "diagnostics": []}

        with mock.patch.object(
            preflight_compile_check, "run_preflight", side_effect=fake_run_preflight
        ):
            preflight_compile_check.run_preflight_once("host", "unity")
            preflight_compile_check.reset_preflight_cache()
            preflight_compile_check.run_preflight_once("host", "unity")

        self.assertEqual(len(calls), 2)

    def test_require_preflight_raises_with_the_parsed_diagnostics(self):
        failing = {
            "status": "failed",
            "kind": preflight_compile_check.KIND_COMPILE_FAILURE,
            "diagnostics": [
                {"code": "CS0103", "message": "nope", "file": "Assets/A.cs", "line": 4, "column": 5}
            ],
            "exit_code": 1,
            "log_path": "preflight.log",
            "reason": "compile failed",
        }
        with mock.patch.object(
            preflight_compile_check, "run_preflight_once", return_value=failing
        ):
            with self.assertRaises(AssertionError) as context:
                preflight_compile_check.require_preflight("host", "unity")
        self.assertIn("Assets/A.cs(4,5): error CS0103", str(context.exception))

    def test_require_preflight_passes_through_a_pass_result(self):
        passing = {"status": "passed", "diagnostics": []}
        with mock.patch.object(
            preflight_compile_check, "run_preflight_once", return_value=passing
        ):
            self.assertIs(preflight_compile_check.require_preflight("host", "unity"), passing)


class RealHostSuiteWiringTests(unittest.TestCase):
    """The suite runs the preflight once, before the first interactive launch."""

    def setUp(self):
        import tests.test_real_host_integration as real_host

        self.real_host = real_host
        preflight_compile_check.reset_preflight_cache()
        self.addCleanup(preflight_compile_check.reset_preflight_cache)

    def _harness(self):
        real_host = self.real_host

        class _Harness(real_host._SharedRealHostDevice, unittest.TestCase):
            pass

        return _Harness

    def test_disabled_gate_skips_without_preflight_or_launch(self):
        events = []
        with mock.patch.object(self.real_host, "_real_host_tests_enabled", return_value=False), \
                mock.patch.object(
                    self.real_host.preflight_compile_check,
                    "run_preflight_once",
                    side_effect=lambda *args, **kwargs: events.append("preflight"),
                ), \
                mock.patch.object(
                    self.real_host, "_start_shared_host", side_effect=lambda *args: events.append("launch")
                ):
            with self.assertRaises(unittest.SkipTest):
                self._harness().setUpClass()
        self.assertEqual(events, [])

    def test_failing_preflight_fails_before_the_interactive_launch(self):
        events = []

        def boundary(project_path):
            events.append("boundary")
            return {"ok": True}

        failing = {
            "status": "failed",
            "kind": preflight_compile_check.KIND_COMPILE_FAILURE,
            "diagnostics": [
                {"code": "CS0103", "message": "nope", "file": "Assets/A.cs", "line": 4, "column": 5}
            ],
            "exit_code": 1,
            "log_path": "preflight.log",
            "reason": "compile failed",
        }
        with mock.patch.object(self.real_host, "_real_host_tests_enabled", return_value=True), \
                mock.patch.object(
                    self.real_host, "_require_real_host_project_path", return_value=Path("host")
                ), \
                mock.patch.object(
                    self.real_host, "_require_unity_editor", return_value=Path("Unity.exe")
                ), \
                mock.patch.object(
                    self.real_host, "_ensure_clean_test_boundary", side_effect=boundary
                ), \
                mock.patch.object(
                    self.real_host.preflight_compile_check, "run_preflight_once", return_value=failing
                ), \
                mock.patch.object(
                    self.real_host, "_start_shared_host", side_effect=lambda *args: events.append("launch")
                ):
            with self.assertRaises(AssertionError) as context:
                self._harness().setUpClass()
        self.assertIn("CS0103", str(context.exception))
        self.assertEqual(events, ["boundary"])
        self.assertNotIn("launch", events)

    def test_several_classes_run_the_batch_preflight_once(self):
        batch_calls = []

        def fake_run_preflight(project_path=None, unity_exe_path=None, **kwargs):
            batch_calls.append((project_path, unity_exe_path))
            return {"status": "passed", "diagnostics": []}

        with mock.patch.object(self.real_host, "_real_host_tests_enabled", return_value=True), \
                mock.patch.object(
                    self.real_host, "_require_real_host_project_path", return_value=Path("host")
                ), \
                mock.patch.object(
                    self.real_host, "_require_unity_editor", return_value=Path("Unity.exe")
                ), \
                mock.patch.object(self.real_host, "_ensure_clean_test_boundary"), \
                mock.patch.object(
                    preflight_compile_check, "run_preflight", side_effect=fake_run_preflight
                ), \
                mock.patch.object(
                    self.real_host,
                    "_start_shared_host",
                    return_value={"base_url": "http://127.0.0.1:55231"},
                ):
            self._harness().setUpClass()
            self._harness().setUpClass()
        self.assertEqual(len(batch_calls), 1)


if __name__ == "__main__":
    unittest.main()
