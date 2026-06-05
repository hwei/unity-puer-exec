import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CLI_DIR = REPO_ROOT / "cli" / "python"
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))

import unity_log_brief  # type: ignore
import unity_puer_exec  # type: ignore


def _write_log(content):
    f = tempfile.NamedTemporaryFile(mode="wb", suffix=".log", delete=False)
    f.write(content.encode("utf-8"))
    f.close()
    return f.name


class ParseLogBriefsTests(unittest.TestCase):
    def test_compiler_output_error_line(self):
        content = (
            "-----CompilerOutput:-stderr--exitcode-1--\n"
            "Assets/Foo.cs(10,5): error CS0246: type not found\n"
            "-----EndCompilerOutput"
        )
        path = _write_log(content)
        try:
            size = os.path.getsize(path)
            briefs = unity_log_brief.parse_log_briefs(path, 0, size)
            self.assertEqual(len(briefs), 1)
            self.assertEqual(briefs[0]["level"], "error")
            self.assertIn("CS0246", briefs[0]["text"])
            self.assertEqual(briefs[0]["line_count"], 1)
            self.assertEqual(briefs[0]["index"], 1)
        finally:
            os.unlink(path)

    def test_compiler_output_warning_line(self):
        content = (
            "-----CompilerOutput:-stderr--exitcode-0--\n"
            "Assets/Bar.cs(5,3): warning CS0168: variable declared but unused\n"
            "-----EndCompilerOutput"
        )
        path = _write_log(content)
        try:
            size = os.path.getsize(path)
            briefs = unity_log_brief.parse_log_briefs(path, 0, size)
            self.assertEqual(len(briefs), 1)
            self.assertEqual(briefs[0]["level"], "warning")
        finally:
            os.unlink(path)

    def test_compiler_output_info_line(self):
        content = (
            "-----CompilerOutput:-stderr--exitcode-0--\n"
            "Compilation succeeded\n"
            "-----EndCompilerOutput"
        )
        path = _write_log(content)
        try:
            size = os.path.getsize(path)
            briefs = unity_log_brief.parse_log_briefs(path, 0, size)
            self.assertEqual(len(briefs), 1)
            self.assertEqual(briefs[0]["level"], "info")
        finally:
            os.unlink(path)

    def test_runtime_traceback_grouping(self):
        # No trailing newline to avoid extra unknown brief from empty last element.
        content = (
            "[Error] Something failed\n"
            "  at SomeMethod () [0x00000] in <filename unknown>:0\n"
            "  at AnotherMethod () [0x00001] in <filename unknown>:0"
        )
        path = _write_log(content)
        try:
            size = os.path.getsize(path)
            briefs = unity_log_brief.parse_log_briefs(path, 0, size)
            self.assertEqual(len(briefs), 1)
            self.assertEqual(briefs[0]["level"], "error")
            self.assertEqual(briefs[0]["line_count"], 3)
        finally:
            os.unlink(path)

    def test_runtime_warning_entry(self):
        content = "[Warning] Deprecated API called"
        path = _write_log(content)
        try:
            size = os.path.getsize(path)
            briefs = unity_log_brief.parse_log_briefs(path, 0, size)
            self.assertEqual(len(briefs), 1)
            self.assertEqual(briefs[0]["level"], "warning")
        finally:
            os.unlink(path)

    def test_runtime_info_entry(self):
        content = "Application started successfully"
        path = _write_log(content)
        try:
            size = os.path.getsize(path)
            briefs = unity_log_brief.parse_log_briefs(path, 0, size)
            self.assertEqual(len(briefs), 1)
            self.assertEqual(briefs[0]["level"], "info")
        finally:
            os.unlink(path)

    def test_unknown_fallback_merged(self):
        # No trailing newline so split produces exactly 2 lines.
        content = (
            "  indented line one\n"
            "  indented line two"
        )
        path = _write_log(content)
        try:
            size = os.path.getsize(path)
            briefs = unity_log_brief.parse_log_briefs(path, 0, size)
            self.assertEqual(len(briefs), 1)
            self.assertEqual(briefs[0]["level"], "unknown")
            self.assertEqual(briefs[0]["line_count"], 2)
            self.assertIsNone(briefs[0]["text"])
        finally:
            os.unlink(path)

    def test_unity_style_non_indented_stacktrace(self):
        # Unity Debug.Log format: non-indented stack frames + blank + (Filename:) footer.
        # Each [Message] line is one logical log entry regardless of how many stack
        # frame lines follow it.
        content = (
            "[UnityPuerExec] Exec accepted\n"
            "UnityEngine.StackTraceUtility:ExtractStackTrace ()\n"
            "UnityEngine.Debug:Log (object)\n"
            "\n"
            "(Filename: ExecServer.cs Line: 42)\n"
            "\n"
            "[UnityPuerExec] Exec starting\n"
            "UnityEngine.StackTraceUtility:ExtractStackTrace ()\n"
            "UnityEngine.Debug:Log (object)\n"
            "\n"
            "(Filename: ExecServer.cs Line: 88)\n"
        )
        path = _write_log(content)
        try:
            size = os.path.getsize(path)
            briefs = unity_log_brief.parse_log_briefs(path, 0, size)
            info_briefs = [b for b in briefs if b["level"] == "info"]
            self.assertEqual(len(info_briefs), 2)
            self.assertTrue(info_briefs[0]["text"].startswith("[UnityPuerExec] Exec accepted"))
            self.assertTrue(info_briefs[1]["text"].startswith("[UnityPuerExec] Exec starting"))
            # Each brief spans header + 2 stack frames + blank + (Filename:) footer = 5
            # lines, and stops BEFORE the trailing blank that separates the next entry.
            self.assertEqual(info_briefs[0]["line_count"], 5)
            self.assertEqual(info_briefs[1]["line_count"], 5)
        finally:
            os.unlink(path)

    def test_unity_style_blank_separated_entries_do_not_merge(self):
        # Two entries separated only by a blank line must NOT be merged.
        content = (
            "Message one\n"
            "\n"
            "Message two\n"
        )
        path = _write_log(content)
        try:
            size = os.path.getsize(path)
            briefs = unity_log_brief.parse_log_briefs(path, 0, size)
            info_briefs = [b for b in briefs if b["level"] == "info"]
            self.assertEqual(len(info_briefs), 2)
        finally:
            os.unlink(path)

    def test_unity_real_multiframe_entry_with_footer(self):
        # Shape taken from a real Editor.log: a header followed by 8 non-indented
        # stack frames (some with "(at ./path:line)" suffixes), a blank, and the
        # "(Filename: ... Line: N)" footer. The whole block is one brief.
        content = (
            "[UnityPuerExec] Ready on port 55231\n"
            "UnityEngine.StackTraceUtility:ExtractStackTrace ()\n"
            "UnityEngine.DebugLogHandler:LogFormat (UnityEngine.LogType,UnityEngine.Object,string,object[])\n"
            "UnityEngine.Logger:Log (UnityEngine.LogType,object)\n"
            "UnityEngine.Debug:Log (object)\n"
            "UnityPuerExec.UnityPuerExecServer:Start () (at ./Library/PackageCache/com.txcombo.unity-puer-exec@0.4.0/Editor/UnityPuerExecServer.cs:276)\n"
            "UnityPuerExec.UnityPuerExecServer:.cctor () (at ./Library/PackageCache/com.txcombo.unity-puer-exec@0.4.0/Editor/UnityPuerExecServer.cs:190)\n"
            "System.Runtime.CompilerServices.RuntimeHelpers:RunClassConstructor (System.RuntimeTypeHandle)\n"
            "UnityEditor.EditorAssemblies:ProcessInitializeOnLoadAttributes (System.Type[])\n"
            "\n"
            "(Filename: ./Library/PackageCache/com.txcombo.unity-puer-exec@0.4.0/Editor/UnityPuerExecServer.cs Line: 276)\n"
        )
        path = _write_log(content)
        try:
            size = os.path.getsize(path)
            briefs = unity_log_brief.parse_log_briefs(path, 0, size)
            self.assertEqual(len(briefs), 1)
            self.assertEqual(briefs[0]["level"], "info")
            self.assertTrue(briefs[0]["text"].startswith("[UnityPuerExec] Ready on port"))
            # header + 8 frames + blank + footer = 11 lines.
            self.assertEqual(briefs[0]["line_count"], 11)
        finally:
            os.unlink(path)

    def test_unity_domain_reload_block_collapses_to_one_brief(self):
        # Real Editor.log emits back-to-back non-indented native lines (no blank
        # separators) followed by tab-indented children. Under the blank-line
        # boundary rule these all collapse into ONE coarse brief. Pin that so a
        # future change does not silently re-split native noise.
        content = (
            "Mono: successfully reloaded assembly\n"
            "- Finished resetting the current domain, in  3.694 seconds\n"
            "Domain Reload Profiling: 4602ms\n"
            "\tBeginReloadAssembly (192ms)\n"
            "\t\tExecutionOrderSort (0ms)\n"
            "\tFinalizeReload (3694ms)"  # no trailing newline -> exactly 6 lines
        )
        path = _write_log(content)
        try:
            size = os.path.getsize(path)
            briefs = unity_log_brief.parse_log_briefs(path, 0, size)
            self.assertEqual(len(briefs), 1)
            self.assertEqual(briefs[0]["level"], "info")
            self.assertTrue(briefs[0]["text"].startswith("Mono: successfully reloaded"))
            self.assertEqual(briefs[0]["line_count"], 6)
        finally:
            os.unlink(path)

    def test_level_lost_when_entries_lack_blank_separator(self):
        # Stack-trace-OFF failure mode: without the blank separators that a stack
        # trace + (Filename:) footer normally provide, consecutive non-indented
        # lines merge into the first entry and their levels are silently lost.
        # This is exactly the degraded condition the C#-side GetStackTraceLogType
        # detection exists to flag; pinning it keeps that motivation legible.
        content = (
            "Plain status line\n"
            "[Error] boom\n"
            "[Warning] careful"  # no trailing newline -> exactly 3 lines
        )
        path = _write_log(content)
        try:
            size = os.path.getsize(path)
            briefs = unity_log_brief.parse_log_briefs(path, 0, size)
            self.assertEqual(len(briefs), 1)
            # Level comes from the first line only; the Error/Warning are absorbed.
            self.assertEqual(briefs[0]["level"], "info")
            self.assertEqual([b["level"] for b in briefs].count("error"), 0)
            self.assertEqual([b["level"] for b in briefs].count("warning"), 0)
            self.assertEqual(briefs[0]["line_count"], 3)
        finally:
            os.unlink(path)

    def test_multiple_entries(self):
        content = (
            "First info entry\n"
            "\n"
            "[Warning] Second entry\n"
            "\n"
            "[Error] Third entry\n"
        )
        path = _write_log(content)
        try:
            size = os.path.getsize(path)
            briefs = unity_log_brief.parse_log_briefs(path, 0, size)
            levels = [b["level"] for b in briefs]
            self.assertIn("info", levels)
            self.assertIn("warning", levels)
            self.assertIn("error", levels)
        finally:
            os.unlink(path)

    def test_empty_range_returns_empty(self):
        content = "Some log content\n"
        path = _write_log(content)
        try:
            briefs = unity_log_brief.parse_log_briefs(path, 5, 5)
            self.assertEqual(briefs, [])
        finally:
            os.unlink(path)

    def test_nonexistent_file_returns_empty(self):
        briefs = unity_log_brief.parse_log_briefs("/nonexistent/path/file.log", 0, 100)
        self.assertEqual(briefs, [])

    def test_text_capped_at_100_chars(self):
        long_line = "A" * 200
        content = long_line
        path = _write_log(content)
        try:
            size = os.path.getsize(path)
            briefs = unity_log_brief.parse_log_briefs(path, 0, size)
            self.assertEqual(len(briefs), 1)
            self.assertIsNotNone(briefs[0]["text"])
            self.assertLessEqual(len(briefs[0]["text"]), 100)
        finally:
            os.unlink(path)

    def test_1based_index_increments(self):
        content = (
            "First entry\n"
            "\n"
            "[Warning] Second entry\n"
        )
        path = _write_log(content)
        try:
            size = os.path.getsize(path)
            briefs = unity_log_brief.parse_log_briefs(path, 0, size)
            indices = [b["index"] for b in briefs]
            self.assertEqual(indices, list(range(1, len(indices) + 1)))
        finally:
            os.unlink(path)


