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
            }
        }

        rewritten, changed, dependency = prepare_validation_host.rewrite_manifest(
            manifest,
            manifest_path,
            package_root=package_root,
        )

        self.assertFalse(changed)
        self.assertEqual(rewritten["dependencies"]["com.txcombo.unity-puer-exec"], expected_dependency)
        self.assertEqual(dependency, expected_dependency)

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


if __name__ == "__main__":
    unittest.main()
