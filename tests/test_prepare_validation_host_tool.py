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

import prepare_validation_host  # type: ignore


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
