"""Source invariants for the import-change signal.

The import-change signal is the incremental filesystem scan alone: every decision walks
the watched roots and compares compile-triggering files' modification times against the
settled-import timestamp. There is no filesystem watcher and no off-thread callback path
to audit. What is checked mechanically here is the structural contract that remains:

  - the settled-import timestamp has exactly one writer, Unity's completion hook, and
    nothing on the scan or exec path assigns it;
  - the mtime scan yields candidates, and a content ledger drops the ones already handed
    to a dispatched refresh; the ledger has one writer, is cleared by the timestamp's only
    writer, suppresses only past a grace window and only while the Editor is idle, and is
    applied by both the decision and the health-side pending view;
  - the content hash is paid only for flagged paths, never inside the scan itself;
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
SESSION_COMMON_PATH = REPO_ROOT / "cli" / "python" / "unity_session_common.py"

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

    def test_settled_timestamp_advance_clears_the_content_ledger(self):
        # The ledger covers one unsettled epoch: content handed to a dispatched refresh
        # since the timestamp last advanced. An entry surviving that advance could only
        # suppress a later identical write Unity has not seen.
        completion = _extract_method_body(self.source, "void OnCompilationCompleted()")
        self.assertIn("RefreshedContentLedger.Clear();", completion)

    def test_decision_and_pending_state_share_the_content_filter(self):
        # /health and the refresh decision must not disagree: a pending state nothing will
        # ever act on keeps wait-for-compile reporting compile_blocked forever.
        for signature in (
            "PendingState GetPendingState()",
            "RefreshDecision Decide()",
        ):
            body = _extract_method_body(self.source, signature)
            self.assertIn(
                "FilterAlreadyRefreshedContent(",
                body,
                "{} must apply the content ledger".format(signature),
            )

    def test_content_ledger_has_a_single_writer(self):
        # Only the post-dispatch record may write the ledger, and the server calls it only
        # on the branch where AssetDatabase.Refresh() returned without throwing. A write on
        # the scan or decision path would suppress content Unity was never asked to import.
        record = _extract_method_body(
            self.source, "void OnRefreshDispatched(RefreshDecision decision)"
        )
        self.assertIn(
            "RefreshedContentLedger[candidate.Path] = new RefreshedContentEntry", record
        )

        for signature in (
            "PendingState GetPendingState()",
            "RefreshDecision Decide()",
            "List<string> ScanWatchedRoots()",
            "void FilterAlreadyRefreshedContent(",
        ):
            body = _extract_method_body(self.source, signature)
            self.assertNotIn(
                "RefreshedContentLedger[",
                body,
                "{} must not record content into the ledger".format(signature),
            )

    def test_suppression_is_gated_on_grace_and_editor_activity(self):
        # A matching entry may suppress only once it has aged past the grace window and the
        # Editor is neither compiling nor importing. Without both gates a caller that
        # re-asks faster than Unity starts the compile reads a settled build that does not
        # exist yet -- a failing one included, which let `play` enter play mode instead of
        # aborting on the compile error.
        body = _extract_method_body(self.source, "void FilterAlreadyRefreshedContent(")
        self.assertIn("PostRefreshSettleGraceTicks", body)
        self.assertIn("!busy", body)
        self.assertIn("editorCompilingOrUpdating", body)
        self.assertIn("entry.DispatchedUtcTicks", body)

    def test_editor_activity_is_sampled_on_the_update_tick(self):
        # EditorApplication's flags are main-thread-only and the pending view is answered on
        # the listener thread, so both decision paths gate on one tick-sampled snapshot.
        body = _extract_method_body(self.source, "void OnEditorUpdate()")
        self.assertIn("editorCompilingOrUpdating =", body)
        self.assertIn("EditorApplication.isCompiling", body)
        self.assertIn("EditorApplication.isUpdating", body)

    def test_a_redispatch_does_not_extend_the_grace_window(self):
        # First dispatch wins. A caller that re-asks before the grace elapses re-dispatches
        # the same content; stamping that re-dispatch would push the grace out again and
        # restore the loop the ledger exists to end.
        record = _extract_method_body(
            self.source, "void OnRefreshDispatched(RefreshDecision decision)"
        )
        self.assertIn(
            "RefreshedContentLedger.TryGetValue(candidate.Path, out existing)", record
        )
        self.assertIn("existing.ContentHash, candidate.ContentHash", record)
        self.assertIn("continue;", record)

    def test_grace_is_shorter_than_the_cli_compile_appear_window(self):
        # The host must acknowledge a no-compile refresh before the caller's own appear
        # window expires, so a caller that waits out that window and then re-asks always
        # re-asks after the grace elapsed and resolves in one invocation.
        match = re.search(
            r"PostRefreshSettleGraceTicks\s*=\s*(\d+)\s*\*\s*TimeSpan\.TicksPerSecond",
            self.source,
        )
        self.assertIsNotNone(match, "post-refresh settle grace constant not found")
        grace_seconds = int(match.group(1))

        appear = re.search(
            r"DEFAULT_COMPILE_APPEAR_TIMEOUT_SECONDS\s*=\s*([0-9.]+)",
            SESSION_COMMON_PATH.read_text(encoding="utf-8"),
        )
        self.assertIsNotNone(appear, "CLI compile appear window not found")
        appear_seconds = float(appear.group(1))

        self.assertGreater(grace_seconds, 0)
        self.assertLess(
            grace_seconds,
            appear_seconds,
            "grace {}s must stay under the CLI appear window {}s".format(
                grace_seconds, appear_seconds
            ),
        )

    def test_unreadable_content_is_never_suppressed(self):
        # A candidate that cannot be read hashes to null, and null never matches a recorded
        # entry, so a locked or vanished file stays a change instead of being dropped.
        body = _extract_method_body(self.source, "void FilterAlreadyRefreshedContent(")
        self.assertIn("hash != null", body)

        hasher = _extract_method_body(self.source, "string SafeContentHash(string path)")
        self.assertIn("return null;", hasher)

    def test_scan_reads_no_file_content(self):
        # The content hash is paid only for paths the mtime comparison already flagged, so a
        # settled tree still costs directory enumeration and stat alone.
        for signature in (
            "List<string> ScanWatchedRoots()",
            "void Walk(string directory",
            "void IncrementalScan(string directory",
        ):
            body = _extract_method_body(self.source, signature)
            self.assertNotIn(
                "SafeContentHash(",
                body,
                "{} must not read file content".format(signature),
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
