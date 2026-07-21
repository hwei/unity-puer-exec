#!/usr/bin/env python3
"""Log brief parser for Unity Editor log files.

Parses a byte range of the Unity Editor log into structured brief entries.
Briefs are compact summaries of log entries with level (info/warning/error/unknown),
line count, byte offsets, and a short text preview.
"""
import re
from pathlib import Path


LEVEL_INFO = "info"
LEVEL_WARNING = "warning"
LEVEL_ERROR = "error"
LEVEL_UNKNOWN = "unknown"

_BRIEF_SEQUENCE_CHARS = {
    LEVEL_INFO: "I",
    LEVEL_WARNING: "W",
    LEVEL_ERROR: "E",
    LEVEL_UNKNOWN: "?",
}

_COMPILER_OUTPUT_START = "-----CompilerOutput:"
_COMPILER_OUTPUT_END = "-----EndCompilerOutput"


def _compiler_line_level(line):
    if ": error CS" in line:
        return LEVEL_ERROR
    if ": warning CS" in line:
        return LEVEL_WARNING
    return LEVEL_INFO


# Unity always emits a fully-qualified `UnityEngine.Debug:Log*` managed frame for
# every Debug.Log* call (when stack-trace logging is enabled). The `UnityEngine.Debug`
# + `:`/`.` separator anchor is what excludes the per-entry internal frames that are NOT
# the level signal: `UnityEngine.DebugLogHandler:LogFormat` (no separator after `Debug`)
# and `UnityEngine.Logger:Log` (not `Debug`). It also excludes user frames such as
# `MyGame.Debug:LogError`. The optional `(?:Format)?` absorbs the `*Format` overloads.
_DEBUG_FRAME_RE = re.compile(
    r"UnityEngine\.Debug[:.]Log(Error|Warning|Exception|Assertion)?(?:Format)?\b"
)
# Uncaught exceptions surface with a bare `<Type>Exception:` header and no level marker.
_EXCEPTION_HEADER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*Exception:")


def _runtime_entry_level(header_line, entry_lines=None):
    """Derive a runtime entry level, in priority order.

    1. Explicit header marker (`[Error]`/`[Exception]`/`[Warning]`).
    2. The entry's `UnityEngine.Debug:Log*` stack frame — the level the GUI
       Editor.log carries when the header has no marker. Real GUI logs never
       prefix the header, so without this the runtime path collapses to all-info.
    3. A bare uncaught-exception header (`<Type>Exception:`).
    4. Default `info`.

    `entry_lines`, when provided, is the full raw-line span of the entry so the
    frame scan stays bounded to this entry and cannot read a neighbor's frame.
    """
    stripped = header_line.lstrip()
    if stripped.startswith("[Error]") or stripped.startswith("[Exception]"):
        return LEVEL_ERROR
    if stripped.startswith("[Warning]"):
        return LEVEL_WARNING
    if entry_lines:
        for entry_line in entry_lines:
            match = _DEBUG_FRAME_RE.search(entry_line)
            if match:
                variant = match.group(1)
                if variant in ("Error", "Exception", "Assertion"):
                    return LEVEL_ERROR
                if variant == "Warning":
                    return LEVEL_WARNING
                return LEVEL_INFO
    if _EXCEPTION_HEADER_RE.match(stripped):
        return LEVEL_ERROR
    return LEVEL_INFO


