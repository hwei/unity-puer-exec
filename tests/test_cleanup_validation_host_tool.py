import json
import shutil
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import cleanup_validation_host  # type: ignore


class CleanupValidationHostTests(unittest.TestCase):
    def test_cleanup_validation_temp_assets_removes_declared_roots_and_meta(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            assets_path = project_path / "Assets"
            (assets_path / "__AgentValidation").mkdir(parents=True)
            (assets_path / "__AgentValidation" / "scene.unity").write_text("scene", encoding="utf-8")
            (assets_path / "__AgentValidation.meta").write_text("meta", encoding="utf-8")
            (assets_path / "__codex_validation_temp").mkdir()
            (assets_path / "__codex_validation_temp.meta").write_text("meta", encoding="utf-8")
            (assets_path / "CodexValidation").mkdir()
            (assets_path / "CodexValidation" / "Probe.cs").write_text("class Probe {}", encoding="utf-8")

            result = cleanup_validation_host.cleanup_validation_temp_assets(project_path)

            self.assertEqual(result["status"], "cleaned")
            self.assertEqual(result["errors"], [])
            self.assertEqual(result["residue"], [])
            self.assertFalse((assets_path / "__AgentValidation").exists())
            self.assertFalse((assets_path / "__AgentValidation.meta").exists())
            self.assertFalse((assets_path / "__codex_validation_temp").exists())
            self.assertFalse((assets_path / "__codex_validation_temp.meta").exists())
            self.assertFalse((assets_path / "CodexValidation").exists())

    def test_cleanup_validation_temp_assets_reports_already_clean(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            (project_path / "Assets").mkdir(parents=True)

            result = cleanup_validation_host.cleanup_validation_temp_assets(project_path)

            self.assertEqual(result["status"], "already_clean")
            self.assertEqual(result["removed"], [])
            self.assertEqual(result["errors"], [])
            self.assertEqual(result["residue"], [])

    def test_cleanup_leaves_paths_outside_the_declared_inventory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            assets_path = project_path / "Assets"
            (assets_path / "__codex_validation_temp").mkdir(parents=True)
            (assets_path / "KeepMe.txt").write_text("keep", encoding="utf-8")

            result = cleanup_validation_host.cleanup_validation_temp_assets(project_path)

            self.assertEqual(result["status"], "cleaned")
            self.assertEqual(result["errors"], [])
            self.assertEqual(result["residue"], [])
            self.assertIn("removed", result)
            self.assertTrue((assets_path / "KeepMe.txt").exists())
            with self.assertRaises(ValueError) as raised:
                cleanup_validation_host.assert_declared_validation_temp_path(
                    project_path, "Assets/KeepMe.txt"
                )
            self.assertIn("outside the declared inventory", str(raised.exception))

    def test_editor_delete_removes_roots_without_a_filesystem_delete(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            assets_path = project_path / "Assets"
            temp_root = assets_path / "__codex_validation_temp"
            temp_root.mkdir(parents=True)
            (temp_root / "Probe.cs").write_text("class Probe {}", encoding="utf-8")
            (temp_root / "Probe.cs.meta").write_text("meta", encoding="utf-8")
            (assets_path / "__codex_validation_temp.meta").write_text("meta", encoding="utf-8")
            seen = []
            real_rmtree = shutil.rmtree

            def editor_delete(paths):
                seen.extend(paths)
                for relative in paths:
                    target = project_path / relative
                    if target.is_dir():
                        real_rmtree(target)
                    elif target.exists():
                        target.unlink()
                    meta = target.with_name(target.name + ".meta")
                    if meta.exists():
                        meta.unlink()
                return {"removed": paths, "errors": []}

            with mock.patch.object(cleanup_validation_host.shutil, "rmtree") as rmtree:
                result = cleanup_validation_host.cleanup_validation_temp_assets(
                    project_path, editor_delete=editor_delete
                )

            rmtree.assert_not_called()
            self.assertIn("Assets/__codex_validation_temp", seen)
            self.assertNotIn("Assets/KeepMe.txt", seen)
            self.assertEqual(result["errors"], [])
            self.assertEqual(result["residue"], [])
            self.assertEqual(result["status"], "cleaned")
            self.assertTrue(result["removed"])
            self.assertFalse(temp_root.exists())

    def test_main_prints_json_payload(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            (project_path / "Assets" / "CodexValidation").mkdir(parents=True)

            with mock.patch("sys.stdout.write") as stdout_write:
                exit_code = cleanup_validation_host.main(["--project-path", str(project_path)])

            written = "".join(call.args[0] for call in stdout_write.call_args_list)
            payload = json.loads(written)
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "cleaned")
