"""The documented default suite and the CI selection must be the same set.

The default unit-test module list is written down twice: as the module
arguments of ``python -m unittest`` in ``.github/workflows/unit-tests.yml`` and
as the copy-pasteable command line in
``openspec/specs/validation-host-integration/how-to-run.md``. Drift between the
two is silent -- CI stays green while the documented suite quietly covers more
than the executed one (or the reverse).

This module parses both lists **as they are written** and compares them as
sets. It deliberately introduces no third representation: there is no expected
module list here to keep in sync, only the two parsed inputs.

Set equality between the two lists cannot see a module that is missing from
both of them -- both sides omit it, so the comparison passes. The second
property below closes that hole by enumerating ``tests/test_*.py`` on disk and
requiring the unselected remainder to be an explicit, reasoned ``EXCLUSIONS``
table. That table is a complement, never a copy: it names only modules that are
in neither list, so it cannot drift with the lists it complements.

Mocked layer only: it reads two text files and needs neither a Unity Editor nor
a validation host.
"""

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = REPO_ROOT / "tests"
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "unit-tests.yml"
HOW_TO_RUN_PATH = (
    REPO_ROOT
    / "openspec"
    / "specs"
    / "validation-host-integration"
    / "how-to-run.md"
)

# Modules that are in neither default-suite list, each with the reason it cannot
# run there. Every ``tests/test_*.py`` module must be selected in both lists or
# appear here -- a module in neither place fails the guard by name.
EXCLUSIONS = {
    "tests.test_real_host_integration": (
        "requires a live Unity Editor and a prepared validation host; "
        "runs only under UNITY_PUER_EXEC_RUN_REAL_HOST_TESTS=1"
    ),
}

_UNITTEST_COMMAND = "python -m unittest"
_FENCE_RE = re.compile(r"^```")


def _join_continued_lines(lines, start_index):
    """Join a shell command whose continuations end in a trailing backtick.

    PowerShell splats the ``python -m unittest`` call across lines with a
    trailing backtick; the documented command line is a single line. Both forms
    collapse to one logical command here.
    """
    collected = []
    for line in lines[start_index:]:
        stripped = line.strip()
        if stripped.endswith("`"):
            collected.append(stripped[:-1].strip())
            continue
        collected.append(stripped)
        break
    return " ".join(part for part in collected if part)


def _modules_after_command(command):
    """Return the module arguments of one ``python -m unittest`` command."""
    index = command.find(_UNITTEST_COMMAND)
    if index < 0:
        return []
    arguments = command[index + len(_UNITTEST_COMMAND):].split()
    return [argument for argument in arguments if not argument.startswith("-")]


def parse_workflow_modules(workflow_text):
    """Parse the module arguments out of the unit-test workflow's run block."""
    lines = workflow_text.splitlines()
    for position, line in enumerate(lines):
        if _UNITTEST_COMMAND not in line:
            continue
        command = _join_continued_lines(lines, position)
        modules = _modules_after_command(command)
        if modules:
            return modules
    raise AssertionError(
        "no '{0}' command with module arguments found in {1}".format(
            _UNITTEST_COMMAND, WORKFLOW_PATH.as_posix()
        )
    )


def parse_documented_modules(document_text):
    """Parse the default-suite command line out of the how-to-run document."""
    lines = document_text.splitlines()
    in_fence = False
    for position, line in enumerate(lines):
        if _FENCE_RE.match(line.strip()):
            in_fence = not in_fence
            continue
        if not in_fence or _UNITTEST_COMMAND not in line:
            continue
        command = _join_continued_lines(lines, position)
        modules = _modules_after_command(command)
        if modules:
            return modules
    raise AssertionError(
        "no fenced '{0}' command with module arguments found in {1}".format(
            _UNITTEST_COMMAND, HOW_TO_RUN_PATH.as_posix()
        )
    )


def describe_disagreement(workflow_modules, documented_modules):
    """Return a human-readable description of every one-sided module."""
    workflow_set = set(workflow_modules)
    documented_set = set(documented_modules)
    only_in_workflow = sorted(workflow_set - documented_set)
    only_in_document = sorted(documented_set - workflow_set)

    lines = []
    for module in only_in_workflow:
        lines.append(
            "{0} is in the CI workflow but missing from the documented default suite".format(
                module
            )
        )
    for module in only_in_document:
        lines.append(
            "{0} is in the documented default suite but missing from the CI workflow".format(
                module
            )
        )
    return "\n".join(lines)


