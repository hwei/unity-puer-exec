import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import release_openupm  # type: ignore


def _completed(stdout="", stderr="", returncode=0):
    return mock.Mock(stdout=stdout, stderr=stderr, returncode=returncode)


class ReleaseOpenUpmToolTests(unittest.TestCase):
    def test_parser_accepts_release_options(self):
        parser = release_openupm.build_parser()

        args = parser.parse_args(
            [
                "--version",
                "1.2.3",
                "--commit",
                "--tag",
                "--dry-run",
                "--real-host-validation",
            ]
        )

        self.assertEqual(args.version, "1.2.3")
        self.assertTrue(args.commit)
        self.assertTrue(args.tag)
        self.assertTrue(args.dry_run)
        self.assertTrue(args.real_host_validation)

    def test_release_rewrites_package_version_and_runs_default_unit_suite(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            package_json_path = Path(temp_dir) / "package.json"
            package_json_path.write_text(
                json.dumps({"name": "com.txcombo.unity-puer-exec", "version": "0.0.1"}) + "\n",
                encoding="utf-8",
            )

            command_log = []

            def fake_run(command, cwd, capture_output, text, env=None, check=False):
                command_log.append((tuple(command), env))
                if command[:3] == ["git", "status", "--porcelain"]:
                    return _completed(stdout="")
                if command[:5] == ["git", "rev-parse", "-q", "--verify", "refs/tags/v0.2.0"]:
                    return _completed(returncode=1)
                if command[:4] == ["git", "remote", "get-url", "origin"]:
                    return _completed(stdout="https://example.invalid/repo.git\n")
                if command[:4] == ["git", "ls-remote", "--tags", "origin"]:
                    return _completed(stdout="")
                if command[:3] == [sys.executable, "-m", "unittest"]:
                    return _completed(stdout="ok\n")
                raise AssertionError("Unexpected command: {}".format(command))

            with mock.patch.object(release_openupm, "PACKAGE_JSON_PATH", package_json_path):
                with mock.patch("release_openupm.subprocess.run", side_effect=fake_run):
                    result = release_openupm.perform_release("0.2.0")

            package_json = json.loads(package_json_path.read_text(encoding="utf-8"))
            self.assertEqual(package_json["version"], "0.2.0")
            self.assertEqual(result["status"], "prepared")
            self.assertEqual(
                [entry for entry in result["executed_actions"] if "unit release test suite" in entry],
                ["Ran default mocked/unit release test suite."],
            )
            self.assertTrue(
                any(command[:3] == (sys.executable, "-m", "unittest") for command, _ in command_log)
            )

    def test_dirty_worktree_refuses_before_package_edit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            package_json_path = Path(temp_dir) / "package.json"
            original = {"name": "com.txcombo.unity-puer-exec", "version": "0.0.1"}
            package_json_path.write_text(json.dumps(original) + "\n", encoding="utf-8")

            def fake_run(command, cwd, capture_output, text, env=None, check=False):
                if command[:3] == ["git", "status", "--porcelain"]:
                    return _completed(stdout=" M tools/release_openupm.py\n")
                raise AssertionError("Unexpected command: {}".format(command))

            with mock.patch.object(release_openupm, "PACKAGE_JSON_PATH", package_json_path):
                with mock.patch("release_openupm.subprocess.run", side_effect=fake_run):
                    with self.assertRaises(release_openupm.ReleaseError) as exc:
                        release_openupm.perform_release("0.2.0")

            package_json = json.loads(package_json_path.read_text(encoding="utf-8"))
            self.assertEqual(package_json["version"], "0.0.1")
            self.assertIn("clean working tree", str(exc.exception))

    def test_duplicate_local_tag_refuses_before_package_edit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            package_json_path = Path(temp_dir) / "package.json"
            package_json_path.write_text(
                json.dumps({"name": "com.txcombo.unity-puer-exec", "version": "0.0.1"}) + "\n",
                encoding="utf-8",
            )

            def fake_run(command, cwd, capture_output, text, env=None, check=False):
                if command[:3] == ["git", "status", "--porcelain"]:
                    return _completed(stdout="")
                if command[:5] == ["git", "rev-parse", "-q", "--verify", "refs/tags/v0.2.0"]:
                    return _completed(stdout="abc123\n", returncode=0)
                raise AssertionError("Unexpected command: {}".format(command))

            with mock.patch.object(release_openupm, "PACKAGE_JSON_PATH", package_json_path):
                with mock.patch("release_openupm.subprocess.run", side_effect=fake_run):
                    with self.assertRaises(release_openupm.ReleaseError) as exc:
                        release_openupm.perform_release("0.2.0")

            self.assertIn("already exists locally", str(exc.exception))
            package_json = json.loads(package_json_path.read_text(encoding="utf-8"))
            self.assertEqual(package_json["version"], "0.0.1")

    def test_duplicate_remote_tag_refuses_before_package_edit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            package_json_path = Path(temp_dir) / "package.json"
            package_json_path.write_text(
                json.dumps({"name": "com.txcombo.unity-puer-exec", "version": "0.0.1"}) + "\n",
                encoding="utf-8",
            )

            def fake_run(command, cwd, capture_output, text, env=None, check=False):
                if command[:3] == ["git", "status", "--porcelain"]:
                    return _completed(stdout="")
                if command[:5] == ["git", "rev-parse", "-q", "--verify", "refs/tags/v0.2.0"]:
                    return _completed(returncode=1)
                if command[:4] == ["git", "remote", "get-url", "origin"]:
                    return _completed(stdout="https://example.invalid/repo.git\n")
                if command[:4] == ["git", "ls-remote", "--tags", "origin"]:
                    return _completed(stdout="abc123\trefs/tags/v0.2.0\n")
                raise AssertionError("Unexpected command: {}".format(command))

            with mock.patch.object(release_openupm, "PACKAGE_JSON_PATH", package_json_path):
                with mock.patch("release_openupm.subprocess.run", side_effect=fake_run):
                    with self.assertRaises(release_openupm.ReleaseError) as exc:
                        release_openupm.perform_release("0.2.0")

            self.assertIn("already exists on origin", str(exc.exception))
            package_json = json.loads(package_json_path.read_text(encoding="utf-8"))
            self.assertEqual(package_json["version"], "0.0.1")

    def test_tag_requires_commit(self):
        with self.assertRaises(release_openupm.ReleaseError) as exc:
            release_openupm.perform_release("0.2.0", create_tag=True)

        self.assertIn("--commit", str(exc.exception))

    def test_dry_run_reports_plan_without_state_change_or_test_execution(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            package_json_path = Path(temp_dir) / "package.json"
            package_json_path.write_text(
                json.dumps({"name": "com.txcombo.unity-puer-exec", "version": "0.0.1"}) + "\n",
                encoding="utf-8",
            )

            command_log = []

            def fake_run(command, cwd, capture_output, text, env=None, check=False):
                command_log.append(tuple(command))
                if command[:3] == ["git", "status", "--porcelain"]:
                    return _completed(stdout="")
                if command[:5] == ["git", "rev-parse", "-q", "--verify", "refs/tags/v0.2.0"]:
                    return _completed(returncode=1)
                if command[:4] == ["git", "remote", "get-url", "origin"]:
                    return _completed(stdout="https://example.invalid/repo.git\n")
                if command[:4] == ["git", "ls-remote", "--tags", "origin"]:
                    return _completed(stdout="")
                raise AssertionError("Unexpected command: {}".format(command))

            with mock.patch.object(release_openupm, "PACKAGE_JSON_PATH", package_json_path):
                with mock.patch("release_openupm.subprocess.run", side_effect=fake_run):
                    result = release_openupm.perform_release(
                        "0.2.0",
                        create_commit=True,
                        create_tag=True,
                        dry_run=True,
                    )

            package_json = json.loads(package_json_path.read_text(encoding="utf-8"))
            self.assertEqual(package_json["version"], "0.0.1")
            self.assertEqual(result["status"], "dry-run")
            self.assertEqual(result["executed_actions"], [])
            self.assertTrue(any("Create local git commit" in action for action in result["planned_actions"]))
            self.assertTrue(any("Create local git tag v0.2.0." == action for action in result["planned_actions"]))
            self.assertFalse(any(command[:3] == (sys.executable, "-m", "unittest") for command in command_log))

    def test_real_host_validation_is_opt_in_in_plan_and_execution(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            package_json_path = Path(temp_dir) / "package.json"
            package_json_path.write_text(
                json.dumps({"name": "com.txcombo.unity-puer-exec", "version": "0.0.1"}) + "\n",
                encoding="utf-8",
            )

            command_log = []

            def fake_run(command, cwd, capture_output, text, env=None, check=False):
                command_log.append((tuple(command), env))
                if command[:3] == ["git", "status", "--porcelain"]:
                    return _completed(stdout="")
                if command[:5] == ["git", "rev-parse", "-q", "--verify", "refs/tags/v0.2.0"]:
                    return _completed(returncode=1)
                if command[:4] == ["git", "remote", "get-url", "origin"]:
                    return _completed(stdout="https://example.invalid/repo.git\n")
                if command[:4] == ["git", "ls-remote", "--tags", "origin"]:
                    return _completed(stdout="")
                if command[:3] == [sys.executable, "-m", "unittest"]:
                    return _completed(stdout="ok\n")
                raise AssertionError("Unexpected command: {}".format(command))

            with mock.patch.object(release_openupm, "PACKAGE_JSON_PATH", package_json_path):
                with mock.patch("release_openupm.subprocess.run", side_effect=fake_run):
                    dry_result = release_openupm.perform_release("0.2.0", dry_run=True)
                    real_host_result = release_openupm.perform_release(
                        "0.2.0",
                        real_host_validation=True,
                    )

            self.assertFalse(dry_result["real_host_validation"]["enabled"])
            self.assertTrue(real_host_result["real_host_validation"]["enabled"])
            real_host_test_calls = [
                (command, env)
                for command, env in command_log
                if command[:4] == (sys.executable, "-m", "unittest", release_openupm.REAL_HOST_TEST_MODULE)
            ]
            self.assertEqual(len(real_host_test_calls), 1)
            self.assertEqual(real_host_test_calls[0][1][release_openupm.REAL_HOST_ENV], "1")

    def test_failed_tests_restore_original_version_before_commit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            package_json_path = Path(temp_dir) / "package.json"
            package_json_path.write_text(
                json.dumps({"name": "com.txcombo.unity-puer-exec", "version": "0.0.1"}) + "\n",
                encoding="utf-8",
            )

            def fake_run(command, cwd, capture_output, text, env=None, check=False):
                if command[:3] == ["git", "status", "--porcelain"]:
                    return _completed(stdout="")
                if command[:5] == ["git", "rev-parse", "-q", "--verify", "refs/tags/v0.2.0"]:
                    return _completed(returncode=1)
                if command[:4] == ["git", "remote", "get-url", "origin"]:
                    return _completed(stdout="https://example.invalid/repo.git\n")
                if command[:4] == ["git", "ls-remote", "--tags", "origin"]:
                    return _completed(stdout="")
                if command[:3] == [sys.executable, "-m", "unittest"]:
                    return _completed(returncode=1, stderr="boom\n")
                raise AssertionError("Unexpected command: {}".format(command))

            with mock.patch.object(release_openupm, "PACKAGE_JSON_PATH", package_json_path):
                with mock.patch("release_openupm.subprocess.run", side_effect=fake_run):
                    with self.assertRaises(release_openupm.ReleaseError):
                        release_openupm.perform_release("0.2.0")

            package_json = json.loads(package_json_path.read_text(encoding="utf-8"))
            self.assertEqual(package_json["version"], "0.0.1")


if __name__ == "__main__":
    unittest.main()
