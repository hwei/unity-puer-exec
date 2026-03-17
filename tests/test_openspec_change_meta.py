import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import openspec_change_meta  # type: ignore


class OpenSpecChangeMetaTests(unittest.TestCase):
    def test_parse_meta_text_supports_scalar_and_list_fields(self):
        meta = openspec_change_meta.parse_meta_text(
            "\n".join(
                [
                    "status: queued",
                    "change_type: harness",
                    "priority: P1",
                    "blocked_by:",
                    "- formalize-contract",
                    "- add-host-fixture",
                    "assumption_state: needs-review",
                    "evidence: host-validation",
                    "updated_at: 2026-03-17",
                ]
            )
        )

        self.assertEqual(meta.status, "queued")
        self.assertEqual(meta.change_type, "harness")
        self.assertEqual(meta.priority, "P1")
        self.assertEqual(meta.blocked_by, ("formalize-contract", "add-host-fixture"))
        self.assertEqual(meta.assumption_state, "needs-review")
        self.assertEqual(meta.evidence, "host-validation")
        self.assertEqual(meta.updated_at, "2026-03-17")

    def test_ensure_meta_file_uses_template_defaults_and_current_date(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            change_dir = Path(temp_dir) / "new-change"
            change_dir.mkdir()

            meta_path = openspec_change_meta.ensure_meta_file(
                change_dir,
                defaults={"change_type": "validation", "priority": "P0"},
            )

            meta = openspec_change_meta.load_meta(meta_path)
            self.assertEqual(meta.status, "queued")
            self.assertEqual(meta.change_type, "validation")
            self.assertEqual(meta.priority, "P0")
            self.assertEqual(meta.blocked_by, ())

    def test_list_non_archived_change_dirs_skips_archive(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            changes_dir = Path(temp_dir)
            (changes_dir / "archive").mkdir()
            (changes_dir / "alpha").mkdir()
            (changes_dir / "beta").mkdir()

            change_names = [path.name for path in openspec_change_meta.list_non_archived_change_dirs(changes_dir)]
            self.assertEqual(change_names, ["alpha", "beta"])


if __name__ == "__main__":
    unittest.main()