def _parse_chunk(raw_bytes, base_offset):
    """Parse a raw log byte range into a list of brief dicts.

    Args:
        raw_bytes: Raw (undecoded) byte content of the log range.
        base_offset: Byte offset of the first byte in raw_bytes.

    Returns:
        List of brief dicts with keys:
            index, level, line_count, start_offset, end_offset, text
    """
    # Split on the raw "\n" byte before decoding so start_offset/end_offset are exact
    # byte boundaries (including CRLF, whose "\r" stays attached to the preceding raw
    # line, and multibyte UTF-8 content, which never contains a literal 0x0A byte).
    raw_line_bytes = raw_bytes.split(b"\n")
    # Drop trailing empty element produced by split on newline-terminated content;
    # without this, the empty string is mis-classified as an unknown brief and
    # breaks brief_sequence prefix consistency across growing log ranges.
    if raw_line_bytes and raw_line_bytes[-1] == b"":
        raw_line_bytes.pop()
    # Compute the exact byte offset for each line start from the raw byte lengths.
    line_byte_starts = []
    current = base_offset
    for line_bytes in raw_line_bytes:
        line_byte_starts.append(current)
        current += len(line_bytes) + 1  # +1 for \n

    raw_lines = [lb.decode("utf-8", errors="replace") for lb in raw_line_bytes]

    briefs = []
    in_compiler_section = False
    i = 0
    pending_unknown_start = None
    pending_unknown_count = 0

    def flush_unknown():
        nonlocal pending_unknown_start, pending_unknown_count
        if pending_unknown_count == 0:
            return
        start_line_idx = pending_unknown_start
        end_line_idx = pending_unknown_start + pending_unknown_count - 1
        brief_start = line_byte_starts[start_line_idx]
        brief_end = line_byte_starts[end_line_idx] + len(raw_line_bytes[end_line_idx]) + 1
        briefs.append({
            "index": len(briefs) + 1,
            "level": LEVEL_UNKNOWN,
            "line_count": pending_unknown_count,
            "start_offset": brief_start,
            "end_offset": brief_end,
            "text": None,
        })
        pending_unknown_start = None
        pending_unknown_count = 0

    def add_brief(level, line_idx_start, line_idx_end):
        """Add a brief covering lines [line_idx_start, line_idx_end] inclusive."""
        flush_unknown()
        first_line = raw_lines[line_idx_start]
        text = first_line[:100] if first_line else None
        brief_start = line_byte_starts[line_idx_start]
        brief_end = line_byte_starts[line_idx_end] + len(raw_line_bytes[line_idx_end]) + 1
        briefs.append({
            "index": len(briefs) + 1,
            "level": level,
            "line_count": line_idx_end - line_idx_start + 1,
            "start_offset": brief_start,
            "end_offset": brief_end,
            "text": text if text else None,
        })

    def accumulate_unknown(line_idx):
        nonlocal pending_unknown_start, pending_unknown_count
        if pending_unknown_start is None:
            pending_unknown_start = line_idx
        pending_unknown_count += 1

    while i < len(raw_lines):
        line = raw_lines[i]
        stripped = line.strip()

        if not in_compiler_section and line.startswith(_COMPILER_OUTPUT_START):
            flush_unknown()
            in_compiler_section = True
            i += 1
            continue

        if in_compiler_section:
            if line.startswith(_COMPILER_OUTPUT_END):
                in_compiler_section = False
                i += 1
                continue
            # Each non-blank line in compiler section is its own brief
            if stripped:
                add_brief(_compiler_line_level(line), i, i)
            # blank lines in compiler section are skipped
            i += 1
            continue

        # Outside compiler section: runtime traceback-based grouping.
        # An entry starts with a non-blank, non-indented line. It continues with
        # subsequent lines until the next entry BOUNDARY, where a boundary is a
        # non-blank, non-indented line that FOLLOWS a blank line. A non-indented
        # line that is NOT preceded by a blank is a continuation (e.g. a Unity
        # stack-frame line, which begins at column 0); the "(Filename: ...)" footer
        # after a blank separator is absorbed as the entry's trailing footer.
        #
        # ASSUMPTION — this grouping only delimits entries correctly when Unity
        # stack-trace logging is ENABLED (StackTraceLogType.ScriptOnly or .Full).
        # With stack traces on, each Debug.Log emits:
        #     <header>\n<stack frames...>\n\n(Filename: X.cs Line: N)\n\n
        # so the blank line after the footer is the boundary the rule keys on.
        # When stack-trace logging is disabled (StackTraceLogType.None), Debug.Log
        # output collapses to bare back-to-back header lines with no blank
        # separators, so this rule MERGES distinct entries and silently loses the
        # levels of all but the first. That degraded condition is NOT detectable
        # here by structure (real Editor.log has back-to-back non-indented native
        # noise — Mono reload, Domain Reload Profiling — even when stack traces are
        # on); it is detected on the C# side via Application.GetStackTraceLogType
        # (see openspec/specs/log-brief and Console > Stack Trace Logging) and
        # surfaced as a brief_sequence sentinel + hint in the exec/wait flow.
        # Unknown: lines that don't fit this pattern.
        #
        # Entry LEVEL is derived once the entry span is finalized (see
        # _runtime_entry_level): header marker first, then the anchored
        # UnityEngine.Debug:Log* frame inside the entry (GUI Editor.log carries no
        # header prefix, so the frame is the level signal there), then a bare
        # <Type>Exception: header, else info.

        if not stripped:
            # Blank line: check if it starts a new entry boundary
            # Look ahead for next non-blank line
            j = i + 1
            while j < len(raw_lines) and not raw_lines[j].strip():
                j += 1
            if j < len(raw_lines) and raw_lines[j] and not raw_lines[j][0].isspace():
                # New entry starts at j - current blanks are separators, not content
                # Flush any accumulated unknown at the gap
                if pending_unknown_count > 0:
                    flush_unknown()
                i = j
                continue
            else:
                # Blank line that is NOT followed by a non-indented line:
                # could be trailing blanks or part of an entry
                # Treat as unknown if we're not mid-entry
                accumulate_unknown(i)
                i += 1
                continue

        if line[0].isspace():
            # Indented line outside a compiler section = unknown
            accumulate_unknown(i)
            i += 1
            continue

        # Non-blank, non-indented line: start of a runtime log entry
        flush_unknown()
        entry_start = i
        header_line = line
        i += 1
        # Consume continuation lines: indented continuations, non-indented Unity stack
        # frames (which start at column 0), and the trailing "(Filename: ...)" footer
        # that Unity appends after a blank separator.
        while i < len(raw_lines):
            next_line = raw_lines[i]
            next_stripped = next_line.strip()
            if not next_stripped:
                # Blank line: peek ahead to see what follows
                j = i + 1
                while j < len(raw_lines) and not raw_lines[j].strip():
                    j += 1
                if j >= len(raw_lines):
                    # Trailing blank - stop (don't include trailing blank in entry)
                    break
                next_non_blank = raw_lines[j]
                if next_non_blank[0].isspace():
                    # Blank followed by indented = still part of this entry
                    i += 1
                    continue
                if next_non_blank.strip().startswith("(Filename:"):
                    # Unity log footer: consume blank(s) + footer line as part of entry
                    i = j + 1
                    continue
                # Blank followed by a new log entry
                break
            elif next_line[0].isspace():
                # Indented = continuation of this entry
                i += 1
                continue
            else:
                # Non-indented non-blank = Unity stack frame continuation
                i += 1
                continue
        entry_end = i - 1
        # Level is computed from the finalized entry span so the Debug:Log* frame
        # (often below the header, e.g. under JS/native frames) is in scope, while
        # the scan stays bounded to this entry's own lines.
        level = _runtime_entry_level(header_line, raw_lines[entry_start:entry_end + 1])
        add_brief(level, entry_start, entry_end)

    flush_unknown()
    return briefs


