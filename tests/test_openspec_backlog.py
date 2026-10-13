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
    def _write_change(self, root: Path, name: str, *, task_lines=None, **defaults):
        change_dir = root / name
        change_dir.mkdir()
        openspec_change_meta.ensure_meta_file(change_dir, defaults=defaults)
        if task_lines is None:
            task_lines = ["## 1. Work", "", "- [ ] 1.1 Pending task"]
        if task_lines:
            (change_dir / "tasks.md").write_text("\n".join(task_lines) + "\n", encoding="utf-8")

    def _write_archived_change(self, archive_root: Path, name: str):
        archived_dir = archive_root / f"2026-03-23-{name}"
        archived_dir.mkdir(parents=True)

    def test_rank_prefers_eligible_high_priority_and_recent_git_distance(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            changes_dir = Path(temp_dir) / "changes"
            archive_dir = changes_dir / "archive"
            changes_dir.mkdir()
            archive_dir.mkdir()
            self._write_change(changes_dir, "alpha", status="queued", change_type="harness", priority="P0")
            self._write_change(changes_dir, "beta", status="active", change_type="feature", priority="P0")

            records = openspec_backlog.load_change_records(changes_dir)
            distance_map = {
                str(changes_dir / "alpha"): 3,
                str(changes_dir / "beta"): 0,
            }
            with mock.patch.object(
                openspec_backlog,
                "get_git_commit_distance",
                side_effect=lambda path, repo_root=openspec_backlog.REPO_ROOT: distance_map[str(path)],
            ):
                rankings = openspec_backlog.rank_records(
                    openspec_backlog.evaluate_records(records, archive_dir=archive_dir)
                )

            self.assertEqual([item.record.name for item in rankings], ["beta", "alpha"])
            self.assertIn("git_commit_distance=0", rankings[0].reasons)

    def test_filter_supports_derived_backlog_view_and_change_type(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            changes_dir = Path(temp_dir) / "changes"
            archive_dir = changes_dir / "archive"
            changes_dir.mkdir()
            archive_dir.mkdir()
            self._write_change(changes_dir, "eligible-harness", status="queued", change_type="harness")
            self._write_change(
                changes_dir,
                "blocked-harness",
                status="queued",
                change_type="harness",
                blocked_by=["eligible-harness"],
            )
            self._write_change(changes_dir, "eligible-feature", status="queued", change_type="feature")

            records = openspec_backlog.load_change_records(changes_dir)
            with mock.patch.object(openspec_backlog, "get_git_commit_distance", return_value=1):
                evaluated = openspec_backlog.evaluate_records(records, archive_dir=archive_dir)
            filtered = openspec_backlog.filter_records(
                evaluated,
                status="eligible",
                change_type="harness",
                backlog_only=True,
            )

            self.assertEqual([item.record.name for item in filtered], ["eligible-harness"])

    def test_missing_dependency_is_inconsistent(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            changes_dir = Path(temp_dir) / "changes"
            archive_dir = changes_dir / "archive"
            changes_dir.mkdir()
            archive_dir.mkdir()
            self._write_change(
                changes_dir,
                "broken-change",
                status="queued",
                blocked_by=["missing-prereq"],
            )

            records = openspec_backlog.load_change_records(changes_dir)
            with mock.patch.object(openspec_backlog, "get_git_commit_distance", return_value=2):
                evaluated = openspec_backlog.evaluate_records(records, archive_dir=archive_dir)

            self.assertEqual(evaluated[0].derived_status, "inconsistent")
            self.assertEqual(evaluated[0].missing_dependencies, ("missing-prereq",))
            self.assertIn("missing_dependency", evaluated[0].diagnostics)

    def test_archived_dependency_allows_eligibility(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            changes_dir = Path(temp_dir) / "changes"
            archive_dir = changes_dir / "archive"
            changes_dir.mkdir()
            archive_dir.mkdir()
            self._write_archived_change(archive_dir, "done-prereq")
            self._write_change(
                changes_dir,
                "ready-change",
                status="queued",
                blocked_by=["done-prereq"],
            )

            records = openspec_backlog.load_change_records(changes_dir)
            with mock.patch.object(openspec_backlog, "get_git_commit_distance", return_value=4):
                evaluated = openspec_backlog.evaluate_records(records, archive_dir=archive_dir)

            self.assertTrue(evaluated[0].eligible)
            self.assertEqual(evaluated[0].derived_status, "eligible")

    def test_superseded_is_excluded_from_backlog(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            changes_dir = Path(temp_dir) / "changes"
            archive_dir = changes_dir / "archive"
            changes_dir.mkdir()
            archive_dir.mkdir()
            self._write_change(changes_dir, "old-path", status="superseded")
            self._write_change(changes_dir, "new-path", status="queued")

            records = openspec_backlog.load_change_records(changes_dir)
            with mock.patch.object(openspec_backlog, "get_git_commit_distance", return_value=1):
                evaluated = openspec_backlog.evaluate_records(records, archive_dir=archive_dir)
            filtered = openspec_backlog.filter_records(evaluated, backlog_only=True)

            self.assertEqual([item.record.name for item in filtered], ["new-path"])

    def test_next_outputs_json_for_eligible_changes_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            changes_dir = Path(temp_dir) / "changes"
            archive_dir = changes_dir / "archive"
            changes_dir.mkdir()
            archive_dir.mkdir()
            self._write_change(changes_dir, "eligible-ok", status="queued", change_type="spike")
            self._write_change(
                changes_dir,
                "blocked-item",
                status="queued",
                change_type="feature",
                blocked_by=["eligible-ok"],
            )
            self._write_change(
                changes_dir,
                "invalid-assumption",
                status="queued",
                change_type="harness",
                assumption_state="invalid",
            )

            distance_map = {
                str(changes_dir / "eligible-ok"): 1,
                str(changes_dir / "blocked-item"): 3,
                str(changes_dir / "invalid-assumption"): 2,
            }
            stdout = io.StringIO()
            with mock.patch.object(openspec_backlog, "CHANGES_DIR", changes_dir), mock.patch.object(
                openspec_backlog, "ARCHIVE_DIR", archive_dir
            ), mock.patch.object(
                openspec_backlog,
                "get_git_commit_distance",
                side_effect=lambda path, repo_root=openspec_backlog.REPO_ROOT: distance_map[str(path)],
            ):
                with redirect_stdout(stdout):
                    openspec_backlog.main(["next", "--json"])

            payload = json.loads(stdout.getvalue())
            self.assertEqual([item["name"] for item in payload], ["eligible-ok"])
            self.assertTrue(payload[0]["derived"]["eligible"])

    def test_status_filter_uses_derived_status(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            changes_dir = Path(temp_dir) / "changes"
            archive_dir = changes_dir / "archive"
            changes_dir.mkdir()
            archive_dir.mkdir()
            self._write_change(changes_dir, "ready", status="queued")
            self._write_change(changes_dir, "old", status="superseded")

            stdout = io.StringIO()
            with mock.patch.object(openspec_backlog, "CHANGES_DIR", changes_dir), mock.patch.object(
                openspec_backlog, "ARCHIVE_DIR", archive_dir
            ), mock.patch.object(openspec_backlog, "get_git_commit_distance", return_value=0):
                with redirect_stdout(stdout):
                    openspec_backlog.main(["list", "--status", "superseded", "--json"])

            payload = json.loads(stdout.getvalue())
            self.assertEqual([item["name"] for item in payload], ["old"])
            self.assertEqual(payload[0]["derived"]["status"], "superseded")

    def test_meta_status_filter_remains_available_for_raw_inspection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            changes_dir = Path(temp_dir) / "changes"
            archive_dir = changes_dir / "archive"
            changes_dir.mkdir()
            archive_dir.mkdir()
            self._write_change(changes_dir, "queued-item", status="queued")
            self._write_change(changes_dir, "old-item", status="superseded")

            stdout = io.StringIO()
            with mock.patch.object(openspec_backlog, "CHANGES_DIR", changes_dir), mock.patch.object(
                openspec_backlog, "ARCHIVE_DIR", archive_dir
            ), mock.patch.object(openspec_backlog, "get_git_commit_distance", return_value=0):
                with redirect_stdout(stdout):
                    openspec_backlog.main(["list", "--meta-status", "superseded", "--json"])

            payload = json.loads(stdout.getvalue())
            self.assertEqual([item["name"] for item in payload], ["old-item"])
            self.assertEqual(payload[0]["meta"]["status"], "superseded")

    def test_change_without_pending_tasks_is_not_eligible(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            changes_dir = Path(temp_dir) / "changes"
            archive_dir = changes_dir / "archive"
            changes_dir.mkdir()
            archive_dir.mkdir()
            self._write_change(changes_dir, "done-change", task_lines=["## 1. Done", "", "- [x] 1.1 Finished"])

            records = openspec_backlog.load_change_records(changes_dir)
            with mock.patch.object(openspec_backlog, "get_git_commit_distance", return_value=0):
                evaluated = openspec_backlog.evaluate_records(records, archive_dir=archive_dir)

            self.assertFalse(evaluated[0].eligible)
            self.assertEqual(evaluated[0].derived_status, "blocked")
            self.assertIn("no_pending_tasks", evaluated[0].diagnostics)

    def test_change_without_tasks_is_not_eligible(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            changes_dir = Path(temp_dir) / "changes"
            archive_dir = changes_dir / "archive"
            changes_dir.mkdir()
            archive_dir.mkdir()
            self._write_change(changes_dir, "draft-change", task_lines=[])

            records = openspec_backlog.load_change_records(changes_dir)
            with mock.patch.object(openspec_backlog, "get_git_commit_distance", return_value=0):
                evaluated = openspec_backlog.evaluate_records(records, archive_dir=archive_dir)

            self.assertFalse(evaluated[0].eligible)
            self.assertEqual(evaluated[0].derived_status, "blocked")
            self.assertIn("missing_tasks", evaluated[0].diagnostics)

    def test_evidence_values_splits_strips_and_drops_empties(self):
        self.assertEqual(openspec_backlog.evidence_values("tests"), ("tests",))
        self.assertEqual(
            openspec_backlog.evidence_values("tests, cli-transcript"),
            ("tests", "cli-transcript"),
        )
        self.assertEqual(
            openspec_backlog.evidence_values(" tests ,, manual-check ,"),
            ("tests", "manual-check"),
        )
        self.assertEqual(openspec_backlog.evidence_values(""), ())
        self.assertEqual(openspec_backlog.evidence_values("  ,  "), ())

    def test_evidence_values_is_the_single_evidence_splitter(self):
        source = (TOOLS_DIR / "openspec_backlog.py").read_text(encoding="utf-8")
        splitting_lines = [
            line
            for line in source.splitlines()
            if "split" in line and "evidence" in line.lower() and "def evidence_values" not in line
        ]
        self.assertEqual(
            [line.strip() for line in splitting_lines],
            ['return tuple(part.strip() for part in evidence.split(",") if part.strip())'],
        )

    def test_evidence_rank_matches_documented_heuristic(self):
        last = len(openspec_backlog.EVIDENCE_ORDER)
        self.assertEqual(openspec_backlog.evidence_rank("tests"), 0)
        self.assertEqual(openspec_backlog.evidence_rank("tests, manual-check"), 0)
        self.assertEqual(openspec_backlog.evidence_rank("manual-check, tests"), 0)
        self.assertEqual(openspec_backlog.evidence_rank("manual-check"), last - 1)
        self.assertEqual(openspec_backlog.evidence_rank("tests, not-a-real-value"), 0)
        self.assertEqual(openspec_backlog.evidence_rank("not-a-real-value"), last)
        self.assertEqual(openspec_backlog.evidence_rank(""), last)
        self.assertEqual(openspec_backlog.evidence_rank("   "), last)

    def _filtered_names(self, changes_dir: Path, archive_dir: Path, **kwargs):
        records = openspec_backlog.load_change_records(changes_dir)
        with mock.patch.object(openspec_backlog, "get_git_commit_distance", return_value=0):
            evaluated = openspec_backlog.evaluate_records(records, archive_dir=archive_dir)
        return [item.record.name for item in openspec_backlog.filter_records(evaluated, **kwargs)]

    def test_evidence_filter_is_includes_match_over_multi_value_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            changes_dir = Path(temp_dir) / "changes"
            archive_dir = changes_dir / "archive"
            changes_dir.mkdir()
            archive_dir.mkdir()
            self._write_change(changes_dir, "joined-in-order", evidence="tests, cli-transcript")
            self._write_change(changes_dir, "joined-out-of-order", evidence="cli-transcript, tests")
            self._write_change(changes_dir, "single", evidence="tests")
            self._write_change(changes_dir, "other", evidence="manual-check")

            matched = self._filtered_names(changes_dir, archive_dir, evidence="tests")
            self.assertEqual(sorted(matched), ["joined-in-order", "joined-out-of-order", "single"])

            # Includes-match, not exact-set match: a lone `tests` record still matches,
            # and does not match a different requested value.
            self.assertEqual(self._filtered_names(changes_dir, archive_dir, evidence="manual-check"), ["other"])

    def test_evidence_filter_tolerates_unknown_stored_value(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            changes_dir = Path(temp_dir) / "changes"
            archive_dir = changes_dir / "archive"
            changes_dir.mkdir()
            archive_dir.mkdir()
            unknown_dir = changes_dir / "unknown-evidence"
            unknown_dir.mkdir()
            (unknown_dir / "meta.yaml").write_text(
                "\n".join(
                    [
                        "change_type: feature",
                        "priority: P1",
                        "blocked_by: []",
                        "assumption_state: valid",
                        "evidence: tests, retired-value",
                        "updated_at: 2026-03-23",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (unknown_dir / "tasks.md").write_text("## 1. Work\n\n- [ ] 1.1 Task\n", encoding="utf-8")

            # `retired-value` is rejected by the parser, so build the record past the
            # parser to model a value that later became unrecognized.
            record = openspec_backlog.ChangeRecord(
                name="unknown-evidence",
                path=unknown_dir,
                meta=openspec_change_meta.ChangeMeta(
                    status=None,
                    change_type="feature",
                    priority="P1",
                    blocked_by=(),
                    assumption_state="valid",
                    evidence="tests, retired-value",
                    updated_at="2026-03-23",
                ),
            )
            with mock.patch.object(openspec_backlog, "get_git_commit_distance", return_value=0):
                evaluated = openspec_backlog.evaluate_records([record], archive_dir=archive_dir)

            # An unknown stored value does not raise and simply fails to match;
            # argparse `choices` keeps such a value from ever reaching the filter
            # from the CLI, and the recognized values in the same record still match.
            self.assertEqual(
                [item.record.name for item in openspec_backlog.filter_records(evaluated, evidence="host-validation")],
                [],
            )
            self.assertEqual(
                [item.record.name for item in openspec_backlog.filter_records(evaluated, evidence="tests")],
                ["unknown-evidence"],
            )
            self.assertEqual(openspec_backlog.evidence_rank("retired-value"), len(openspec_backlog.EVIDENCE_ORDER))

    def test_evidence_flag_rejects_joined_value(self):
        parser = openspec_backlog.build_parser()
        with self.assertRaises(SystemExit):
            with mock.patch("sys.stderr", new_callable=io.StringIO):
                parser.parse_args(["list", "--evidence", "tests, cli-transcript"])
        self.assertEqual(
            parser.parse_args(["list", "--evidence", "tests"]).evidence,
            "tests",
        )

    def test_evidence_flag_help_states_includes_match(self):
        parser = openspec_backlog.build_parser()
        subparsers = [
            action
            for action in parser._subparsers._group_actions  # noqa: SLF001
        ]
        self.assertTrue(subparsers)
        help_text = subparsers[0].choices["list"].format_help()
        self.assertIn("--evidence", help_text)
        self.assertIn("Includes-match", help_text)

    def test_non_evidence_filters_are_unchanged(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            changes_dir = Path(temp_dir) / "changes"
            archive_dir = changes_dir / "archive"
            changes_dir.mkdir()
            archive_dir.mkdir()
            self._write_change(
                changes_dir,
                "baseline",
                status="queued",
                change_type="harness",
                priority="P0",
                assumption_state="valid",
                evidence="tests",
            )
            self._write_change(
                changes_dir,
                "other",
                status="blocked",
                change_type="feature",
                priority="P2",
                assumption_state="invalid",
                evidence="manual-check",
            )

            self.assertEqual(self._filtered_names(changes_dir, archive_dir, status="eligible"), ["baseline"])
            self.assertEqual(self._filtered_names(changes_dir, archive_dir, status="blocked"), ["other"])
            self.assertEqual(self._filtered_names(changes_dir, archive_dir, meta_status="queued"), ["baseline"])
            self.assertEqual(self._filtered_names(changes_dir, archive_dir, change_type="harness"), ["baseline"])
            self.assertEqual(self._filtered_names(changes_dir, archive_dir, priority="P2"), ["other"])
            self.assertEqual(self._filtered_names(changes_dir, archive_dir, assumption_state="valid"), ["baseline"])
            self.assertEqual(self._filtered_names(changes_dir, archive_dir, backlog_only=True), ["baseline"])


if __name__ == "__main__":
    unittest.main()
