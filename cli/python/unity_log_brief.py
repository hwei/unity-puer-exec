#!/usr/bin/env python3
"""Log brief parser for Unity Editor log files.

Parses a byte range of the Unity Editor log into structured brief entries.
Briefs are compact summaries of log entries with level (info/warning/error/unknown),
line count, byte offsets, and a short text preview.
"""
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


def _runtime_entry_level(header_line):
    stripped = header_line.lstrip()
    if stripped.startswith("[Error]") or stripped.startswith("[Exception]"):
        return LEVEL_ERROR
    if stripped.startswith("[Warning]"):
        return LEVEL_WARNING
    return LEVEL_INFO


def _parse_chunk(chunk, base_offset):
    """Parse a decoded text chunk into a list of brief dicts.

    Args:
        chunk: Decoded text content of the log range.
        base_offset: Byte offset of the first character in chunk.

    Returns:
        List of brief dicts with keys:
            index, level, line_count, start_offset, end_offset, text
    """
    # Split into lines, tracking byte positions. We use len(line.encode("utf-8", errors="replace"))
    # as a proxy for byte length. The offsets are approximate for non-ASCII content but
    # are consistent with how read_editor_log_size works (st_size is bytes).
    raw_lines = chunk.split("\n")
    # Drop trailing empty element produced by split on newline-terminated content;
    # without this, the empty string is mis-classified as an unknown brief and
    # breaks brief_sequence prefix consistency across growing log ranges.
    if raw_lines and raw_lines[-1] == "":
        raw_lines.pop()
    # Compute byte offset for each line start. We use encoded length + 1 for "\n".
    line_byte_starts = []
    current = base_offset
    for line in raw_lines:
        line_byte_starts.append(current)
        current += len(line.encode("utf-8", errors="replace")) + 1  # +1 for \n

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
        brief_end = line_byte_starts[end_line_idx] + len(raw_lines[end_line_idx].encode("utf-8", errors="replace")) + 1
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
        brief_end = line_byte_starts[line_idx_end] + len(raw_lines[line_idx_end].encode("utf-8", errors="replace")) + 1
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

        # Outside compiler section: runtime traceback-based grouping
        # An entry starts with a non-blank, non-indented line.
        # It continues with subsequent lines (blank or indented) until we hit:
        #   a blank line followed by a non-indented non-blank line (new entry starts)
        #   or end of input.
        # Unknown: lines that don't fit this pattern.

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
        level = _runtime_entry_level(line)
        i += 1
        # Consume continuation lines (indented or blank-then-indented)
        while i < len(raw_lines):
            next_line = raw_lines[i]
            next_stripped = next_line.strip()
            if not next_stripped:
                # Blank line: peek ahead to see if next non-blank is indented
                j = i + 1
                while j < len(raw_lines) and not raw_lines[j].strip():
                    j += 1
                if j < len(raw_lines) and raw_lines[j] and not raw_lines[j][0].isspace():
                    # Next entry starts - stop here
                    break
                elif j >= len(raw_lines):
                    # Trailing blank - stop (don't include trailing blank in entry)
                    break
                else:
                    # Blank followed by indented = still part of this entry
                    i += 1
                    continue
            elif next_line[0].isspace():
                # Indented = continuation of this entry
                i += 1
                continue
            else:
                # Non-indented non-blank = new entry
                break
        entry_end = i - 1
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

    chunk = raw_bytes.decode("utf-8", errors="replace")
    return _parse_chunk(chunk, start_offset)


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