def enumerate_test_modules(tests_dir=TESTS_DIR):
    """Return every ``tests.test_*`` module name that exists on disk."""
    return {
        "tests.{0}".format(path.stem)
        for path in Path(tests_dir).glob("test_*.py")
    }


def describe_unselected(on_disk, selected):
    """Return one line per module that is neither selected nor excluded."""
    described = []
    for module in sorted(on_disk - selected):
        if module in EXCLUSIONS:
            continue
        described.append(
            "{0} is in neither the CI workflow nor the documented default suite, "
            "and is not named in EXCLUSIONS".format(module)
        )
    return "\n".join(described)


class DefaultSuiteSelectionTests(unittest.TestCase):
    def setUp(self):
        self.workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.document_text = HOW_TO_RUN_PATH.read_text(encoding="utf-8")
        self.workflow_modules = parse_workflow_modules(self.workflow_text)
        self.documented_modules = parse_documented_modules(self.document_text)

    def test_both_lists_are_actually_parsed(self):
        for label, modules in (
            ("CI workflow", self.workflow_modules),
            ("documented default suite", self.documented_modules),
        ):
            self.assertTrue(modules, "{0}: parsed no module arguments".format(label))
            self.assertEqual(
                len(modules),
                len(set(modules)),
                "{0} names a module more than once: {1}".format(label, modules),
            )
            for module in modules:
                self.assertTrue(
                    module.startswith("tests."),
                    "{0} parsed a non-test-module argument: {1}".format(label, module),
                )

    def test_ci_selection_matches_the_documented_default_suite(self):
        self.assertEqual(
            set(self.workflow_modules),
            set(self.documented_modules),
            "The CI module list and the documented default-suite command line must name "
            "the same set of test modules:\n"
            + describe_disagreement(self.workflow_modules, self.documented_modules),
        )

    def test_every_test_module_is_selected_or_excluded_by_name(self):
        """Every module on disk is selected in both lists or explicitly excluded.

        ``set`` equality between the two lists cannot see a module that both
        lists omit. This complements it: ``selected`` is still derived from the
        parsed lists, and the on-disk enumeration supplies the universe that
        equality alone cannot express.
        """
        on_disk = enumerate_test_modules()
        selected = set(self.workflow_modules) | set(self.documented_modules)

        self.assertTrue(
            on_disk,
            "enumerated no tests.test_* modules under {0}".format(
                TESTS_DIR.as_posix()
            ),
        )

        unselected = on_disk - selected
        self.assertEqual(
            unselected,
            set(EXCLUSIONS),
            "The unselected test modules and the EXCLUSIONS table must be the same "
            "set. Every tests/test_*.py module must be selected in both default-suite "
            "lists or named in EXCLUSIONS with a reason.\n"
            + describe_unselected(on_disk, selected)
            + "\nMissing from EXCLUSIONS: {0}\nStale in EXCLUSIONS: {1}".format(
                sorted(unselected - set(EXCLUSIONS)),
                sorted(set(EXCLUSIONS) - unselected),
            ),
        )

    def test_every_exclusion_states_a_reason(self):
        """An exclusion cannot be added without saying why it cannot run."""
        for module, reason in EXCLUSIONS.items():
            self.assertIsInstance(
                reason, str, "{0}: exclusion reason must be a string".format(module)
            )
            self.assertTrue(
                reason.strip(),
                "{0}: exclusion reason must be non-empty, otherwise the exclusion is "
                "an unexplained omission".format(module),
            )

    def test_no_exclusion_is_also_a_selected_module(self):
        """The exclusion table complements the lists, so it cannot overlap them."""
        selected = set(self.workflow_modules) | set(self.documented_modules)
        for module in sorted(set(EXCLUSIONS) & selected):
            self.fail(
                "{0} is named in EXCLUSIONS but is also selected in a default-suite "
                "list; drop the exclusion or drop it from the list".format(module)
            )


if __name__ == "__main__":
    unittest.main()
