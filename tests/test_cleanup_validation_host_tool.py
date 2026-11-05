import json
import re
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


REAL_HOST_SUITE_PATH = REPO_ROOT / "tests" / "test_real_host_integration.py"
# Repository-owned asset roots the real-host suite creates are spelled as
# `"Assets" / "root"`, `Path("Assets", "root")`, or `"Assets/root/..."`.
# The scan is source-text based on purpose: importing the real-host module must
# not be needed (and must not require a Unity Editor) for this guard to run.
ASSETS_DIR_LITERAL_PATTERNS = (
    re.compile(r'["\']Assets["\']\s*\)?\s*/\s*["\']([^"\']+)["\']'),
    re.compile(r'Path\(\s*["\']Assets["\']\s*,\s*["\']([^"\']+)["\']'),
    re.compile(r'["\']Assets/([^"\']+)["\']'),
    re.compile(r'["\']Assets/["\']\s*\+\s*["\']([^"\']+)["\']'),
)


def suite_asset_roots_from_source(source_text):
    """First-level directory names under Assets/ named by the suite's literals."""
    roots = set()
    for pattern in ASSETS_DIR_LITERAL_PATTERNS:
        for match in pattern.finditer(source_text):
            first_segment = match.group(1).replace("\\", "/").split("/")[0].strip()
            # A format/dynamic segment (`f"Assets/{name}"`) is not a literal root
            # and cannot be checked statically; skip it instead of failing on it.
            if "{" in first_segment or "}" in first_segment or "%" in first_segment:
                continue
            if first_segment:
                roots.add((Path("Assets") / first_segment).as_posix())
    return roots


def find_undeclared_suite_asset_roots(source_text, declared_roots):
    declared = {Path(root).as_posix() for root in declared_roots}
    return sorted(suite_asset_roots_from_source(source_text) - declared)


def assert_suite_asset_roots_declared(source_text, declared_roots):
    undeclared = find_undeclared_suite_asset_roots(source_text, declared_roots)
    if undeclared:
        raise AssertionError(
            "real-host suite creates asset roots outside the declared validation-temp "
            "inventory: {} (declared: {})".format(
                ", ".join(undeclared),
                ", ".join(sorted({Path(root).as_posix() for root in declared_roots})),
            )
        )


class CleanupValidationHostTests(unittest.TestCase):
    def test_declared_inventory_report_names_host_reset_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            (project_path / "Assets").mkdir(parents=True)

            result = cleanup_validation_host.cleanup_validation_temp_assets(project_path)

            self.assertIn(
                str((project_path / "Assets" / "__codex_host_reset").resolve()),
                result["declared_roots"],
            )

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
            (assets_path / "__codex_host_reset").mkdir()
            (assets_path / "__codex_host_reset" / "Baseline.unity").write_text("scene", encoding="utf-8")
            (assets_path / "__codex_host_reset.meta").write_text("meta", encoding="utf-8")

            result = cleanup_validation_host.cleanup_validation_temp_assets(project_path)

            self.assertEqual(result["status"], "cleaned")
            self.assertEqual(result["errors"], [])
            self.assertEqual(result["residue"], [])
            self.assertFalse((assets_path / "__AgentValidation").exists())
            self.assertFalse((assets_path / "__AgentValidation.meta").exists())
            self.assertFalse((assets_path / "__codex_validation_temp").exists())
            self.assertFalse((assets_path / "__codex_validation_temp.meta").exists())
            self.assertFalse((assets_path / "__codex_host_reset").exists())
            self.assertFalse((assets_path / "__codex_host_reset.meta").exists())
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


class RealHostSuiteInventoryGuardTests(unittest.TestCase):
    """Every asset root the real-host suite creates must be declared for cleanup.

    The roots come from the suite's own source literals, so a new asset the suite
    starts creating fails here instead of silently surviving a run as host
    residue. Reading the source keeps this test free of any Unity Editor.
    """

    def read_suite_source(self):
        self.assertTrue(
            REAL_HOST_SUITE_PATH.is_file(),
            "real-host suite source not found: {}".format(REAL_HOST_SUITE_PATH),
        )
        return REAL_HOST_SUITE_PATH.read_text(encoding="utf-8")

    def test_real_host_suite_asset_roots_are_declared(self):
        source_text = self.read_suite_source()
        roots = suite_asset_roots_from_source(source_text)
        # Prove the scan sees the suite's known roots; an empty or blind scan must
        # not make this guard vacuously pass.
        self.assertIn("Assets/__codex_host_reset", roots)
        self.assertIn("Assets/__codex_validation_temp", roots)

        assert_suite_asset_roots_declared(
            source_text, cleanup_validation_host.DECLARED_VALIDATION_TEMP_ROOTS
        )

    def test_guard_fails_and_names_an_undeclared_root(self):
        synthetic_source = (
            'PROBE_DIR = project_path / "Assets" / "__codex_undeclared_probe"\n'
            'SCENE = Path("Assets") / "__codex_host_reset" / "Baseline.unity"\n'
        )
        with self.assertRaises(AssertionError) as raised:
            assert_suite_asset_roots_declared(
                synthetic_source, cleanup_validation_host.DECLARED_VALIDATION_TEMP_ROOTS
            )
        message = str(raised.exception)
        self.assertIn("Assets/__codex_undeclared_probe", message)
