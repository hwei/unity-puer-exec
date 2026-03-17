import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import openspec_backlog  # type: ignore
import openspec_change_meta  # type: ignore


class OpenSpecBacklogTests(unittest.TestCase):
    def _write_change(self, root: Path, name: str, **defaults):
        change_dir = root / name
        change_dir.mkdir()
        openspec_change_meta.ensure_meta_file(change_dir, defaults=defaults)

    def test_rank_prefers_active_high_priority_with_more_unlocks(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            changes_dir = Path(temp_dir)
            self._write_change(
                changes_dir,
                "active-harness",
                status="active",
                change_type="harness",
                priority="P0",
                evidence="tests",
                updated_at="2026-03-17",
            )
            self._write_change(
                changes_dir,
                "queued-feature",
                status="queued",
                change_type="feature",
                priority="P0",
                blocked_by=["active-harness"],
                evidence="tests",
                updated_at="2026-03-16",
            )
            self._write_change(
                changes_dir,
                "queued-validation",
                status="queued",
                change_type="validation",
                priority="P1",
                evidence="host-validation",
                updated_at="2026-03-17",
            )

            rankings = openspec_backlog.rank_records(openspec_backlog.load_change_records(changes_dir))
            self.assertEqual(rankings[0][0].name, "active-harness")
            self.assertIn("unlock_count=1", rankings[0][2])

    def test_filter_supports_backlog_view_and_change_type(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            changes_dir = Path(temp_dir)
            self._write_change(changes_dir, "queued-harness", status="queued", change_type="harness")
            self._write_change(changes_dir, "active-harness", status="active", change_type="harness")
            self._write_change(changes_dir, "queued-feature", status="queued", change_type="feature")

            records = openspec_backlog.load_change_records(changes_dir)
            filtered = openspec_backlog.filter_records(
                records,
                status="queued",
                change_type="harness",
                backlog_only=True,
            )

            self.assertEqual([record.name for record in filtered], ["queued-harness"])

    def test_next_outputs_json_for_actionable_changes_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            changes_dir = Path(temp_dir)
            self._write_change(changes_dir, "queued-ok", status="queued", change_type="spike")
            self._write_change(
                changes_dir,
                "blocked-item",
                status="blocked",
                change_type="feature",
            )
            self._write_change(
                changes_dir,
                "invalid-assumption",
                status="active",
                change_type="harness",
                assumption_state="invalid",
            )

            stdout = io.StringIO()
            with mock.patch.object(openspec_backlog, "CHANGES_DIR", changes_dir):
                with redirect_stdout(stdout):
                    openspec_backlog.main(["next", "--json"])

            payload = json.loads(stdout.getvalue())
            self.assertEqual([item["name"] for item in payload], ["queued-ok"])


if __name__ == "__main__":
    unittest.main()
