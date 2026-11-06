"""Source invariants for PuerTS major-version compatibility.

The package compiles against two PuerTS majors from one source tree: the Editor assembly
definition maps the host's installed ``com.tencent.puerts.core`` version to the
``PUERTS_3`` symbol, and ``UnityPuerExecServer.cs`` splits the JavaScript environment's
type and construction on it. Nothing else in the package is version-aware, and that is the
property worth holding mechanically:

  - the assembly carries exactly one version define, keyed to the PuerTS package, using the
    open-ended ``[3.0.0`` lower bound so a newer 3.x or 4.x host needs no asmdef edit;
  - every ``ScriptEnv`` and ``Backend`` code reference sits inside an ``#if PUERTS_3``
    region, because those are the types a 2.x host does not have (GitHub issue #4: CS0246);
  - the 2.x environment is constructed inside the matching ``#else`` region;
  - the ``jsEnv`` field is declared once per branch and every other ``jsEnv`` use is
    unconditional, so no request-handling path is version-specific;
  - no other Editor source file reintroduces a 3.x-only type unguarded.

Comments and string literals are blanked before matching, so prose and endpoint names such
as ``/reset-jsenv`` cannot satisfy or violate an invariant. These assertions read source,
so they run in the mocked unit-test layer with no Editor.
"""
import json
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "packages" / "com.txcombo.unity-puer-exec"
EDITOR_ASMDEF_PATH = PACKAGE_ROOT / "Editor" / "UnityPuerExec.Editor.asmdef"
SERVER_PATH = PACKAGE_ROOT / "Editor" / "UnityPuerExecServer.cs"
EDITOR_SOURCE_DIR = PACKAGE_ROOT / "Editor"

PUERTS_PACKAGE_NAME = "com.tencent.puerts.core"
PUERTS_3_DEFINE = "PUERTS_3"
# A bare version means "this version or higher": cinemachine gates the same package at 5.3.1,
# 7.3.1 and 14.0.0 with three cumulative defines, which only reads as a floor. The open-ended
# bracket form "[3.0.0" that issue #4 suggested is NOT that floor -- it matches nothing and
# Unity ignores it silently, observed as an absent PUERTS_3 in a 3.0.0 host's response file.
# Bracketed expressions in real packages always carry both bounds.
PUERTS_3_EXPRESSION = "3.0.0"

BRANCH_PUERTS_3 = "puerts3"
BRANCH_PUERTS_2 = "puerts2"
BRANCH_UNCONDITIONAL = "unconditional"

# Word-bounded on purpose. The version-neutral method name CreateScriptEnv and the
# 3.x-only JsBackendTypeNames array must not match, so a call site written once for both
# majors stays unconditional.
PUERTS_3_ONLY_TOKEN = re.compile(r"\b(?:ScriptEnv|Backend)\b")
JS_ENV_CONSTRUCTION = re.compile(r"\bnew\s+JsEnv\s*\(")
FIELD_DECLARATION = re.compile(r"\bprivate\s+static\s+(?P<type>\w+)\s+jsEnv\s*;")
JS_ENV_USE = re.compile(r"\bjsEnv\b")
PUERTS_2_FACTORY = re.compile(
    r"\bprivate\s+static\s+JsEnv\s+CreateScriptEnv\s*\(\s*ILoader\s+\w+\s*\)"
)


