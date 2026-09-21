"""Structural guard over durable OpenSpec specs.

The ``openspec`` CLI is the authority for spec validation, but it is not
guaranteed to be on PATH in the default unit-test workflow. This module
re-implements only two stable structural rules over ``openspec/specs/**/spec.md``
so drift fails the default suite instead of surfacing as another validator
warning nobody reads:

- every requirement carries at least one ``#### Scenario:`` block
- every requirement's normative text states a ``SHALL`` or ``MUST``

It deliberately does not shell out to the CLI and does not attempt full
validation; the ``openspec`` CLI remains the authority for everything else.
"""

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SPECS_ROOT = REPO_ROOT / "openspec" / "specs"

_REQUIREMENT_RE = re.compile(r"^###\s+Requirement:\s*(?P<name>.+?)\s*$")
_SCENARIO_RE = re.compile(r"^####\s+Scenario:")
_NORMATIVE_KEYWORD_RE = re.compile(r"\b(?:SHALL|MUST)\b")


def iter_spec_files(specs_root=SPECS_ROOT):
    """Return every durable spec document under ``specs_root``, sorted."""
    return sorted(specs_root.rglob("spec.md"))


def iter_requirements(spec_text):
    """Yield ``(name, block_lines)`` for each ``### Requirement:`` section.

    A block runs from its heading up to the next requirement heading (or end of
    document), so it includes the requirement body and every scenario beneath it.
    """
    lines = spec_text.splitlines()
    starts = [index for index, line in enumerate(lines) if _REQUIREMENT_RE.match(line)]
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(lines)
        block = lines[start:end]
        match = _REQUIREMENT_RE.match(block[0])
        yield match.group("name"), block


def find_violations(spec_text):
    """Return the structural rule violations found in one spec document."""
    violations = []
    for name, block in iter_requirements(spec_text):
        normative_text = []
        for line in block:
            if _SCENARIO_RE.match(line):
                break
            normative_text.append(line)

        if not any(_SCENARIO_RE.match(line) for line in block):
            violations.append(f"'{name}' has no '#### Scenario:' block")
        if not _NORMATIVE_KEYWORD_RE.search("\n".join(normative_text)):
            violations.append(f"'{name}' states no SHALL or MUST")
    return violations


def _fixture_spec():
    return (
        "# Fixture\n"
        "\n"
        "## Requirements\n"
        "\n"
        "### Requirement: Alpha\n"
        "\n"
        "The system SHALL handle alpha.\n"
        "\n"
        "#### Scenario: Alpha is handled\n"
        "\n"
        "- **WHEN** alpha arrives\n"
        "- **THEN** it is handled\n"
    )


class SpecHygieneTests(unittest.TestCase):
    def test_every_durable_requirement_has_a_scenario_and_a_normative_keyword(self):
        spec_files = iter_spec_files()
        self.assertTrue(spec_files, f"no durable spec files found under {SPECS_ROOT}")

        violations = []
        for path in spec_files:
            for violation in find_violations(path.read_text(encoding="utf-8")):
                violations.append(f"{path.relative_to(REPO_ROOT).as_posix()}: {violation}")

        self.assertEqual(
            [],
            violations,
            "Durable specs must give every requirement a '#### Scenario:' and a SHALL/MUST:\n"
            + "\n".join(violations),
        )

    def test_compliant_fixture_requirement_is_accepted(self):
        self.assertEqual([], find_violations(_fixture_spec()))

    def test_removing_the_scenario_from_a_fixture_requirement_is_reported(self):
        compliant = _fixture_spec()
        without_scenario = compliant.split("#### Scenario:")[0].rstrip() + "\n"

        self.assertIn(
            "'Alpha' has no '#### Scenario:' block",
            find_violations(without_scenario),
        )

    def test_removing_the_normative_keyword_from_a_fixture_requirement_is_reported(self):
        compliant = _fixture_spec()
        without_keyword = compliant.replace("SHALL handle", "handles")

        self.assertIn(
            "'Alpha' states no SHALL or MUST",
            find_violations(without_keyword),
        )

    def test_each_requirement_is_checked_independently(self):
        spec_text = (
            "# Fixture\n"
            "\n"
            "## Requirements\n"
            "\n"
            "### Requirement: Alpha\n"
            "\n"
            "The system SHALL handle alpha.\n"
            "\n"
            "#### Scenario: Alpha is handled\n"
            "\n"
            "- **WHEN** alpha arrives\n"
            "- **THEN** it is handled\n"
            "\n"
            "### Requirement: Beta\n"
            "\n"
            "The system handles beta.\n"
        )

        self.assertEqual(["'Beta' has no '#### Scenario:' block", "'Beta' states no SHALL or MUST"], find_violations(spec_text))


if __name__ == "__main__":
    unittest.main()
