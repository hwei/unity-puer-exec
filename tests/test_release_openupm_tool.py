import contextlib
import json
import os
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


PACKAGE_NAME = "com.txcombo.unity-puer-exec"
BASE_PACKAGE_FILES = {
    "README.md": "# Unity Puer Exec\n\nPackage readme.\n",
    "Editor/UnityPuerExecServer.cs": "// server\n",
}


def _completed(stdout="", stderr="", returncode=0):
    return mock.Mock(stdout=stdout, stderr=stderr, returncode=returncode)


def _package_json_text(version, line_ending="\n"):
    document = {
        "name": PACKAGE_NAME,
        "displayName": "Unity Puer Exec",
        "version": version,
        "unity": "2022.3",
        "description": "Editor package for driving a Puerts host from an external CLI.",
    }
    return json.dumps(document, indent=2).replace("\n", line_ending) + line_ending


def _build_package_tree(package_root, version, line_ending="\n", extra_files=None):
    package_root.mkdir(parents=True, exist_ok=True)
    files = dict(BASE_PACKAGE_FILES)
    files.update(extra_files or {})
    for relative_path, content in files.items():
        target = package_root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        normalised = content.replace("\r\n", "\n").replace("\n", line_ending)
        target.write_bytes(normalised.encode("utf-8"))
    package_json_path = package_root / "package.json"
    package_json_path.write_bytes(_package_json_text(version, line_ending).encode("utf-8"))
    return package_root


def _make_repo_package(temp_dir, version="0.0.1", extra_files=None):
    return _build_package_tree(
        Path(temp_dir) / "repo" / "packages" / PACKAGE_NAME,
        version,
        extra_files=extra_files,
    )


def _make_host(temp_dir, dependencies=None, embedded_packages=()):
    """Build a fake validation host project.

    ``embedded_packages`` is a sequence of ``(directory_name, version,
    line_ending)`` triples; each becomes an immediate child of ``Packages/``
    declaring the formal package name.
    """
    project_path = Path(temp_dir) / "host" / "Project"
    packages_path = project_path / "Packages"
    packages_path.mkdir(parents=True, exist_ok=True)
    (packages_path / "manifest.json").write_bytes(
        json.dumps({"dependencies": dependencies or {}}, indent=2).encode("utf-8")
    )
    for directory_name, version, line_ending in embedded_packages:
        _build_package_tree(
            packages_path / directory_name, version, line_ending=line_ending
        )
    return project_path


def _file_dependency_value(project_path, target_package_root):
    relative = os.path.relpath(
        str(target_package_root), str(project_path / "Packages")
    ).replace("\\", "/")
    return "file:{}".format(relative)


def _absolute_file_dependency_value(target_package_root):
    return "file:///{}".format(target_package_root.as_posix().lstrip("/"))


@contextlib.contextmanager
def _host_project(project_path):
    with mock.patch.dict(os.environ, {"UNITY_PROJECT_PATH": str(project_path)}):
        yield


def _resolved_path_text(path):
    """The path text the helper reports, which always resolves the host."""
    return str(Path(path).resolve())


def _unittest_calls(command_log):
    return [
        command
        for command, _env in command_log
        if command[:3] == (sys.executable, "-m", "unittest")
    ]


@contextlib.contextmanager
def _repo_package(package_root):
    with mock.patch.object(
        release_openupm, "PACKAGE_JSON_PATH", package_root / "package.json"
    ):
        yield


def _git_runner(command_log=None, test_returncode=0, tag_name="v0.2.0"):
    """Replacement for ``subprocess.run`` covering the release helper's commands."""

    def fake_run(command, cwd, capture_output, text, env=None, check=False):
        if command_log is not None:
            command_log.append((tuple(command), env))
        if command[:3] == ["git", "status", "--porcelain"]:
            return _completed(stdout="")
        if command[:5] == ["git", "rev-parse", "-q", "--verify", "refs/tags/{}".format(tag_name)]:
            return _completed(returncode=1)
        if command[:4] == ["git", "remote", "get-url", "origin"]:
            return _completed(stdout="https://example.invalid/repo.git\n")
        if command[:4] == ["git", "ls-remote", "--tags", "origin"]:
            return _completed(stdout="")
        if command[:3] == [sys.executable, "-m", "unittest"]:
            return _completed(stdout="ok\n", returncode=test_returncode)
        raise AssertionError("Unexpected command: {}".format(command))

    return fake_run


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
            project_path = _make_host(
                temp_dir,
                embedded_packages=[(PACKAGE_NAME, "0.2.0", "\n")],
            )

            command_log = []
            fake_run = _git_runner(command_log=command_log)

            with mock.patch.object(release_openupm, "PACKAGE_JSON_PATH", package_json_path):
                with mock.patch("release_openupm.subprocess.run", side_effect=fake_run):
                    with _host_project(project_path):
                        dry_result = release_openupm.perform_release("0.2.0", dry_run=True)
                        real_host_result = release_openupm.perform_release(
                            "0.2.0",
                            real_host_validation=True,
                        )

            self.assertFalse(dry_result["real_host_validation"]["enabled"])
            self.assertTrue(real_host_result["real_host_validation"]["enabled"])
            self.assertEqual(
                real_host_result["real_host_validation"]["host_package"]["observed_version"],
                "0.2.0",
            )
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


