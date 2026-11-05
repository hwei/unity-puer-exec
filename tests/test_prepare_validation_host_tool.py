import datetime
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import prepare_validation_host  # type: ignore


def _write_embedded_package(directory_path, package_name):
    directory_path.mkdir(parents=True, exist_ok=True)
    (directory_path / "package.json").write_text(
        json.dumps({"name": package_name, "version": "0.0.0"}),
        encoding="utf-8",
    )
    return directory_path


def _same_anchor_manifest_path(package_root):
    return Path(package_root.anchor) / "validation-host" / "Project" / "Packages" / "manifest.json"


class PrepareValidationHostTests(unittest.TestCase):
    def test_compute_file_dependency_uses_reproducible_relative_path(self):
        package_root = prepare_validation_host.FORMAL_PACKAGE_ROOT
        manifest_path = _same_anchor_manifest_path(package_root)
        expected_dependency = "file:{}".format(
            os.path.relpath(package_root, manifest_path.parent).replace("\\", "/")
        )

        dependency = prepare_validation_host.compute_file_dependency(
            manifest_path,
            package_root=package_root,
        )

        self.assertEqual(dependency, expected_dependency)

    def test_compute_file_dependency_falls_back_to_absolute_file_url_across_windows_volumes(self):
        manifest_path = Path("F:/validation-host/Project/Packages/manifest.json")
        package_root = Path("D:/repo/packages/com.txcombo.unity-puer-exec")

        dependency = prepare_validation_host.compute_file_dependency(
            manifest_path,
            package_root=package_root,
        )

        self.assertEqual(dependency, "file:///D:/repo/packages/com.txcombo.unity-puer-exec")

    def test_rewrite_manifest_replaces_legacy_embedded_package(self):
        package_root = prepare_validation_host.FORMAL_PACKAGE_ROOT
        manifest_path = _same_anchor_manifest_path(package_root)
        expected_dependency = "file:{}".format(
            os.path.relpath(package_root, manifest_path.parent).replace("\\", "/")
        )
        manifest = {
            "dependencies": {
                "com.c3.unity-puer-exec.validation": "file:com.c3.unity-puer-exec.validation",
                "com.cysharp.unitask": "file:com.cysharp.unitask",
            },
            "scopedRegistries": [],
        }

        rewritten, changed, dependency = prepare_validation_host.rewrite_manifest(
            manifest,
            manifest_path,
            package_root=package_root,
        )

        self.assertTrue(changed)
        self.assertEqual(dependency, expected_dependency)
        self.assertNotIn("com.c3.unity-puer-exec.validation", rewritten["dependencies"])
        self.assertEqual(
            rewritten["dependencies"]["com.txcombo.unity-puer-exec"],
            expected_dependency,
        )
        self.assertEqual(rewritten["dependencies"]["com.cysharp.unitask"], "file:com.cysharp.unitask")

    def test_rewrite_manifest_is_idempotent_for_formal_dependency(self):
        package_root = prepare_validation_host.FORMAL_PACKAGE_ROOT
        manifest_path = _same_anchor_manifest_path(package_root)
        expected_dependency = "file:{}".format(
            os.path.relpath(package_root, manifest_path.parent).replace("\\", "/")
        )
        manifest = {
            "dependencies": {
                "com.txcombo.unity-puer-exec": expected_dependency,
                "com.cysharp.unitask": "file:com.cysharp.unitask",
            },
            "testables": ["com.txcombo.unity-puer-exec"],
        }

        rewritten, changed, dependency = prepare_validation_host.rewrite_manifest(
            manifest,
            manifest_path,
            package_root=package_root,
        )

        self.assertFalse(changed)
        self.assertEqual(rewritten["dependencies"]["com.txcombo.unity-puer-exec"], expected_dependency)
        self.assertEqual(rewritten["testables"], ["com.txcombo.unity-puer-exec"])
        self.assertEqual(dependency, expected_dependency)

    def test_rewrite_manifest_declares_the_package_testable(self):
        # Unity compiles and discovers the package's own test assemblies only for a
        # package listed in testables, so the local wiring has to declare it. Without
        # the entry a batch test launch exits successfully having run nothing.
        package_root = prepare_validation_host.FORMAL_PACKAGE_ROOT
        manifest_path = _same_anchor_manifest_path(package_root)
        manifest = {
            "dependencies": {
                "com.txcombo.unity-puer-exec": prepare_validation_host.compute_file_dependency(
                    manifest_path, package_root=package_root
                )
            }
        }

        rewritten, changed, _ = prepare_validation_host.rewrite_manifest(
            manifest,
            manifest_path,
            package_root=package_root,
        )

        self.assertTrue(changed)
        self.assertEqual(rewritten["testables"], ["com.txcombo.unity-puer-exec"])

    def test_rewrite_manifest_preserves_existing_testables_entries(self):
        package_root = prepare_validation_host.FORMAL_PACKAGE_ROOT
        manifest_path = _same_anchor_manifest_path(package_root)
        manifest = {
            "dependencies": {
                "com.txcombo.unity-puer-exec": prepare_validation_host.compute_file_dependency(
                    manifest_path, package_root=package_root
                )
            },
            "testables": ["com.example.other"],
        }

        rewritten, changed, _ = prepare_validation_host.rewrite_manifest(
            manifest,
            manifest_path,
            package_root=package_root,
        )

        self.assertTrue(changed)
        self.assertEqual(rewritten["testables"], ["com.example.other", "com.txcombo.unity-puer-exec"])

    def test_ensure_testable_package_is_idempotent(self):
        manifest = {"testables": ["com.txcombo.unity-puer-exec"]}

        rewritten, changed = prepare_validation_host.ensure_testable_package(manifest)

        self.assertFalse(changed)
        self.assertIs(rewritten, manifest)

    def test_ensure_testable_package_rejects_a_non_list_testables(self):
        with self.assertRaises(ValueError):
            prepare_validation_host.ensure_testable_package(
                {"testables": "com.txcombo.unity-puer-exec"}
            )

    def test_detect_embedded_package_shadowing_reports_distinct_embedded_package(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "Project"
            manifest_path = project_path / "Packages" / "manifest.json"
            embedded_path = project_path / "Packages" / "com.txcombo.unity-puer-exec"
            package_root = Path(temp_dir) / "repo" / "packages" / "com.txcombo.unity-puer-exec"
            _write_embedded_package(embedded_path, "com.txcombo.unity-puer-exec")
            package_root.mkdir(parents=True)

            shadowing, path, paths = prepare_validation_host.detect_embedded_package_shadowing(
                manifest_path,
                package_root=package_root,
            )

            self.assertTrue(shadowing)
            self.assertEqual(path, str(embedded_path))
            self.assertEqual(paths, [str(embedded_path)])

    def test_detect_embedded_package_shadowing_reports_renamed_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "Project"
            manifest_path = project_path / "Packages" / "manifest.json"
            embedded_path = project_path / "Packages" / "com.txcombo.unity-puer-exec.bak"
            package_root = Path(temp_dir) / "repo" / "packages" / "com.txcombo.unity-puer-exec"
            _write_embedded_package(embedded_path, "com.txcombo.unity-puer-exec")
            package_root.mkdir(parents=True)

            shadowing, path, paths = prepare_validation_host.detect_embedded_package_shadowing(
                manifest_path,
                package_root=package_root,
            )

            self.assertTrue(shadowing)
            self.assertEqual(path, str(embedded_path))
            self.assertEqual(paths, [str(embedded_path)])

    def test_detect_embedded_package_shadowing_reports_every_shadowing_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "Project"
            manifest_path = project_path / "Packages" / "manifest.json"
            first_path = project_path / "Packages" / "com.txcombo.unity-puer-exec"
            second_path = project_path / "Packages" / "com.txcombo.unity-puer-exec.bak"
            package_root = Path(temp_dir) / "repo" / "packages" / "com.txcombo.unity-puer-exec"
            _write_embedded_package(first_path, "com.txcombo.unity-puer-exec")
            _write_embedded_package(second_path, "com.txcombo.unity-puer-exec")
            package_root.mkdir(parents=True)

            shadowing, path, paths = prepare_validation_host.detect_embedded_package_shadowing(
                manifest_path,
                package_root=package_root,
            )

            self.assertTrue(shadowing)
            self.assertEqual(path, str(first_path))
            self.assertEqual(sorted(paths), sorted([str(first_path), str(second_path)]))

    def test_detect_embedded_package_shadowing_is_false_when_embedded_package_absent(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "Project" / "Packages" / "manifest.json"
            package_root = Path(temp_dir) / "repo" / "packages" / "com.txcombo.unity-puer-exec"

            shadowing, path, paths = prepare_validation_host.detect_embedded_package_shadowing(
                manifest_path,
                package_root=package_root,
            )

            self.assertFalse(shadowing)
            self.assertIsNone(path)
            self.assertEqual(paths, [])

    def test_detect_embedded_package_shadowing_is_false_when_embedded_path_is_package_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "Project" / "Packages" / "manifest.json"
            package_root = manifest_path.parent / "com.txcombo.unity-puer-exec"
            _write_embedded_package(package_root, "com.txcombo.unity-puer-exec")

            shadowing, path, paths = prepare_validation_host.detect_embedded_package_shadowing(
                manifest_path,
                package_root=package_root,
            )

            self.assertFalse(shadowing)
            self.assertIsNone(path)
            self.assertEqual(paths, [])

    def test_detect_embedded_package_shadowing_ignores_unrelated_directories(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "Project"
            packages_path = project_path / "Packages"
            manifest_path = packages_path / "manifest.json"
            package_root = Path(temp_dir) / "repo" / "packages" / "com.txcombo.unity-puer-exec"
            package_root.mkdir(parents=True)

            _write_embedded_package(packages_path / "com.example.other", "com.example.other")
            (packages_path / "no-package-json").mkdir(parents=True)
            malformed_path = packages_path / "malformed"
            malformed_path.mkdir(parents=True)
            (malformed_path / "package.json").write_text("{ not json", encoding="utf-8")

            shadowing, path, paths = prepare_validation_host.detect_embedded_package_shadowing(
                manifest_path,
                package_root=package_root,
            )

            self.assertFalse(shadowing)
            self.assertIsNone(path)
            self.assertEqual(paths, [])

    def test_main_reports_embedded_package_shadowing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "Project"
            packages_path = project_path / "Packages"
            embedded_path = packages_path / "com.txcombo.unity-puer-exec"
            package_root = Path(temp_dir) / "repo" / "packages" / "com.txcombo.unity-puer-exec"
            packages_path.mkdir(parents=True)
            _write_embedded_package(embedded_path, "com.txcombo.unity-puer-exec")
            package_root.mkdir(parents=True)
            manifest_path = packages_path / "manifest.json"
            manifest_path.write_text(json.dumps({"dependencies": {}}), encoding="utf-8")

            with mock.patch.object(prepare_validation_host, "FORMAL_PACKAGE_ROOT", package_root):
                stdout = StringIO()
                with redirect_stdout(stdout):
                    exit_code = prepare_validation_host.main(["--project-path", str(project_path)])

            self.assertEqual(exit_code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertTrue(payload["package_testable"])
            self.assertEqual(payload["testables"], ["com.txcombo.unity-puer-exec"])
            self.assertTrue(payload["embedded_package_shadowing"])
            self.assertTrue(payload["embedded_package_path"].endswith("Project\\Packages\\com.txcombo.unity-puer-exec"))
            self.assertEqual(payload["embedded_package_paths"], [payload["embedded_package_path"]])

    def test_main_supports_dry_run_with_explicit_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "dependencies": {
                            "com.c3.unity-puer-exec.validation": "file:com.c3.unity-puer-exec.validation"
                        }
                    }
                ),
                encoding="utf-8",
            )

            with mock.patch.object(
                prepare_validation_host,
                "FORMAL_PACKAGE_ROOT",
                Path("D:/repo/packages/com.txcombo.unity-puer-exec"),
            ):
                exit_code = prepare_validation_host.main(
                    ["--manifest-path", str(manifest_path), "--dry-run"]
                )

            self.assertEqual(exit_code, 0)
            manifest_after = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertIn("com.c3.unity-puer-exec.validation", manifest_after["dependencies"])
            # A dry run reports the target wiring without writing it.
            self.assertNotIn("testables", manifest_after)

    def test_resolve_project_path_applies_dotenv_launch_args_with_explicit_project_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            dotenv_path = Path(temp_dir) / ".env"
            dotenv_path.write_text(
                "UNITY_PROJECT_PATH=X:/from-dotenv\n"
                'UNITY_PUER_EXEC_UNITY_LAUNCH_ARGS=["-force-gles30"]\n',
                encoding="utf-8",
            )
            env = {}
            resolved = prepare_validation_host.resolve_project_path(
                project_path="X:/explicit",
                env=env,
                dotenv_path=dotenv_path,
            )

            self.assertEqual(resolved, Path("X:/explicit").resolve())
            self.assertEqual(env.get("UNITY_PUER_EXEC_UNITY_LAUNCH_ARGS"), '["-force-gles30"]')
            self.assertEqual(env.get("UNITY_PROJECT_PATH"), "X:/from-dotenv")

    def test_resolve_project_path_preserves_explicit_process_env_launch_args(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            dotenv_path = Path(temp_dir) / ".env"
            dotenv_path.write_text(
                'UNITY_PUER_EXEC_UNITY_LAUNCH_ARGS=["-force-gles30"]\n',
                encoding="utf-8",
            )
            env = {"UNITY_PUER_EXEC_UNITY_LAUNCH_ARGS": '["-force-d3d11"]'}
            resolved = prepare_validation_host.resolve_project_path(
                project_path="X:/explicit",
                env=env,
                dotenv_path=dotenv_path,
            )

            self.assertEqual(resolved, Path("X:/explicit").resolve())
            self.assertEqual(env.get("UNITY_PUER_EXEC_UNITY_LAUNCH_ARGS"), '["-force-d3d11"]')

    def test_resolve_project_path_uses_dotenv_project_path_when_omitted(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            dotenv_path = Path(temp_dir) / ".env"
            dotenv_path.write_text(
                "UNITY_PROJECT_PATH=X:/from-dotenv\n",
                encoding="utf-8",
            )
            env = {}
            resolved = prepare_validation_host.resolve_project_path(
                project_path=None,
                env=env,
                dotenv_path=dotenv_path,
            )

            self.assertEqual(resolved, Path("X:/from-dotenv").resolve())

def _snapshot_tree(root_path):
    """Every file under root_path -> its bytes, for byte-for-byte round-trip proof."""
    root_path = Path(root_path)
    return {
        candidate.relative_to(root_path).as_posix(): candidate.read_bytes()
        for candidate in sorted(root_path.rglob("*"))
        if candidate.is_file()
    }


def _write_endpoint_publication(project_path, unity_pid=4242, port=55231):
    """A complete Editor publication, the shape ``read_endpoint_publication`` accepts."""
    endpoint_path = Path(project_path) / "Temp" / "UnityPuerExec" / "endpoint.json"
    endpoint_path.parent.mkdir(parents=True, exist_ok=True)
    endpoint_path.write_text(
        json.dumps(
            {
                "port": port,
                "unity_pid": unity_pid,
                "project_path": str(project_path),
                "session_marker": "session-marker-fixture",
            }
        ),
        encoding="utf-8",
    )
    return endpoint_path


def _write_embedded_tree(directory_path, package_name, extra=None):
    """An embedded package with nested files, so a move is not just a bare rename."""
    _write_embedded_package(directory_path, package_name)
    editor_dir = directory_path / "Editor"
    editor_dir.mkdir(parents=True, exist_ok=True)
    (editor_dir / "Bridge.cs").write_bytes(b"// bridge\r\n")
    (directory_path / "CLI~").mkdir(parents=True, exist_ok=True)
    (directory_path / "CLI~" / "unity-puer-exec.exe").write_bytes(b"\x00\x01binary\xff")
    for relative_path, content in (extra or {}).items():
        target = directory_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    return directory_path


class EmbeddedShadowSwitchTests(unittest.TestCase):
    """Clear/restore of an embedded package shadow (proposal: paired operation)."""

    def _make_host(self, temp_dir):
        project_path = Path(temp_dir) / "Project"
        packages_path = project_path / "Packages"
        packages_path.mkdir(parents=True)
        manifest_path = packages_path / "manifest.json"
        manifest_path.write_text(
            json.dumps({"dependencies": {"com.example.other": "file:com.example.other"}}),
            encoding="utf-8",
        )
        package_root = Path(temp_dir) / "repo" / "packages" / "com.txcombo.unity-puer-exec"
        package_root.mkdir(parents=True)
        return project_path, manifest_path, package_root

    def _free_host(self, project_path):
        """A host nothing holds: no lockfile and no published endpoint."""
        self.assertFalse(
            prepare_validation_host.project_lockfile_is_held(project_path),
            "fixture host must read as free",
        )
        self.assertFalse(prepare_validation_host.editor_endpoint_is_live(project_path))
        return project_path

    # -- 2.1 clear ---------------------------------------------------------

    def test_clear_moves_every_shadowing_directory_into_the_dated_host_local_backup(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path, manifest_path, package_root = self._make_host(temp_dir)
            self._free_host(project_path)
            first_path = project_path / "Packages" / "com.txcombo.unity-puer-exec"
            second_path = project_path / "Packages" / "com.txcombo.unity-puer-exec.bak"
            _write_embedded_tree(first_path, "com.txcombo.unity-puer-exec")
            _write_embedded_tree(second_path, "com.txcombo.unity-puer-exec")

            outcome = prepare_validation_host.clear_embedded_shadow(
                project_path,
                manifest_path=manifest_path,
                package_root=package_root,
                today=datetime.date(2026, 5, 4),
            )

            self.assertEqual(outcome["status"], "cleared")
            backup_root = project_path / ".unity-puer-exec-embedded-backup"
            self.assertEqual(Path(outcome["backup_path"]), backup_root)
            self.assertEqual(len(outcome["moved"]), 2)
            self.assertEqual(
                sorted(move["source"] for move in outcome["moved"]),
                sorted([str(first_path), str(second_path)]),
            )
            self.assertEqual(
                sorted(move["target"] for move in outcome["moved"]),
                sorted(
                    [
                        str(backup_root / "com.txcombo.unity-puer-exec-20260504"),
                        str(backup_root / "com.txcombo.unity-puer-exec.bak-20260504"),
                    ]
                ),
            )
            # Nothing is left in Packages/ and nothing was deleted by the moves.
            self.assertFalse(first_path.exists())
            self.assertFalse(second_path.exists())
            self.assertTrue(
                (
                    backup_root
                    / "com.txcombo.unity-puer-exec-20260504"
                    / "Editor"
                    / "Bridge.cs"
                ).is_file()
            )
            self.assertTrue(
                (
                    backup_root
                    / "com.txcombo.unity-puer-exec-20260504"
                    / "CLI~"
                    / "unity-puer-exec.exe"
                ).is_file()
            )

    def test_clear_reports_unchanged_and_writes_nothing_when_no_shadow_is_present(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path, manifest_path, package_root = self._make_host(temp_dir)
            _write_embedded_package(
                project_path / "Packages" / "com.example.other", "com.example.other"
            )
            before = _snapshot_tree(project_path)

            outcome = prepare_validation_host.clear_embedded_shadow(
                project_path,
                manifest_path=manifest_path,
                package_root=package_root,
            )

            self.assertEqual(outcome["status"], "unchanged")
            self.assertEqual(outcome["moved"], [])
            self.assertIsNone(outcome["backup_path"])
            self.assertFalse((project_path / ".unity-puer-exec-embedded-backup").exists())
            self.assertEqual(_snapshot_tree(project_path), before)

    def test_clear_refuses_when_the_backup_path_already_holds_content(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path, manifest_path, package_root = self._make_host(temp_dir)
            self._free_host(project_path)
            embedded_path = project_path / "Packages" / "com.txcombo.unity-puer-exec"
            _write_embedded_tree(embedded_path, "com.txcombo.unity-puer-exec")
            occupied = (
                project_path
                / ".unity-puer-exec-embedded-backup"
                / "com.txcombo.unity-puer-exec-20260504"
            )
            _write_embedded_tree(occupied, "com.txcombo.unity-puer-exec")
            (occupied / "left-behind.txt").write_text("not restored", encoding="utf-8")

            outcome = prepare_validation_host.clear_embedded_shadow(
                project_path,
                manifest_path=manifest_path,
                package_root=package_root,
                today=datetime.date(2026, 5, 4),
            )

            self.assertEqual(outcome["status"], "refused")
            self.assertIn("backup_path_occupied", outcome["reason"])
            self.assertIn(str(occupied), outcome["reason"])
            self.assertEqual(outcome["moved"], [])
            # The embedded package stays where it is and the backup is untouched.
            self.assertTrue((embedded_path / "package.json").is_file())
            self.assertTrue((occupied / "left-behind.txt").is_file())

    def test_clear_reuses_an_empty_hand_rolled_backup_skeleton(self):
        # An empty dated directory is the residue a previous hand-rolled clear
        # leaves behind (design: it is inert). Reusing it deletes nothing.
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path, manifest_path, package_root = self._make_host(temp_dir)
            self._free_host(project_path)
            embedded_path = project_path / "Packages" / "com.txcombo.unity-puer-exec"
            _write_embedded_tree(embedded_path, "com.txcombo.unity-puer-exec")
            skeleton = (
                project_path
                / ".unity-puer-exec-embedded-backup"
                / "com.txcombo.unity-puer-exec-20260504"
            )
            skeleton.mkdir(parents=True)

            outcome = prepare_validation_host.clear_embedded_shadow(
                project_path,
                manifest_path=manifest_path,
                package_root=package_root,
                today=datetime.date(2026, 5, 4),
            )

            self.assertEqual(outcome["status"], "cleared")
            self.assertTrue((skeleton / "Editor" / "Bridge.cs").is_file())

    def test_clear_dry_run_does_not_consume_an_empty_backup_skeleton(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path, manifest_path, package_root = self._make_host(temp_dir)
            self._free_host(project_path)
            embedded_path = project_path / "Packages" / "com.txcombo.unity-puer-exec"
            _write_embedded_tree(embedded_path, "com.txcombo.unity-puer-exec")
            skeleton = (
                project_path
                / ".unity-puer-exec-embedded-backup"
                / "com.txcombo.unity-puer-exec-20260504"
            )
            skeleton.mkdir(parents=True)

            outcome = prepare_validation_host.clear_embedded_shadow(
                project_path,
                manifest_path=manifest_path,
                package_root=package_root,
                today=datetime.date(2026, 5, 4),
                dry_run=True,
            )

            self.assertEqual(outcome["status"], "dry-run")
            # The preview wrote nothing, including not removing the inert skeleton.
            self.assertTrue(skeleton.is_dir())
            self.assertTrue(embedded_path.is_dir())

    # -- 2.2 restore -------------------------------------------------------

    def test_restore_moves_the_backups_contents_back_to_their_packages_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path, manifest_path, package_root = self._make_host(temp_dir)
            self._free_host(project_path)
            embedded_path = project_path / "Packages" / "com.txcombo.unity-puer-exec"
            _write_embedded_tree(embedded_path, "com.txcombo.unity-puer-exec")
            original = _snapshot_tree(embedded_path)

            prepare_validation_host.clear_embedded_shadow(
                project_path,
                manifest_path=manifest_path,
                package_root=package_root,
                today=datetime.date(2026, 5, 4),
            )
            outcome = prepare_validation_host.restore_embedded_shadow(
                project_path,
                manifest_path=manifest_path,
                today=datetime.date(2026, 5, 4),
            )

            self.assertEqual(outcome["status"], "restored")
            self.assertEqual(len(outcome["moved"]), 1)
            self.assertEqual(Path(outcome["moved"][0]["target"]), embedded_path)
            self.assertEqual(_snapshot_tree(embedded_path), original)
            self.assertFalse((project_path / ".unity-puer-exec-embedded-backup").exists())

    def test_restore_refuses_rather_than_merging_into_an_occupied_target(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path, manifest_path, package_root = self._make_host(temp_dir)
            self._free_host(project_path)
            embedded_path = project_path / "Packages" / "com.txcombo.unity-puer-exec"
            _write_embedded_tree(embedded_path, "com.txcombo.unity-puer-exec")

            prepare_validation_host.clear_embedded_shadow(
                project_path,
                manifest_path=manifest_path,
                package_root=package_root,
                today=datetime.date(2026, 5, 4),
            )
            # Someone reinstalled the package by hand while the shadow was cleared.
            reinstalled = _write_embedded_package(
                embedded_path, "com.txcombo.unity-puer-exec"
            )
            (reinstalled / "reinstalled.txt").write_text("hand install", encoding="utf-8")
            backup_entry = (
                project_path
                / ".unity-puer-exec-embedded-backup"
                / "com.txcombo.unity-puer-exec-20260504"
            )

            outcome = prepare_validation_host.restore_embedded_shadow(
                project_path,
                manifest_path=manifest_path,
                today=datetime.date(2026, 5, 4),
            )

            self.assertEqual(outcome["status"], "refused")
            self.assertIn("restore_target_occupied", outcome["reason"])
            self.assertIn(str(embedded_path), outcome["reason"])
            self.assertEqual(outcome["moved"], [])
            # Neither copy was merged or overwritten.
            self.assertTrue((reinstalled / "reinstalled.txt").is_file())
            self.assertFalse((reinstalled / "Editor" / "Bridge.cs").exists())
            self.assertTrue((backup_entry / "Editor" / "Bridge.cs").is_file())

    def test_restore_reports_unchanged_when_the_embedded_package_is_already_in_place(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path, manifest_path, package_root = self._make_host(temp_dir)
            embedded_path = project_path / "Packages" / "com.txcombo.unity-puer-exec"
            _write_embedded_tree(embedded_path, "com.txcombo.unity-puer-exec")
            before = _snapshot_tree(project_path)

            outcome = prepare_validation_host.restore_embedded_shadow(
                project_path,
                manifest_path=manifest_path,
            )

            self.assertEqual(outcome["status"], "unchanged")
            self.assertEqual(outcome["moved"], [])
            self.assertEqual(_snapshot_tree(project_path), before)

    def test_restore_treats_an_empty_backup_directory_as_unchanged(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path, manifest_path, package_root = self._make_host(temp_dir)
            _write_embedded_package(
                project_path / "Packages" / "com.txcombo.unity-puer-exec",
                "com.txcombo.unity-puer-exec",
            )
            (
                project_path
                / ".unity-puer-exec-embedded-backup"
                / "com.txcombo.unity-puer-exec-20260504"
            ).mkdir(parents=True)

            outcome = prepare_validation_host.restore_embedded_shadow(
                project_path,
                manifest_path=manifest_path,
            )

            self.assertEqual(outcome["status"], "unchanged")
            self.assertEqual(outcome["moved"], [])

    # -- 2.3 round trip ----------------------------------------------------

    def test_clear_then_restore_reproduces_the_packages_tree_byte_for_byte(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path, manifest_path, package_root = self._make_host(temp_dir)
            self._free_host(project_path)
            embedded_path = project_path / "Packages" / "com.txcombo.unity-puer-exec"
            _write_embedded_tree(
                embedded_path,
                "com.txcombo.unity-puer-exec",
                extra={
                    "package.json": json.dumps(
                        {"name": "com.txcombo.unity-puer-exec", "version": "0.12.0"}
                    ).encode("utf-8"),
                    "Runtime/Nested/Deep.txt": b"deep\r\ncontent\x00\xff",
                },
            )
            before = _snapshot_tree(project_path)

            cleared = prepare_validation_host.clear_embedded_shadow(
                project_path,
                manifest_path=manifest_path,
                package_root=package_root,
                today=datetime.date(2026, 5, 4),
            )
            restored = prepare_validation_host.restore_embedded_shadow(
                project_path,
                manifest_path=manifest_path,
                today=datetime.date(2026, 5, 4),
            )

            self.assertEqual(cleared["status"], "cleared")
            self.assertEqual(restored["status"], "restored")
            # Byte for byte, and nothing deleted: file set and every payload match.
            self.assertEqual(_snapshot_tree(project_path), before)

    # -- 2.4 host freedom --------------------------------------------------

    def test_clear_refuses_when_the_lockfile_is_held(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path, manifest_path, package_root = self._make_host(temp_dir)
            embedded_path = project_path / "Packages" / "com.txcombo.unity-puer-exec"
            _write_embedded_tree(embedded_path, "com.txcombo.unity-puer-exec")
            held_lockfile = project_path / "Temp" / "UnityLockfile"
            held_lockfile.parent.mkdir(parents=True, exist_ok=True)
            held_lockfile.write_bytes(b"")
            before = _snapshot_tree(project_path)

            with mock.patch.object(
                prepare_validation_host, "project_lockfile_is_held", return_value=True
            ), mock.patch("subprocess.run") as run_mock:
                cleared = prepare_validation_host.clear_embedded_shadow(
                    project_path,
                    manifest_path=manifest_path,
                    package_root=package_root,
                )

            self.assertEqual(cleared["status"], "refused")
            self.assertIn("host_not_free", cleared["reason"])
            self.assertIn("UnityLockfile", cleared["reason"])
            self.assertEqual(cleared["moved"], [])
            # Nothing moved, and nothing tried to stop an Editor process.
            self.assertEqual(_snapshot_tree(project_path), before)
            run_mock.assert_not_called()

    def test_restore_refuses_when_the_lockfile_is_held(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path, manifest_path, package_root = self._make_host(temp_dir)
            self._free_host(project_path)
            embedded_path = project_path / "Packages" / "com.txcombo.unity-puer-exec"
            _write_embedded_tree(embedded_path, "com.txcombo.unity-puer-exec")
            # The clear happened while the host was free; now an Editor owns it.
            prepare_validation_host.clear_embedded_shadow(
                project_path,
                manifest_path=manifest_path,
                package_root=package_root,
            )
            held_lockfile = project_path / "Temp" / "UnityLockfile"
            held_lockfile.parent.mkdir(parents=True, exist_ok=True)
            held_lockfile.write_bytes(b"")
            before = _snapshot_tree(project_path)

            with mock.patch.object(
                prepare_validation_host, "project_lockfile_is_held", return_value=True
            ), mock.patch("subprocess.run") as run_mock:
                restored = prepare_validation_host.restore_embedded_shadow(
                    project_path,
                    manifest_path=manifest_path,
                )

            self.assertEqual(restored["status"], "refused")
            self.assertIn("host_not_free", restored["reason"])
            self.assertIn("UnityLockfile", restored["reason"])
            self.assertEqual(restored["moved"], [])
            self.assertEqual(_snapshot_tree(project_path), before)
            self.assertFalse(embedded_path.exists())
            run_mock.assert_not_called()

    def test_clear_refuses_when_a_published_endpoint_names_a_running_editor(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path, manifest_path, package_root = self._make_host(temp_dir)
            embedded_path = project_path / "Packages" / "com.txcombo.unity-puer-exec"
            _write_embedded_tree(embedded_path, "com.txcombo.unity-puer-exec")
            _write_endpoint_publication(project_path)
            before = _snapshot_tree(project_path)

            with mock.patch.object(
                prepare_validation_host, "_pid_is_running", return_value=True
            ), mock.patch("subprocess.run") as run_mock:
                cleared = prepare_validation_host.clear_embedded_shadow(
                    project_path,
                    manifest_path=manifest_path,
                    package_root=package_root,
                )

            self.assertEqual(cleared["status"], "refused")
            self.assertIn("host_not_free", cleared["reason"])
            self.assertIn("endpoint.json", cleared["reason"])
            self.assertEqual(cleared["moved"], [])
            self.assertEqual(_snapshot_tree(project_path), before)
            # Nothing tried to stop the Editor it refused over.
            run_mock.assert_not_called()

    def test_restore_refuses_when_a_published_endpoint_names_a_running_editor(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path, manifest_path, package_root = self._make_host(temp_dir)
            self._free_host(project_path)
            embedded_path = project_path / "Packages" / "com.txcombo.unity-puer-exec"
            _write_embedded_tree(embedded_path, "com.txcombo.unity-puer-exec")
            prepare_validation_host.clear_embedded_shadow(
                project_path,
                manifest_path=manifest_path,
                package_root=package_root,
            )
            _write_endpoint_publication(project_path)
            before = _snapshot_tree(project_path)

            with mock.patch.object(
                prepare_validation_host, "_pid_is_running", return_value=True
            ), mock.patch("subprocess.run") as run_mock:
                restored = prepare_validation_host.restore_embedded_shadow(
                    project_path,
                    manifest_path=manifest_path,
                )

            self.assertEqual(restored["status"], "refused")
            self.assertIn("host_not_free", restored["reason"])
            self.assertIn("endpoint.json", restored["reason"])
            self.assertEqual(restored["moved"], [])
            self.assertEqual(_snapshot_tree(project_path), before)
            self.assertFalse(embedded_path.exists())
            run_mock.assert_not_called()

    def test_a_residue_endpoint_from_a_dead_editor_does_not_block_the_operation(self):
        # The suite's own state table calls publication-present-without-a-held-lock
        # "ended_residue": crash and kill residue, not a live Editor. Since the
        # real-host suite itself leaves such a file behind, treating mere presence as
        # busy would make the documented clear/restore pair unusable.
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path, manifest_path, package_root = self._make_host(temp_dir)
            embedded_path = project_path / "Packages" / "com.txcombo.unity-puer-exec"
            _write_embedded_tree(embedded_path, "com.txcombo.unity-puer-exec")
            _write_endpoint_publication(project_path)

            with mock.patch.object(prepare_validation_host, "_pid_is_running", return_value=False):
                self.assertFalse(prepare_validation_host.editor_endpoint_is_live(project_path))
                outcome = prepare_validation_host.clear_embedded_shadow(
                    project_path,
                    manifest_path=manifest_path,
                    package_root=package_root,
                )

            self.assertEqual(outcome["status"], "cleared")

    def test_a_lockfile_left_on_disk_but_not_held_does_not_block_the_operation(self):
        # Windows keeps Temp/UnityLockfile after the Editor exits. Existence is not
        # busy: only a lock that cannot be taken is, which is the rule the real-host
        # suite's clean-boundary check delegates to.
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path, manifest_path, package_root = self._make_host(temp_dir)
            lockfile_path = project_path / "Temp" / "UnityLockfile"
            lockfile_path.parent.mkdir(parents=True, exist_ok=True)
            lockfile_path.write_bytes(b"")
            embedded_path = project_path / "Packages" / "com.txcombo.unity-puer-exec"
            _write_embedded_tree(embedded_path, "com.txcombo.unity-puer-exec")

            self.assertFalse(prepare_validation_host.project_lockfile_is_held(project_path))
            outcome = prepare_validation_host.clear_embedded_shadow(
                project_path,
                manifest_path=manifest_path,
                package_root=package_root,
            )

            self.assertEqual(outcome["status"], "cleared")

    @unittest.skipUnless(
        sys.platform == "win32", "the validation host lockfile rule is Windows-specific"
    )
    def test_a_held_lockfile_is_detected_from_project_local_state(self):
        import msvcrt

        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "Project"
            lockfile_path = project_path / "Temp" / "UnityLockfile"
            lockfile_path.parent.mkdir(parents=True)
            lockfile_path.write_bytes(b"")
            self.assertFalse(prepare_validation_host.project_lockfile_is_held(project_path))

            descriptor = os.open(str(lockfile_path), os.O_RDWR)
            try:
                msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
                self.assertTrue(prepare_validation_host.project_lockfile_is_held(project_path))
            finally:
                os.close(descriptor)
            self.assertFalse(prepare_validation_host.project_lockfile_is_held(project_path))

    # -- 2.5 report shape --------------------------------------------------

    def _run_main(self, argv):
        stdout = StringIO()
        with redirect_stdout(stdout):
            exit_code = prepare_validation_host.main(argv)
        return exit_code, json.loads(stdout.getvalue())

    def test_shadow_operations_report_the_extended_envelope_without_changing_existing_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path, manifest_path, package_root = self._make_host(temp_dir)
            embedded_path = project_path / "Packages" / "com.txcombo.unity-puer-exec"
            _write_embedded_tree(embedded_path, "com.txcombo.unity-puer-exec")
            existing_fields = {
                "status",
                "manifest_path",
                "package_name",
                "dependency",
                "testables",
                "package_testable",
                "embedded_package_shadowing",
                "embedded_package_path",
                "embedded_package_paths",
            }

            with mock.patch.object(prepare_validation_host, "FORMAL_PACKAGE_ROOT", package_root):
                clear_code, clear_payload = self._run_main(
                    ["--project-path", str(project_path), "--clear-embedded-shadow"]
                )
                # A following preparation run reports the shadow as cleared.
                prepare_code, prepare_payload = self._run_main(
                    ["--project-path", str(project_path)]
                )
                restore_code, restore_payload = self._run_main(
                    ["--project-path", str(project_path), "--restore-embedded-shadow"]
                )

            self.assertEqual((clear_code, prepare_code, restore_code), (0, 0, 0))
            self.assertEqual(clear_payload["status"], "cleared")
            self.assertFalse(clear_payload["embedded_package_shadowing"])
            self.assertEqual(clear_payload["embedded_package_paths"], [])
            self.assertTrue(clear_payload["package_testable"])
            self.assertEqual(clear_payload["testables"], ["com.txcombo.unity-puer-exec"])
            self.assertIsNotNone(clear_payload["backup_path"])
            self.assertIsNone(clear_payload["reason"])
            self.assertEqual(len(clear_payload["moved"]), 1)
            self.assertEqual(prepare_payload["status"], "updated")
            self.assertFalse(prepare_payload["embedded_package_shadowing"])
            self.assertEqual(restore_payload["status"], "restored")
            self.assertTrue(restore_payload["embedded_package_shadowing"])
            # The temp root may be spelled through a drive mapping, so compare the
            # path's shape rather than its drive letter.
            self.assertEqual(len(restore_payload["embedded_package_paths"]), 1)
            restored_path = Path(restore_payload["embedded_package_paths"][0])
            self.assertEqual(restored_path.name, "com.txcombo.unity-puer-exec")
            self.assertEqual(restored_path.parent.name, "Packages")
            for payload in (clear_payload, prepare_payload, restore_payload):
                self.assertTrue(existing_fields.issubset(payload), existing_fields - set(payload))
                self.assertIn("backup_path", payload)
                self.assertIn("reason", payload)
                self.assertIn("moved", payload)

    def test_refused_and_dry_run_statuses_are_reported_with_their_own_values(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path, manifest_path, package_root = self._make_host(temp_dir)
            embedded_path = project_path / "Packages" / "com.txcombo.unity-puer-exec"
            _write_embedded_tree(embedded_path, "com.txcombo.unity-puer-exec")
            before = _snapshot_tree(project_path)
            expected_suffix = (
                ".unity-puer-exec-embedded-backup/com.txcombo.unity-puer-exec-"
                + datetime.date.today().strftime("%Y%m%d")
            )

            with mock.patch.object(prepare_validation_host, "FORMAL_PACKAGE_ROOT", package_root):
                dry_code, dry_payload = self._run_main(
                    [
                        "--project-path",
                        str(project_path),
                        "--clear-embedded-shadow",
                        "--dry-run",
                    ]
                )
                self.assertEqual(_snapshot_tree(project_path), before)
                _write_endpoint_publication(project_path)
                with mock.patch.object(
                    prepare_validation_host, "_pid_is_running", return_value=True
                ):
                    refused_code, refused_payload = self._run_main(
                        ["--project-path", str(project_path), "--clear-embedded-shadow"]
                    )

            self.assertEqual((dry_code, refused_code), (0, 2))
            self.assertEqual(dry_payload["status"], "dry-run")
            self.assertEqual(len(dry_payload["moved"]), 1)
            self.assertTrue(
                dry_payload["moved"][0]["target"].replace("\\", "/").endswith(expected_suffix)
            )
            self.assertEqual(refused_payload["status"], "refused")
            self.assertIn("host_not_free", refused_payload["reason"])
            self.assertTrue((embedded_path / "package.json").is_file())

    def test_restore_dry_run_reports_intended_moves_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path, manifest_path, package_root = self._make_host(temp_dir)
            self._free_host(project_path)
            embedded_path = project_path / "Packages" / "com.txcombo.unity-puer-exec"
            _write_embedded_tree(embedded_path, "com.txcombo.unity-puer-exec")
            prepare_validation_host.clear_embedded_shadow(
                project_path,
                manifest_path=manifest_path,
                package_root=package_root,
            )
            before = _snapshot_tree(project_path)

            outcome = prepare_validation_host.restore_embedded_shadow(
                project_path,
                manifest_path=manifest_path,
                dry_run=True,
            )

            self.assertEqual(outcome["status"], "dry-run")
            self.assertEqual(len(outcome["moved"]), 1)
            self.assertEqual(Path(outcome["moved"][0]["target"]), embedded_path)
            self.assertEqual(_snapshot_tree(project_path), before)
            self.assertFalse(embedded_path.exists())

    def test_shadow_operations_refuse_a_manifest_outside_a_packages_directory(self):
        # The backup lives next to Packages/, so a manifest somewhere else gives no
        # host root to act inside. Refuse by name instead of guessing one.
        with tempfile.TemporaryDirectory() as temp_dir:
            stray_manifest = Path(temp_dir) / "manifest.json"
            stray_manifest.write_text(json.dumps({"dependencies": {}}), encoding="utf-8")

            code, payload = self._run_main(
                ["--manifest-path", str(stray_manifest), "--clear-embedded-shadow"]
            )

            self.assertEqual(code, 2)
            self.assertEqual(payload["status"], "refused")
            self.assertIn("manifest_not_in_packages", payload["reason"])
            self.assertEqual(payload["moved"], [])
            self.assertFalse((Path(temp_dir) / ".unity-puer-exec-embedded-backup").exists())

    def test_help_lists_the_paired_flags(self):
        help_text = prepare_validation_host.build_parser().format_help()
        self.assertIn("--clear-embedded-shadow", help_text)
        self.assertIn("--restore-embedded-shadow", help_text)


if __name__ == "__main__":
    unittest.main()
