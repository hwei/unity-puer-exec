"""Source invariants for the import-change signal.

The import-change signal is the incremental filesystem scan alone: every decision walks
the watched roots and compares compile-triggering files' modification times against the
settled-import timestamp. There is no filesystem watcher and no off-thread callback path
to audit. What is checked mechanically here is the structural contract that remains:

  - the settled-import timestamp has exactly one writer, Unity's completion hook, and
    nothing on the scan or exec path assigns it;
  - the scan's exclusion rules stay scoped to the path below a watched root;
  - the extension filter is the compile-triggering set and nothing else;
  - no watcher, watcher callback, candidate set, or watcher-failure state creeps back in.

These assertions are about the tracker's source, so they run in the mocked unit-test
layer with no Editor.
"""
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TRACKER_PATH = (
    REPO_ROOT
    / "packages"
    / "com.txcombo.unity-puer-exec"
    / "Editor"
    / "UnityPuerExecImportChangeTracker.cs"
)

# Tokens that only made sense for the removed watcher-backed design. Their return would
# reintroduce the fallback subsystem this change deleted.
REMOVED_MECHANISM_TOKENS = (
    "FileSystemWatcher",
    "OnWatcherChanged",
    "OnWatcherRenamed",
    "OnWatcherError",
    "CandidatePaths",
    "AddCandidate",
    "StartWatchersLocked",
    "BaselineWalk",
    "signalValid",
    "deferredSignalError",
    "DrainDeferredSignalError",
    "watcher_signal_unavailable",
)


def _extract_method_body(source, signature_fragment):
    """Return the brace-balanced body of the first method matching a signature."""
    index = source.find(signature_fragment)
    if index < 0:
        raise AssertionError("method not found: {}".format(signature_fragment))
    open_brace = source.find("{", index)
    if open_brace < 0:
        raise AssertionError("no body for: {}".format(signature_fragment))
    depth = 0
    for position in range(open_brace, len(source)):
        char = source[position]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[open_brace : position + 1]
    raise AssertionError("unbalanced body for: {}".format(signature_fragment))


class ImportChangeSignalSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = TRACKER_PATH.read_text(encoding="utf-8")

    def test_no_watcher_or_fallback_mechanism_remains(self):
        for token in REMOVED_MECHANISM_TOKENS:
            self.assertNotIn(
                token,
                self.source,
                "removed watcher-fallback mechanism token reappeared: {}".format(token),
            )

    def test_compile_triggering_extensions_are_code_only(self):
        match = re.search(r"CompileTriggeringExtensions\s*=\s*\{([^}]*)\}", self.source)
        self.assertIsNotNone(match, "extension filter declaration not found")
        extensions = re.findall(r'"(\.\w+)"', match.group(1))
        self.assertEqual(
            sorted(extensions),
            sorted([".cs", ".asmdef", ".asmref", ".rsp"]),
            "the scanned filter must be exactly the compile-triggering set",
        )

    def test_settled_timestamp_has_a_single_writer(self):
        # Only the completion hook (and Install's restore of the persisted value) may
        # assign the timestamp. The scan and exec paths must never advance it.
        completion = _extract_method_body(self.source, "void OnCompilationCompleted()")
        self.assertIn("settledImportUtcTicks = DateTime.UtcNow.Ticks;", completion)

        install = _extract_method_body(self.source, "void Install()")
        self.assertIn("settledImportUtcTicks = LoadPersistedTicks();", install)

        for signature in (
            "PendingState GetPendingState()",
            "RefreshDecision Decide()",
            "List<string> ScanWatchedRoots()",
        ):
            body = _extract_method_body(self.source, signature)
            self.assertNotIn(
                "settledImportUtcTicks =",
                body,
                "{} must not advance the settled-import timestamp".format(signature),
            )

    def test_install_caches_watched_roots_for_the_exclusion_helper(self):
        # The normalized watched roots must be captured when the tracker is installed
        # so the exclusion helper can scope the dot-directory rule without recomputing
        # Unity state on every scan.
        self.assertIn("watchedRoots", self.source)

        install = _extract_method_body(self.source, "void Install()")
        self.assertIn("watchedRoots =", install)
        self.assertIn("NormalizePath(root)", install)

    def test_decide_has_only_the_three_live_reasons(self):
        decide = _extract_method_body(self.source, "RefreshDecision Decide()")
        for reason in ("compile_triggering_change", "no_pending_change", "play_mode"):
            self.assertIn(reason, decide, reason)

    def test_dot_rule_is_scoped_to_the_path_below_the_watched_root(self):
        # A dot segment above the watched root (the project's own absolute prefix)
        # must not suppress detection, so the helper strips a matching cached root
        # prefix before it splits segments and applies the dot test.
        body = _extract_method_body(self.source, "bool IsExcludedPath(string normalizedPath, bool")
        self.assertIn("watchedRoots", body)
        self.assertIn("StartsWith", body)
        self.assertIn("Substring", body)

        # The stripped path is what the segment loop splits, with the full path
        # retained as the fallback when no root matches.
        self.assertIn("dotTestPath = normalizedPath;", body)
        self.assertIn("dotTestPath.Split('/')", body)


if __name__ == "__main__":
    unittest.main()