class HostPackagePreflightTests(unittest.TestCase):
    CANDIDATE = "0.2.0"
    CURRENT = "0.0.1"

    def _assert_refusal(self, code, project_path, call, expected_fragments=()):
        with _host_project(project_path):
            with self.assertRaises(release_openupm.ReleaseError) as exc:
                call()
        message = str(exc.exception)
        self.assertTrue(message.startswith(code + ":"), message)
        for fragment in expected_fragments:
            self.assertIn(fragment, message)
        return message

    def test_embedded_copy_declaring_candidate_version_passes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_package = _make_repo_package(temp_dir, self.CURRENT)
            project_path = _make_host(
                temp_dir, embedded_packages=[(PACKAGE_NAME, self.CANDIDATE, "\n")]
            )

            with _repo_package(repo_package):
                with _host_project(project_path):
                    verdict = release_openupm.evaluate_host_package(self.CANDIDATE)

            self.assertTrue(verdict["ok"])
            self.assertEqual(verdict["loaded_via"], "embedded")
            self.assertEqual(verdict["identity"], "host_copy")
            self.assertEqual(verdict["observed_version"], self.CANDIDATE)
            self.assertEqual(verdict["expected_version"], self.CANDIDATE)
            self.assertEqual(verdict["alignment_status"], "not_requested")
            self.assertIsNone(verdict["parity"])

    def test_embedded_copy_declaring_older_version_refuses(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_package = _make_repo_package(temp_dir, self.CURRENT)
            project_path = _make_host(
                temp_dir, embedded_packages=[(PACKAGE_NAME, "0.1.0", "\n")]
            )

            with _repo_package(repo_package):
                self._assert_refusal(
                    "host_package_version_mismatch",
                    project_path,
                    lambda: release_openupm.evaluate_host_package(self.CANDIDATE),
                    expected_fragments=("0.1.0", self.CANDIDATE, _resolved_path_text(project_path)),
                )

    def test_embedded_copy_with_code_drift_refuses_as_stale(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_package = _make_repo_package(
                temp_dir,
                self.CURRENT,
                extra_files={"Editor/NewBehaviour.cs": "// new\n"},
            )
            project_path = _make_host(
                temp_dir, embedded_packages=[(PACKAGE_NAME, "0.1.0", "\n")]
            )

            with _repo_package(repo_package):
                self._assert_refusal(
                    "host_package_stale",
                    project_path,
                    lambda: release_openupm.evaluate_host_package(
                        self.CANDIDATE, sync_requested=True
                    ),
                    expected_fragments=("Editor/NewBehaviour.cs",),
                )

    def test_embedded_copy_file_in_new_top_level_directory_refuses_as_stale(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_package = _make_repo_package(
                temp_dir,
                self.CURRENT,
                extra_files={"Runtime/UnityPuerExecRuntime.cs": "// runtime\n"},
            )
            project_path = _make_host(
                temp_dir, embedded_packages=[(PACKAGE_NAME, "0.1.0", "\n")]
            )

            with _repo_package(repo_package):
                self._assert_refusal(
                    "host_package_stale",
                    project_path,
                    lambda: release_openupm.evaluate_host_package(
                        self.CANDIDATE, sync_requested=True
                    ),
                    expected_fragments=("Runtime/UnityPuerExecRuntime.cs",),
                )

    def test_crlf_only_drift_passes_parity(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_package = _make_repo_package(temp_dir, self.CURRENT)
            project_path = _make_host(
                temp_dir, embedded_packages=[(PACKAGE_NAME, "0.1.0", "\r\n")]
            )

            with _repo_package(repo_package):
                with _host_project(project_path):
                    verdict = release_openupm.evaluate_host_package(
                        self.CANDIDATE, sync_requested=True
                    )

            self.assertTrue(verdict["parity"]["ok"])
            self.assertEqual(verdict["parity"]["difference_count"], 0)
            self.assertEqual(verdict["alignment_status"], "would_align")

    def test_relative_file_dependency_on_repository_needs_no_version_read(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_package = _make_repo_package(temp_dir, self.CURRENT)
            project_path = Path(temp_dir) / "host" / "Project"
            project_path = _make_host(
                temp_dir,
                dependencies={
                    PACKAGE_NAME: _file_dependency_value(project_path, repo_package)
                },
            )

            with _repo_package(repo_package):
                with _host_project(project_path):
                    with mock.patch.object(
                        release_openupm,
                        "_read_declared_version",
                        side_effect=AssertionError("version must not be read"),
                    ):
                        verdict = release_openupm.evaluate_host_package(self.CANDIDATE)

            self.assertTrue(verdict["ok"])
            self.assertEqual(verdict["loaded_via"], "file")
            self.assertEqual(verdict["identity"], "repository_package")
            self.assertIsNone(verdict["observed_version"])
            self.assertEqual(verdict["alignment_status"], "not_requested")

    def test_absolute_file_dependency_on_repository_is_recognised(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_package = _make_repo_package(temp_dir, self.CURRENT)
            project_path = _make_host(
                temp_dir,
                dependencies={
                    PACKAGE_NAME: _absolute_file_dependency_value(repo_package)
                },
            )

            with _repo_package(repo_package):
                with _host_project(project_path):
                    verdict = release_openupm.evaluate_host_package(self.CANDIDATE)

            self.assertEqual(verdict["identity"], "repository_package")
            self.assertTrue(verdict["ok"])

    def test_file_dependency_on_other_copy_compares_versions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_package = _make_repo_package(temp_dir, self.CURRENT)
            other_copy = _build_package_tree(Path(temp_dir) / "elsewhere" / PACKAGE_NAME, "0.1.0")
            project_path = _make_host(
                temp_dir,
                dependencies={PACKAGE_NAME: _file_dependency_value(Path(temp_dir) / "host" / "Project", other_copy)},
            )

            with _repo_package(repo_package):
                self._assert_refusal(
                    "host_package_version_mismatch",
                    project_path,
                    lambda: release_openupm.evaluate_host_package(self.CANDIDATE),
                    expected_fragments=("0.1.0", _resolved_path_text(other_copy)),
                )

    def test_host_without_wiring_refuses(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_package = _make_repo_package(temp_dir, self.CURRENT)
            project_path = _make_host(
                temp_dir, dependencies={PACKAGE_NAME: "0.1.0"}
            )

            with _repo_package(repo_package):
                self._assert_refusal(
                    "host_package_not_wired",
                    project_path,
                    lambda: release_openupm.evaluate_host_package(self.CANDIDATE),
                )

    def test_two_embedded_copies_refuse_as_ambiguous(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_package = _make_repo_package(temp_dir, self.CURRENT)
            project_path = _make_host(
                temp_dir,
                embedded_packages=[
                    ("com.txcombo.unity-puer-exec", self.CANDIDATE, "\n"),
                    ("com.txcombo.unity-puer-exec.bak", self.CANDIDATE, "\n"),
                ],
            )

            with _repo_package(repo_package):
                message = self._assert_refusal(
                    "host_package_ambiguous",
                    project_path,
                    lambda: release_openupm.evaluate_host_package(self.CANDIDATE),
                )

            self.assertIn("com.txcombo.unity-puer-exec.bak", message)

    def test_unresolvable_host_refuses(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_package = _make_repo_package(temp_dir, self.CURRENT)

            with _repo_package(repo_package):
                with mock.patch.object(
                    release_openupm.prepare_validation_host,
                    "resolve_project_path",
                    side_effect=ValueError("Validation host project path is required."),
                ):
                    with self.assertRaises(release_openupm.ReleaseError) as exc:
                        release_openupm.evaluate_host_package(self.CANDIDATE)

            self.assertTrue(str(exc.exception).startswith("host_project_unavailable:"))

    def test_missing_host_directory_refuses(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_package = _make_repo_package(temp_dir, self.CURRENT)
            missing_project = Path(temp_dir) / "absent" / "Project"

            with _repo_package(repo_package):
                self._assert_refusal(
                    "host_project_unavailable",
                    missing_project,
                    lambda: release_openupm.evaluate_host_package(self.CANDIDATE),
                )

    def test_host_without_manifest_refuses(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_package = _make_repo_package(temp_dir, self.CURRENT)
            project_path = Path(temp_dir) / "host" / "Project"
            (project_path / "Packages").mkdir(parents=True)

            with _repo_package(repo_package):
                self._assert_refusal(
                    "host_project_unavailable",
                    project_path,
                    lambda: release_openupm.evaluate_host_package(self.CANDIDATE),
                )


class HostPackageAlignmentTests(unittest.TestCase):
    CANDIDATE = "0.2.0"
    CURRENT = "0.0.1"

    def test_alignment_preserves_every_other_byte_including_crlf(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_package = _make_repo_package(temp_dir, self.CURRENT)
            project_path = _make_host(
                temp_dir, embedded_packages=[(PACKAGE_NAME, "0.1.0", "\r\n")]
            )
            host_package_json = project_path / "Packages" / PACKAGE_NAME / "package.json"
            original_bytes = host_package_json.read_bytes()

            with _repo_package(repo_package):
                with _host_project(project_path):
                    with mock.patch(
                        "release_openupm.subprocess.run", side_effect=_git_runner()
                    ):
                        result = release_openupm.perform_release(
                            self.CANDIDATE, real_host_validation=True, sync_host_version=True
                        )

            aligned_bytes = host_package_json.read_bytes()
            self.assertIn(b"\r\n", aligned_bytes)
            self.assertEqual(
                aligned_bytes,
                original_bytes.replace(b'"version": "0.1.0"', b'"version": "0.2.0"'),
            )
            self.assertIn(
                "Aligned host package version at {} from 0.1.0 to 0.2.0.".format(
                    _resolved_path_text(project_path / "Packages" / PACKAGE_NAME)
                ),
                result["executed_actions"],
            )
            self.assertEqual(
                result["real_host_validation"]["host_package"]["alignment_status"], "aligned"
            )

    def test_file_wired_host_needs_no_version_write(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_package = _make_repo_package(temp_dir, self.CURRENT)
            project_path = Path(temp_dir) / "host" / "Project"
            project_path = _make_host(
                temp_dir,
                dependencies={
                    PACKAGE_NAME: _file_dependency_value(project_path, repo_package)
                },
            )
            repo_package_json = repo_package / "package.json"
            repo_bytes_before = repo_package_json.read_bytes()

            with _repo_package(repo_package):
                with _host_project(project_path):
                    with mock.patch.object(
                        release_openupm, "align_host_package_version"
                    ) as align:
                        with mock.patch(
                            "release_openupm.subprocess.run", side_effect=_git_runner()
                        ):
                            result = release_openupm.perform_release(
                                self.CANDIDATE,
                                real_host_validation=True,
                                sync_host_version=True,
                            )

            align.assert_not_called()
            self.assertNotEqual(repo_package_json.read_bytes(), repo_bytes_before)
            self.assertEqual(read_version(repo_package), self.CANDIDATE)
            host_package = result["real_host_validation"]["host_package"]
            self.assertEqual(host_package["identity"], "repository_package")
            self.assertEqual(host_package["alignment_status"], "not_needed")

    def test_alignment_requires_real_host_validation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_package = _make_repo_package(temp_dir, self.CURRENT)

            with _repo_package(repo_package):
                with mock.patch.object(
                    release_openupm, "align_host_package_version"
                ) as align:
                    with mock.patch(
                        "release_openupm.subprocess.run", side_effect=_git_runner()
                    ):
                        with self.assertRaises(release_openupm.ReleaseError) as exc:
                            release_openupm.perform_release(
                                self.CANDIDATE, sync_host_version=True
                            )

            self.assertIn("--real-host-validation", str(exc.exception))
            align.assert_not_called()

    def test_release_without_real_host_validation_never_touches_the_host(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_package = _make_repo_package(temp_dir, self.CURRENT)
            project_path = _make_host(
                temp_dir, embedded_packages=[(PACKAGE_NAME, "0.1.0", "\n")]
            )
            host_package_json = project_path / "Packages" / PACKAGE_NAME / "package.json"
            original_bytes = host_package_json.read_bytes()

            with _repo_package(repo_package):
                with _host_project(project_path):
                    with mock.patch(
                        "release_openupm.subprocess.run", side_effect=_git_runner()
                    ):
                        release_openupm.perform_release(self.CANDIDATE)

            self.assertEqual(host_package_json.read_bytes(), original_bytes)

    def test_parity_refusal_names_paths_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_package = _make_repo_package(
                temp_dir,
                self.CURRENT,
                extra_files={"Editor/NewBehaviour.cs": "// new\n"},
            )
            project_path = _make_host(
                temp_dir, embedded_packages=[(PACKAGE_NAME, "0.1.0", "\n")]
            )
            host_package_json = project_path / "Packages" / PACKAGE_NAME / "package.json"
            original_bytes = host_package_json.read_bytes()
            command_log = []

            with _repo_package(repo_package):
                with _host_project(project_path):
                    with mock.patch(
                        "release_openupm.subprocess.run",
                        side_effect=_git_runner(command_log=command_log),
                    ):
                        with self.assertRaises(release_openupm.ReleaseError) as exc:
                            release_openupm.perform_release(
                                self.CANDIDATE,
                                real_host_validation=True,
                                sync_host_version=True,
                            )

            self.assertIn("Editor/NewBehaviour.cs", str(exc.exception))
            self.assertEqual(host_package_json.read_bytes(), original_bytes)
            self.assertEqual(read_version(repo_package), self.CURRENT)
            self.assertEqual(_unittest_calls(command_log), [])

    def test_release_error_after_alignment_restores_both_sides(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_package = _make_repo_package(temp_dir, self.CURRENT)
            project_path = _make_host(
                temp_dir, embedded_packages=[(PACKAGE_NAME, "0.1.0", "\n")]
            )
            host_package_json = project_path / "Packages" / PACKAGE_NAME / "package.json"
            original_bytes = host_package_json.read_bytes()

            with _repo_package(repo_package):
                with _host_project(project_path):
                    with mock.patch(
                        "release_openupm.subprocess.run",
                        side_effect=_git_runner(test_returncode=1),
                    ):
                        with self.assertRaises(release_openupm.ReleaseError):
                            release_openupm.perform_release(
                                self.CANDIDATE,
                                real_host_validation=True,
                                sync_host_version=True,
                            )

            self.assertEqual(host_package_json.read_bytes(), original_bytes)
            self.assertEqual(read_version(repo_package), self.CURRENT)

    def test_keyboard_interrupt_after_alignment_restores_both_sides(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_package = _make_repo_package(temp_dir, self.CURRENT)
            project_path = _make_host(
                temp_dir, embedded_packages=[(PACKAGE_NAME, "0.1.0", "\n")]
            )
            host_package_json = project_path / "Packages" / PACKAGE_NAME / "package.json"
            original_bytes = host_package_json.read_bytes()

            with _repo_package(repo_package):
                with _host_project(project_path):
                    with mock.patch(
                        "release_openupm.subprocess.run", side_effect=_git_runner()
                    ):
                        with mock.patch.object(
                            release_openupm,
                            "run_python_module_tests",
                            side_effect=KeyboardInterrupt(),
                        ):
                            with self.assertRaises(KeyboardInterrupt):
                                release_openupm.perform_release(
                                    self.CANDIDATE,
                                    real_host_validation=True,
                                    sync_host_version=True,
                                )

            self.assertEqual(host_package_json.read_bytes(), original_bytes)
            self.assertEqual(read_version(repo_package), self.CURRENT)

    def test_dry_run_reports_identity_and_parity_without_writes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_package = _make_repo_package(temp_dir, self.CURRENT)
            project_path = _make_host(
                temp_dir, embedded_packages=[(PACKAGE_NAME, "0.1.0", "\r\n")]
            )
            host_package_json = project_path / "Packages" / PACKAGE_NAME / "package.json"
            original_host_bytes = host_package_json.read_bytes()
            original_repo_bytes = (repo_package / "package.json").read_bytes()
            command_log = []

            with _repo_package(repo_package):
                with _host_project(project_path):
                    with mock.patch(
                        "release_openupm.subprocess.run",
                        side_effect=_git_runner(command_log=command_log),
                    ):
                        result = release_openupm.perform_release(
                            self.CANDIDATE,
                            dry_run=True,
                            real_host_validation=True,
                            sync_host_version=True,
                        )

            host_package = result["real_host_validation"]["host_package"]
            self.assertEqual(result["status"], "dry-run")
            self.assertEqual(host_package["loaded_via"], "embedded")
            self.assertEqual(host_package["identity"], "host_copy")
            self.assertEqual(host_package["observed_version"], "0.1.0")
            self.assertEqual(host_package["expected_version"], self.CANDIDATE)
            self.assertTrue(host_package["parity"]["ok"])
            self.assertEqual(host_package["alignment_status"], "would_align")
            self.assertTrue(
                any(action.startswith("Align host package version") for action in result["planned_actions"])
            )
            self.assertEqual(result["executed_actions"], [])
            self.assertEqual(host_package_json.read_bytes(), original_host_bytes)
            self.assertEqual((repo_package / "package.json").read_bytes(), original_repo_bytes)
            self.assertEqual(_unittest_calls(command_log), [])


def read_version(package_root):
    return json.loads((Path(package_root) / "package.json").read_text(encoding="utf-8"))["version"]


if __name__ == "__main__":
    unittest.main()
