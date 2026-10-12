"""Source invariants for the import-change signal (refresh-on-change task 3.3).

The watcher callback path cannot be exercised end to end in this repository: on
Windows the Unity Editor's embedded Mono delivers no FileSystemWatcher events, and a
real InternalBufferOverflowException cannot be produced on demand. What *can* be
checked mechanically is the structural contract those callbacks must obey:

  - callbacks run on a threadpool thread, so they may not touch a Unity API (not even
    the logger) and may only mutate thread-safe state;
  - the settled-import timestamp has exactly one writer, Unity's completion hook, and
    nothing on the watcher or exec path assigns it;
  - the extension filter is the compile-triggering set and nothing else.

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

# Methods that FileSystemWatcher invokes from a threadpool thread, plus the helper they
# funnel into. None of these may reference a Unity API.
CALLBACK_METHOD_SIGNATURES = (
    "void OnWatcherChanged(object sender",
    "void OnWatcherRenamed(object sender",
    "void OnWatcherError(object sender",
    "void AddCandidate(string path)",
)

# Helpers the callbacks call. They must stay pure (System.IO / plain data) too.
CALLBACK_HELPER_SIGNATURES = (
    "bool IsCompileTriggeringPath(string path)",
    "bool IsExcludedPath(string normalizedPath)",
    "bool IsExcludedPath(string normalizedPath, bool",
    "string NormalizePath(string path)",
)

UNITY_API_TOKENS = (
    "UnityEngine",
    "UnityEditor",
    "Debug.",
    "AssetDatabase",
    "EditorApplication",
    "SessionState",
    "CompilationPipeline",
    "Application.",
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

    def test_watcher_callbacks_touch_no_unity_api(self):
        for signature in CALLBACK_METHOD_SIGNATURES + CALLBACK_HELPER_SIGNATURES:
            body = _extract_method_body(self.source, signature)
            for token in UNITY_API_TOKENS:
                self.assertNotIn(
                    token,
                    body,
                    "{} must not reference {} from the watcher callback path".format(signature, token),
                )

    def test_compile_triggering_extensions_are_code_only(self):
        match = re.search(r"CompileTriggeringExtensions\s*=\s*\{([^}]*)\}", self.source)
        self.assertIsNotNone(match, "extension filter declaration not found")
        extensions = re.findall(r'"(\.\w+)"', match.group(1))
        self.assertEqual(
            sorted(extensions),
            sorted([".cs", ".asmdef", ".asmref", ".rsp"]),
            "the watched filter must be exactly the compile-triggering set",
        )

    def test_callbacks_coalesce_into_a_thread_safe_candidate_set(self):
        # The candidate set is the coalescing point: repeated events for one path
        # collapse to a single entry.
        self.assertIn("HashSet<string> CandidatePaths", self.source)
        self.assertIn("StringComparer.OrdinalIgnoreCase", self.source)

        add_candidate = _extract_method_body(self.source, "void AddCandidate(string path)")
        self.assertIn("lock (Gate)", add_candidate)
        self.assertIn("CandidatePaths.Add", add_candidate)

        # Both watcher file-event handlers funnel through the coalescing helper rather
        # than mutating shared state inline.
        for signature in ("void OnWatcherChanged(object sender", "void OnWatcherRenamed(object sender"):
            body = _extract_method_body(self.source, signature)
            self.assertIn("AddCandidate(", body, signature)

    def test_watcher_error_invalidates_the_signal(self):
        body = _extract_method_body(self.source, "void OnWatcherError(object sender")
        self.assertIn("signalValid = false", body)
        # The diagnostic is recorded as plain state; the logger is not called from the
        # callback thread.
        self.assertIn("deferredSignalError", body)
        self.assertNotIn("Debug.", body)

    def test_callbacks_are_wired_to_every_relevant_watcher_event(self):
        for wiring in (
            "watcher.Changed += OnWatcherChanged;",
            "watcher.Created += OnWatcherChanged;",
            "watcher.Deleted += OnWatcherChanged;",
            "watcher.Renamed += OnWatcherRenamed;",
            "watcher.Error += OnWatcherError;",
        ):
            self.assertIn(wiring, self.source)

    def test_settled_timestamp_has_a_single_writer(self):
        # Only the completion hook (and Install's restore of the persisted value) may
        # assign the timestamp. The watcher and exec paths must never advance it.
        completion = _extract_method_body(self.source, "void OnCompilationCompleted()")
        self.assertIn("settledImportUtcTicks = DateTime.UtcNow.Ticks;", completion)

        install = _extract_method_body(self.source, "void Install()")
        self.assertIn("settledImportUtcTicks = LoadPersistedTicks();", install)

        for signature in (
            "PendingState GetPendingState()",
            "RefreshDecision Decide()",
            "void OnWatcherChanged(object sender",
            "void OnWatcherRenamed(object sender",
            "void OnWatcherError(object sender",
            "void AddCandidate(string path)",
            "void BaselineWalk(long thresholdTicks)",
        ):
            body = _extract_method_body(self.source, signature)
            self.assertNotIn(
                "settledImportUtcTicks =",
                body,
                "{} must not advance the settled-import timestamp".format(signature),
            )

    def test_install_runs_the_baseline_walk(self):
        install = _extract_method_body(self.source, "void Install()")
        self.assertIn("BaselineWalk(threshold)", install)

    def test_completion_hook_clears_candidates_and_revalidates_signal(self):
        completion = _extract_method_body(self.source, "void OnCompilationCompleted()")
        self.assertIn("CandidatePaths.Clear()", completion)
        self.assertIn("signalValid = Watchers.Count > 0", completion)

    def test_watched_roots_are_cached_for_the_exclusion_helper(self):
        # The normalized watched roots must be captured when the tracker is
        # installed so the pure exclusion helper can scope the dot-directory rule
        # without calling a Unity API on the callback path.
        self.assertIn("watchedRoots", self.source)

        start = _extract_method_body(self.source, "void StartWatchersLocked()")
        self.assertIn("watchedRoots =", start)
        self.assertIn("NormalizePath(root)", start)

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
