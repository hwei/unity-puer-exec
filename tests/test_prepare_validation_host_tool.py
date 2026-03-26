import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import prepare_validation_host  # type: ignore


class PrepareValidationHostTests(unittest.TestCase):
    def test_compute_file_dependency_uses_reproducible_relative_path(self):
        manifest_path = Path("F:/C3/unity-puer-exec-workspace/c3-client-tree2/Project/Packages/manifest.json")
        dependency = prepare_validation_host.compute_file_dependency(manifest_path)
        self.assertEqual(dependency, "file:../../../unity-puer-exec/packages/com.txcombo.unity-puer-exec")

    def test_rewrite_manifest_replaces_legacy_embedded_package(self):
        manifest_path = Path("F:/C3/unity-puer-exec-workspace/c3-client-tree2/Project/Packages/manifest.json")
        manifest = {
            "dependencies": {
                "com.c3.unity-puer-exec.validation": "file:com.c3.unity-puer-exec.validation",
                "com.cysharp.unitask": "file:com.cysharp.unitask",
            },
            "scopedRegistries": [],
        }

        rewritten, changed, dependency = prepare_validation_host.rewrite_manifest(manifest, manifest_path)

        self.assertTrue(changed)
        self.assertEqual(dependency, "file:../../../unity-puer-exec/packages/com.txcombo.unity-puer-exec")
        self.assertNotIn("com.c3.unity-puer-exec.validation", rewritten["dependencies"])
        self.assertEqual(
            rewritten["dependencies"]["com.txcombo.unity-puer-exec"],
            "file:../../../unity-puer-exec/packages/com.txcombo.unity-puer-exec",
        )
        self.assertEqual(rewritten["dependencies"]["com.cysharp.unitask"], "file:com.cysharp.unitask")

    def test_rewrite_manifest_is_idempotent_for_formal_dependency(self):
        manifest_path = Path("F:/C3/unity-puer-exec-workspace/c3-client-tree2/Project/Packages/manifest.json")
        manifest = {
            "dependencies": {
                "com.txcombo.unity-puer-exec": "file:../../../unity-puer-exec/packages/com.txcombo.unity-puer-exec",
                "com.cysharp.unitask": "file:com.cysharp.unitask",
            }
        }

        rewritten, changed, dependency = prepare_validation_host.rewrite_manifest(manifest, manifest_path)

        self.assertFalse(changed)
        self.assertEqual(
            rewritten["dependencies"]["com.txcombo.unity-puer-exec"],
            "file:../../../unity-puer-exec/packages/com.txcombo.unity-puer-exec",
        )
        self.assertEqual(dependency, "file:../../../unity-puer-exec/packages/com.txcombo.unity-puer-exec")

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

            exit_code = prepare_validation_host.main(
                ["--manifest-path", str(manifest_path), "--dry-run"]
            )

            self.assertEqual(exit_code, 0)
            manifest_after = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertIn("com.c3.unity-puer-exec.validation", manifest_after["dependencies"])


if __name__ == "__main__":
    unittest.main()
