import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import openspec_change_meta  # type: ignore


def collect_archive_meta_failures():
    """Parse every archived `meta.yaml` and return `(name, error)` for each failure.

    There is no exemption list: any archived record that fails to load fails
    this guard. `openspec_change_meta.ARCHIVE_DIR.glob("*/meta.yaml")` cannot
    see a directory with no `meta.yaml` at all, so presence is asserted
    separately by `collect_archive_dirs_without_meta`.
    """
    failures = []
    for meta_path in sorted(openspec_change_meta.ARCHIVE_DIR.glob("*/meta.yaml")):
        try:
            openspec_change_meta.load_meta(meta_path)
        except Exception as exc:  # noqa: BLE001 - the guard reports any failure kind
            failures.append((meta_path.parent.name, str(exc)))
    return failures


def collect_archive_dirs_without_meta():
    """Return every archive directory that has no `meta.yaml` file."""
    if not openspec_change_meta.ARCHIVE_DIR.is_dir():
        return []
    return [
        path.name
        for path in sorted(openspec_change_meta.ARCHIVE_DIR.iterdir())
        if path.is_dir() and not (path / "meta.yaml").is_file()
    ]


def collect_list_form_evidence_files():
    """Return archived `meta.yaml` paths whose raw text uses list-form `evidence`.

    This inspects raw text on purpose. `load_meta` deliberately accepts both
    the scalar and list forms and collapses them to the same string, so the
    parsed `ChangeMeta` cannot tell them apart and cannot enforce the
    canonical scalar form.
    """
    offenders = []
    for meta_path in sorted(openspec_change_meta.ARCHIVE_DIR.glob("*/meta.yaml")):
        lines = meta_path.read_text(encoding="utf-8").splitlines()
        for index, raw_line in enumerate(lines):
            stripped = raw_line.strip()
            if not stripped.startswith("evidence:"):
                continue
            value = stripped[len("evidence:") :].strip()
            # `evidence: [a, b]` is an inline list.
            if value.startswith("["):
                offenders.append((meta_path.parent.name, index + 1, stripped))
                break
            # A bare `evidence:` key is a block list only when the following
            # non-empty line is a `- item` entry.
            if value:
                continue
            for following in lines[index + 1 :]:
                following_stripped = following.strip()
                if not following_stripped or following_stripped.startswith("#"):
                    continue
                if following_stripped.startswith("- "):
                    offenders.append((meta_path.parent.name, index + 1, stripped))
                break
            break
    return offenders


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

    def test_real_archive_records_all_parse_with_no_exemptions(self):
        # No name-based exemptions: the guard means "the whole archive parses".
        self.assertEqual(collect_archive_meta_failures(), [])

    def test_every_archive_directory_has_a_meta_file(self):
        # The `*/meta.yaml` glob cannot see a directory with no record at all,
        # which is how ten archived changes went unnoticed.
        self.assertEqual(collect_archive_dirs_without_meta(), [])

    def test_no_archived_meta_uses_list_form_evidence(self):
        # Raw-text assertion: the parser accepts both forms on purpose.
        self.assertEqual(collect_list_form_evidence_files(), [])

    def test_presence_and_list_form_collectors_detect_their_violations(self):
        # Keeps the two guards above from becoming vacuous: each collector is
        # exercised against a fixture that actually violates its rule.
        violations = {
            "no-record-at-all": "",
            "inline-list-form": (
                "change_type: feature\npriority: P1\nblocked_by: []\n"
                "assumption_state: valid\nevidence: [tests, manual-check]\n"
                "updated_at: 2026-03-26\n"
            ),
            "block-list-form": (
                "change_type: feature\npriority: P1\nblocked_by: []\n"
                "assumption_state: valid\nevidence:\n- tests\n- manual-check\n"
                "updated_at: 2026-03-26\n"
            ),
        }

        for label, text in violations.items():
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as temp_dir:
                    archive_dir = Path(temp_dir) / "archive"
                    change_dir = archive_dir / "2026-03-26-fixture-change"
                    change_dir.mkdir(parents=True)
                    if text:
                        (change_dir / "meta.yaml").write_text(text, encoding="utf-8")

                    with unittest.mock.patch.object(
                        openspec_change_meta, "ARCHIVE_DIR", archive_dir
                    ):
                        self.assertEqual(
                            collect_archive_dirs_without_meta(),
                            [] if text else ["2026-03-26-fixture-change"],
                        )
                        self.assertEqual(
                            len(collect_list_form_evidence_files()),
                            0 if label == "no-record-at-all" else 1,
                        )

    def test_scalar_and_empty_list_forms_are_not_flagged_as_list_form(self):
        # The presence of a valid `meta.yaml` is enough; the scalar form and
        # the empty `evidence: []` form must not trip the raw-text guard.
        fixture = (
            "change_type: feature\npriority: P1\nblocked_by: []\n"
            "assumption_state: valid\nevidence: tests, manual-check\n"
            "updated_at: 2026-03-26\n"
        )
        blocked_fixture = fixture.replace("blocked_by: []", "blocked_by:\n- other-change")

        with tempfile.TemporaryDirectory() as temp_dir:
            archive_dir = Path(temp_dir) / "archive"
            scalar_dir = archive_dir / "2026-03-26-scalar-evidence"
            scalar_dir.mkdir(parents=True)
            (scalar_dir / "meta.yaml").write_text(fixture, encoding="utf-8")
            blocked_dir = archive_dir / "2026-03-26-blocked-by"
            blocked_dir.mkdir(parents=True)
            (blocked_dir / "meta.yaml").write_text(blocked_fixture, encoding="utf-8")

            with unittest.mock.patch.object(
                openspec_change_meta, "ARCHIVE_DIR", archive_dir
            ):
                self.assertEqual(collect_archive_dirs_without_meta(), [])
                self.assertEqual(collect_list_form_evidence_files(), [])

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