def parse_log_briefs(log_path, start_offset, end_offset):
    """Parse Unity Editor log entries in the byte range [start_offset, end_offset).

    Args:
        log_path: Path to the log file (str or Path).
        start_offset: Starting byte offset (inclusive).
        end_offset: Ending byte offset (exclusive).

    Returns:
        List of brief dicts, each with keys:
            index (1-based int), level (str), line_count (int),
            start_offset (int), end_offset (int), text (str or None)
    """
    if log_path is None:
        return []
    if start_offset is None or end_offset is None:
        return []
    if start_offset >= end_offset:
        return []

    path = Path(log_path)
    if not path.exists():
        return []

    try:
        with path.open("rb") as handle:
            handle.seek(start_offset)
            raw_bytes = handle.read(end_offset - start_offset)
    except OSError:
        return []

    return _parse_chunk(raw_bytes, start_offset)


def full_text_for_brief(log_path, brief):
    """Decode the complete raw byte span assigned to one brief as UTF-8 text.

    Reads the exact `[start_offset, end_offset)` span independently of any earlier
    parse so full-text retrieval stays byte-accurate even for spans that straddle a
    chunk boundary used elsewhere. Malformed byte sequences are replaced, matching
    the parser's existing decode tolerance.
    """
    path = Path(log_path)
    if not path.exists():
        return None
    start_offset = brief.get("start_offset")
    end_offset = brief.get("end_offset")
    if start_offset is None or end_offset is None or start_offset >= end_offset:
        return None
    try:
        with path.open("rb") as handle:
            handle.seek(start_offset)
            raw_bytes = handle.read(end_offset - start_offset)
    except OSError:
        return None
    return raw_bytes.decode("utf-8", errors="replace")


def build_brief_sequence(briefs):
    """Build a compact brief sequence string from a list of brief dicts.

    Each run uses the existing brief symbol. Single-entry runs stay as the bare
    symbol; repeated runs append a decimal count to that symbol.

    Args:
        briefs: List of brief dicts as returned by parse_log_briefs.

    Returns:
        String like "WI32E2I".
    """
    if not briefs:
        return ""

    parts = []
    run_char = None
    run_count = 0

    def flush_run():
        if run_char is None:
            return
        if run_count == 1:
            parts.append(run_char)
        else:
            parts.append(f"{run_char}{run_count}")

    for brief in briefs:
        brief_char = _BRIEF_SEQUENCE_CHARS.get(brief.get("level", ""), "?")
        if brief_char == run_char:
            run_count += 1
            continue
        flush_run()
        run_char = brief_char
        run_count = 1

    flush_run()
    return "".join(parts)


def filter_briefs(briefs, levels=None, include_indices=None):
    """Filter briefs by level and/or 1-based index.

    When both filters are supplied the result is their union (no duplicates).
    When neither is supplied all briefs are returned.

    Args:
        briefs: List of brief dicts.
        levels: Iterable of level strings to include, or None.
        include_indices: Iterable of 1-based int indices to include, or None.

    Returns:
        Filtered list of brief dicts in original order.
    """
    if not levels and not include_indices:
        return list(briefs)

    level_set = set(levels) if levels else set()
    index_set = set(include_indices) if include_indices else set()

    result = []
    seen_indices = set()
    for brief in briefs:
        idx = brief.get("index")
        level = brief.get("level")
        matched = (level in level_set) or (idx in index_set)
        if matched and idx not in seen_indices:
            result.append(brief)
            seen_indices.add(idx)
    return result
