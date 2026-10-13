import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import openspec_change_meta  # type: ignore


# Decision (task 2.3): the archive guard tolerates exactly these records by
# name. They fail because they predate the `blocked_by` / `evidence`
# required-field rule, not because of any parse defect in this change, so
# rewriting them is a separate governance decision. The guard fails on any
# other unparseable record, including any record that fails on `evidence`.
KNOWN_LEGACY_ARCHIVE_RECORDS = frozenset(
    {
        "2026-03-26-exec-import-support",
        "2026-03-26-readme-user-facing-rewrite",
        "2026-05-12-exec-async-warning-status",
        "2026-05-14-relax-runtime-guidance-compile-count-situation",
    }
)


def collect_archive_meta_failures():
    failures = []
    for meta_path in sorted(openspec_change_meta.ARCHIVE_DIR.glob("*/meta.yaml")):
        try:
            openspec_change_meta.load_meta(meta_path)
        except Exception as exc:  # noqa: BLE001 - the guard reports any failure kind
            failures.append((meta_path.parent.name, str(exc)))
    return failures


class OpenSpecChangeMetaTests(unittest.TestCase):
    def test_parse_meta_text_supports_optional_status_and_list_fields(self):
        meta = openspec_change_meta.parse_meta_text(
            "\n".join(
                [
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

        self.assertIsNone(meta.status)
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
            self.assertIsNone(meta.status)
            self.assertEqual(meta.change_type, "validation")
            self.assertEqual(meta.priority, "P0")
            self.assertEqual(meta.blocked_by, ())

    def test_parse_meta_text_keeps_legacy_status_values(self):
        meta = openspec_change_meta.parse_meta_text(
            "\n".join(
                [
                    "status: queued",
                    "change_type: spike",
                    "priority: P2",
                    "blocked_by: []",
                    "assumption_state: valid",
                    "evidence: manual-check",
                    "updated_at: 2026-03-24",
                ]
            )
        )

        self.assertEqual(meta.status, "queued")

    def test_evidence_scalar_inline_list_and_block_list_forms_parse(self):
        base = [
            "change_type: refactor",
            "priority: P2",
            "blocked_by: []",
            "assumption_state: valid",
            "updated_at: 2026-10-13",
        ]

        scalar = openspec_change_meta.parse_meta_text(
            "\n".join([*base[:3], "evidence: tests", *base[3:]])
        )
        inline = openspec_change_meta.parse_meta_text(
            "\n".join(
                [*base[:3], "evidence: [tests, manual-check]", *base[3:]]
            )
        )
        block = openspec_change_meta.parse_meta_text(
            "\n".join(
                [
                    *base[:3],
                    "evidence:",
                    "- tests",
                    "- cli-transcript",
                    "- host-validation",
                    *base[3:],
                ]
            )
        )

        self.assertEqual(scalar.evidence, "tests")
        self.assertEqual(inline.evidence, "tests, manual-check")
        self.assertEqual(block.evidence, "tests, cli-transcript, host-validation")

    def test_multi_value_evidence_join_is_deterministic_and_lossless(self):
        meta = openspec_change_meta.parse_meta_text(
            "\n".join(
                [
                    "change_type: validation",
                    "priority: P1",
                    "blocked_by: []",
                    "assumption_state: valid",
                    "evidence:",
                    "- host-validation",
                    "- tests",
                    "- cli-transcript",
                    "updated_at: 2026-10-13",
                ]
            )
        )

        self.assertEqual(meta.evidence, "host-validation, tests, cli-transcript")
        # No value is discarded: each parsed entry survives the collapse.
        for entry in ("host-validation", "tests", "cli-transcript"):
            self.assertIn(entry, meta.evidence)

    def test_unsupported_evidence_message_names_values_and_accepted_set(self):
        with self.assertRaises(ValueError) as ctx:
            openspec_change_meta.parse_meta_text(
                "\n".join(
                    [
                        "change_type: refactor",
                        "priority: P2",
                        "blocked_by: []",
                        "assumption_state: valid",
                        "evidence: [tests, nope]",
                        "updated_at: 2026-10-13",
                    ]
                )
            )

        message = str(ctx.exception)
        # Names the offending parsed value rather than implying it is forbidden.
        self.assertIn("'nope'", message)
        self.assertIn("parsed values: tests, nope", message)
        self.assertIn("tests, host-validation, cli-transcript, manual-check", message)
        self.assertIn("inline list", message)

    def test_dump_meta_round_trips_multi_value_evidence(self):
        original = openspec_change_meta.parse_meta_text(
            "\n".join(
                [
                    "change_type: validation",
                    "priority: P1",
                    "blocked_by:",
                    "- some-other-change",
                    "assumption_state: valid",
                    "evidence:",
                    "- tests",
                    "- cli-transcript",
                    "updated_at: 2026-10-13",
                ]
            )
        )

        reparsed = openspec_change_meta.parse_meta_text(
            openspec_change_meta.dump_meta(original)
        )
        self.assertEqual(reparsed, original)
        self.assertEqual(reparsed.evidence, "tests, cli-transcript")

    def test_empty_evidence_list_is_rejected_with_form_hint(self):
        for text in ("evidence: []", "evidence:"):
            with self.assertRaises(ValueError) as ctx:
                openspec_change_meta.parse_meta_text(
                    "\n".join(
                        [
                            "change_type: refactor",
                            "priority: P2",
                            "blocked_by: []",
                            "assumption_state: valid",
                            text,
                            "updated_at: 2026-10-13",
                        ]
                    )
                )
            self.assertIn("at least one value", str(ctx.exception))
            self.assertIn("inline list", str(ctx.exception))

    def test_evidence_entries_tolerate_surrounding_whitespace(self):
        meta = openspec_change_meta.parse_meta_text(
            "\n".join(
                [
                    "change_type: refactor",
                    "priority: P2",
                    "blocked_by: []",
                    "assumption_state: valid",
                    "evidence: [ tests ,   manual-check ]",
                    "updated_at: 2026-10-13",
                ]
            )
        )
        self.assertEqual(meta.evidence, "tests, manual-check")

    def test_quoted_inline_list_entries_are_rejected_rather_than_guessed(self):
        # The hand-rolled parser never emits quotes and does not strip them.
        # Pin the behavior so a future author does not assume quoting works.
        with self.assertRaises(ValueError) as ctx:
            openspec_change_meta.parse_meta_text(
                "\n".join(
                    [
                        "change_type: refactor",
                        "priority: P2",
                        "blocked_by: []",
                        "assumption_state: valid",
                        'evidence: ["tests", manual-check]',
                        "updated_at: 2026-10-13",
                    ]
                )
            )
        self.assertIn("parsed values", str(ctx.exception))

    def test_real_archive_records_all_parse_except_known_legacy_ones(self):
        failures = collect_archive_meta_failures()
        unexpected = [
            failure for failure in failures if failure[0] not in KNOWN_LEGACY_ARCHIVE_RECORDS
        ]
        self.assertEqual(unexpected, [])

        # The tolerated records must only fail for the missing-required-field
        # reason; anything else (notably `evidence`) is a real regression.
        for name, message in failures:
            self.assertIn(name, KNOWN_LEGACY_ARCHIVE_RECORDS)
            self.assertIn("Missing required metadata fields", message)
            self.assertNotIn("Unsupported evidence", message)

        # And the records that carry the list form are now parseable.
        for name in (
            "2026-04-01-remove-wait-until-ready-command",
            "2026-10-13-make-base-url-exec-refresh-recoverable",
            "2026-10-13-reproduce-play-mode-transport-reset-flake",
        ):
            self.assertNotIn(name, [failure[0] for failure in failures])

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