class BuildBriefSequenceTests(unittest.TestCase):
    def test_sequence_chars(self):
        briefs = [
            {"level": "info"},
            {"level": "warning"},
            {"level": "error"},
            {"level": "unknown"},
        ]
        self.assertEqual(unity_log_brief.build_brief_sequence(briefs), "IWE?")

    def test_repeated_runs_use_symbol_plus_count(self):
        briefs = [
            {"level": "warning"},
            {"level": "info"},
            {"level": "info"},
            {"level": "info"},
            {"level": "error"},
            {"level": "error"},
            {"level": "info"},
        ]
        self.assertEqual(unity_log_brief.build_brief_sequence(briefs), "WI3E2I")

    def test_empty_sequence(self):
        self.assertEqual(unity_log_brief.build_brief_sequence([]), "")

    def test_unknown_level_maps_to_question_mark(self):
        briefs = [{"level": "bogus"}]
        self.assertEqual(unity_log_brief.build_brief_sequence(briefs), "?")


class FilterBriefsTests(unittest.TestCase):
    def _sample_briefs(self):
        return [
            {"index": 1, "level": "info"},
            {"index": 2, "level": "warning"},
            {"index": 3, "level": "error"},
            {"index": 4, "level": "info"},
        ]

    def test_no_filter_returns_all(self):
        briefs = self._sample_briefs()
        result = unity_log_brief.filter_briefs(briefs)
        self.assertEqual(len(result), 4)

    def test_filter_by_level(self):
        briefs = self._sample_briefs()
        result = unity_log_brief.filter_briefs(briefs, levels=["error"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["level"], "error")

    def test_filter_by_index(self):
        briefs = self._sample_briefs()
        result = unity_log_brief.filter_briefs(briefs, include_indices=[2, 4])
        self.assertEqual([b["index"] for b in result], [2, 4])

    def test_union_semantics(self):
        briefs = self._sample_briefs()
        # levels=["error"] gives index 3; include_indices=[2] gives index 2 (warning)
        result = unity_log_brief.filter_briefs(briefs, levels=["error"], include_indices=[2])
        indices = [b["index"] for b in result]
        self.assertIn(2, indices)
        self.assertIn(3, indices)
        self.assertEqual(len(result), 2)

    def test_no_duplicates_in_union(self):
        briefs = self._sample_briefs()
        # error is at index 3; also request index 3 explicitly
        result = unity_log_brief.filter_briefs(briefs, levels=["error"], include_indices=[3])
        self.assertEqual(len(result), 1)

    def test_preserves_original_order(self):
        briefs = self._sample_briefs()
        result = unity_log_brief.filter_briefs(briefs, include_indices=[4, 1])
        self.assertEqual([b["index"] for b in result], [1, 4])


class GetLogBriefsCliTests(unittest.TestCase):
    def _run(self, argv):
        return unity_puer_exec.run_cli(argv)

    def _make_log(self, content):
        f = tempfile.NamedTemporaryFile(mode="wb", suffix=".log", delete=False)
        f.write(content.encode("utf-8"))
        f.close()
        return f.name

    def test_get_log_briefs_returns_all_briefs(self):
        content = (
            "First entry\n"
            "\n"
            "[Error] Second entry\n"
        )
        path = self._make_log(content)
        try:
            size = os.path.getsize(path)
            exit_code, stdout, stderr = self._run([
                "get-log-briefs",
                "--unity-log-path", path,
                "--range", "0-{}".format(size),
            ])
            self.assertEqual(exit_code, 0)
            body = json.loads(stdout)
            self.assertTrue(body["ok"])
            self.assertIsInstance(body["result"], list)
            levels = [b["level"] for b in body["result"]]
            self.assertIn("error", levels)
        finally:
            os.unlink(path)

    def test_get_log_briefs_range_comma_form(self):
        content = "[Warning] A warning"
        path = self._make_log(content)
        try:
            size = os.path.getsize(path)
            exit_code, stdout, _ = self._run([
                "get-log-briefs",
                "--unity-log-path", path,
                "--range", "0,{}".format(size),
            ])
            self.assertEqual(exit_code, 0)
            body = json.loads(stdout)
            self.assertEqual(len(body["result"]), 1)
        finally:
            os.unlink(path)

    def test_get_log_briefs_filter_by_levels(self):
        content = (
            "Info entry\n"
            "\n"
            "[Error] Error entry\n"
        )
        path = self._make_log(content)
        try:
            size = os.path.getsize(path)
            exit_code, stdout, _ = self._run([
                "get-log-briefs",
                "--unity-log-path", path,
                "--range", "0-{}".format(size),
                "--levels", "error",
            ])
            self.assertEqual(exit_code, 0)
            body = json.loads(stdout)
            for b in body["result"]:
                self.assertEqual(b["level"], "error")
        finally:
            os.unlink(path)

    def test_get_log_briefs_filter_by_include(self):
        content = (
            "Info entry one\n"
            "\n"
            "[Warning] Warning entry\n"
            "\n"
            "[Error] Error entry\n"
        )
        path = self._make_log(content)
        try:
            size = os.path.getsize(path)
            exit_code, stdout, _ = self._run([
                "get-log-briefs",
                "--unity-log-path", path,
                "--range", "0-{}".format(size),
                "--include", "1",
            ])
            self.assertEqual(exit_code, 0)
            body = json.loads(stdout)
            indices = [b["index"] for b in body["result"]]
            self.assertIn(1, indices)
            self.assertNotIn(2, indices)
        finally:
            os.unlink(path)

    def test_get_log_briefs_invalid_range_raises_usage_error(self):
        exit_code, stdout, stderr = self._run([
            "get-log-briefs",
            "--range", "notanumber",
        ])
        self.assertEqual(exit_code, 2)

    def test_get_log_briefs_empty_range_returns_empty_result(self):
        content = "Some content\n"
        path = self._make_log(content)
        try:
            exit_code, stdout, _ = self._run([
                "get-log-briefs",
                "--unity-log-path", path,
                "--range", "0-0",
            ])
            self.assertEqual(exit_code, 0)
            body = json.loads(stdout)
            self.assertEqual(body["result"], [])
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