def code_view(source):
    """Return ``source`` with comments and literal contents blanked, offsets preserved.

    Blanking rather than deleting keeps every line and column where the original had it, so
    the branch scanner and the token matches can share one view of the file.
    """
    out = []
    index = 0
    length = len(source)
    state = "code"
    while index < length:
        char = source[index]
        following = source[index + 1] if index + 1 < length else ""
        if state == "code":
            if char == "/" and following == "/":
                state = "line_comment"
                out.append("  ")
                index += 2
                continue
            if char == "/" and following == "*":
                state = "block_comment"
                out.append("  ")
                index += 2
                continue
            if char == "@":
                if following == '"':
                    state = "verbatim_string"
                    out.append(' "')
                    index += 2
                    continue
                out.append(char)
                index += 1
                continue
            if char == '"':
                state = "string"
                out.append('"')
                index += 1
                continue
            if char == "'":
                state = "char"
                out.append("'")
                index += 1
                continue
            out.append(char)
            index += 1
            continue
        if state == "line_comment":
            if char == "\n":
                state = "code"
                out.append("\n")
            else:
                out.append(" ")
            index += 1
            continue
        if state == "block_comment":
            if char == "*" and following == "/":
                state = "code"
                out.append("  ")
                index += 2
                continue
            out.append("\n" if char == "\n" else " ")
            index += 1
            continue
        if state == "string":
            if char == "\\":
                out.append("  ")
                index += 2
                continue
            if char == '"':
                state = "code"
                out.append('"')
            else:
                out.append(" ")
            index += 1
            continue
        if state == "verbatim_string":
            if char == '"' and following == '"':
                out.append("  ")
                index += 2
                continue
            if char == '"':
                state = "code"
                out.append('"')
            else:
                out.append("\n" if char == "\n" else " ")
            index += 1
            continue
        # state == "char"
        if char == "\\":
            out.append("  ")
            index += 2
            continue
        if char == "'":
            state = "code"
            out.append("'")
        else:
            out.append(" ")
        index += 1
    return "".join(out)


def branch_labels(code):
    """Return the conditional branch each line of ``code`` belongs to.

    Only the frame that actually tests ``PUERTS_3`` decides the label, so a future nested
    ``#if`` on some other symbol cannot make a 3.x-only type look unconditional.
    """
    labels = []
    stack = []
    for line in code.split("\n"):
        directive = line.strip()
        if directive.startswith("#if"):
            stack.append([directive[3:].strip() == PUERTS_3_DEFINE, False])
        elif directive.startswith("#else") or directive.startswith("#elif"):
            if stack:
                stack[-1][1] = True
        elif directive.startswith("#endif"):
            if stack:
                stack.pop()
        label = BRANCH_UNCONDITIONAL
        for tests_puerts_3, in_else in reversed(stack):
            if tests_puerts_3:
                label = BRANCH_PUERTS_2 if in_else else BRANCH_PUERTS_3
                break
        labels.append(label)
    return labels


def read_server():
    source = SERVER_PATH.read_text(encoding="utf-8")
    code = code_view(source)
    return code, code.split("\n"), branch_labels(code)


def matches_with_branches(pattern, lines, labels):
    """Yield ``(line_number, branch, matched_text)`` for every match of ``pattern``."""
    for number, (line, label) in enumerate(zip(lines, labels), start=1):
        for match in pattern.finditer(line):
            yield number, label, match.group(0)


class AsmdefVersionDefineTests(unittest.TestCase):
    def setUp(self):
        self.asmdef = json.loads(EDITOR_ASMDEF_PATH.read_text(encoding="utf-8"))

    def test_exactly_one_version_define_keyed_to_the_puerts_package(self):
        defines = self.asmdef["versionDefines"]
        self.assertEqual(1, len(defines))
        self.assertEqual(PUERTS_PACKAGE_NAME, defines[0]["name"])
        self.assertEqual(PUERTS_3_DEFINE, defines[0]["define"])

    def test_version_define_uses_the_bare_version_floor(self):
        expression = self.asmdef["versionDefines"][0]["expression"]
        self.assertEqual(PUERTS_3_EXPRESSION, expression)
        # The failure this pins is silent: a bracketed expression with one bound parses to
        # nothing, Unity sets no define, and a 3.x host compiles the 2.x branch. It surfaces
        # only as CS0618 on the obsolete JsEnv, which no gate in this repository fails on.
        self.assertFalse(
            expression.startswith("["),
            "a one-sided bracket expression matches nothing; use a bare version floor",
        )

    def test_puerts_assembly_reference_is_unchanged(self):
        # Both majors name their runtime assembly definition com.tencent.puerts.core, so
        # one reference serves both and the version define has something to key against.
        self.assertIn(PUERTS_PACKAGE_NAME, self.asmdef["references"])

    def test_editor_assembly_stays_editor_only(self):
        self.assertEqual(["Editor"], self.asmdef["includePlatforms"])


class ServerVersionSplitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code, cls.lines, cls.labels = read_server()

    def test_puerts_3_only_types_are_all_guarded(self):
        unguarded = [
            (number, text)
            for number, label, text in matches_with_branches(
                PUERTS_3_ONLY_TOKEN, self.lines, self.labels
            )
            if label != BRANCH_PUERTS_3
        ]
        self.assertEqual(
            [],
            unguarded,
            "ScriptEnv/Backend outside an #if PUERTS_3 region would not compile on a 2.x "
            "host (GitHub issue #4): {}".format(unguarded),
        )

    def test_guarded_puerts_3_only_types_are_actually_present(self):
        # A guard with nothing inside it would make the test above pass vacuously.
        guarded = [
            number
            for number, label, _ in matches_with_branches(
                PUERTS_3_ONLY_TOKEN, self.lines, self.labels
            )
            if label == BRANCH_PUERTS_3
        ]
        self.assertTrue(guarded, "no guarded ScriptEnv/Backend reference found")

    def test_two_x_environment_is_constructed_in_the_else_branch(self):
        constructions = list(
            matches_with_branches(JS_ENV_CONSTRUCTION, self.lines, self.labels)
        )
        self.assertEqual(1, len(constructions))
        number, label, _ = constructions[0]
        self.assertEqual(
            BRANCH_PUERTS_2,
            label,
            "line {} constructs JsEnv outside the 2.x branch".format(number),
        )

    def test_two_x_factory_signature_matches_the_three_x_one(self):
        factories = list(
            matches_with_branches(PUERTS_2_FACTORY, self.lines, self.labels)
        )
        self.assertEqual(1, len(factories))
        _, label, _ = factories[0]
        self.assertEqual(BRANCH_PUERTS_2, label)

    def test_field_is_declared_once_per_branch(self):
        declarations = list(
            matches_with_branches(FIELD_DECLARATION, self.lines, self.labels)
        )
        by_branch = {}
        for number, label, text in declarations:
            declared_type = FIELD_DECLARATION.search(text).group("type")
            by_branch.setdefault(label, []).append((number, declared_type))
        self.assertEqual(
            {BRANCH_PUERTS_3: 1, BRANCH_PUERTS_2: 1},
            {label: len(items) for label, items in by_branch.items()},
            "the jsEnv field must be declared exactly once in each branch",
        )
        self.assertEqual("ScriptEnv", by_branch[BRANCH_PUERTS_3][0][1])
        self.assertEqual("JsEnv", by_branch[BRANCH_PUERTS_2][0][1])

    def test_every_other_jsenv_use_is_unconditional(self):
        declaration_lines = {
            number
            for number, _, _ in matches_with_branches(
                FIELD_DECLARATION, self.lines, self.labels
            )
        }
        conditional_uses = [
            (number, label)
            for number, label, _ in matches_with_branches(
                JS_ENV_USE, self.lines, self.labels
            )
            if number not in declaration_lines and label != BRANCH_UNCONDITIONAL
        ]
        self.assertEqual(
            [],
            conditional_uses,
            "a version-specific jsEnv use means a request path now depends on the host's "
            "PuerTS major: {}".format(conditional_uses),
        )

    def test_jsenv_is_used_on_the_request_paths(self):
        # Guard against the invariant above being satisfied by deleting the call sites.
        uses = [
            number
            for number, _, _ in matches_with_branches(
                JS_ENV_USE, self.lines, self.labels
            )
        ]
        self.assertLess(5, len(uses))


class OtherEditorSourcesTests(unittest.TestCase):
    def test_no_other_editor_source_uses_a_puerts_3_only_type(self):
        offenders = []
        for path in sorted(EDITOR_SOURCE_DIR.glob("*.cs")):
            if path == SERVER_PATH:
                continue
            code = code_view(path.read_text(encoding="utf-8"))
            labels = branch_labels(code)
            for number, label, text in matches_with_branches(
                PUERTS_3_ONLY_TOKEN, code.split("\n"), labels
            ):
                if label != BRANCH_PUERTS_3:
                    offenders.append("{}:{} {}".format(path.name, number, text))
        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
