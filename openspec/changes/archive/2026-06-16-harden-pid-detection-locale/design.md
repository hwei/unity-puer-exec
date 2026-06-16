## Context

`is_pid_running(pid)` runs:

```
tasklist /FI "PID eq <pid>" /NH /FO CSV
```

and returns `bool(output) and "No tasks are running" not in output`. The
`/FI "PID eq ..."` filter prints either a CSV row for the matching process, or a
localizable informational line when nothing matches. The current check keys off
the English form of that informational line, so on any non-English Windows the
informational line is non-empty and does not contain `"No tasks are running"`,
making the function report every PID as alive.

`list_unity_pids()` in the same file already avoids this trap: it parses the CSV
with `csv.reader`, skips the `INFO:`/no-match rows, and only counts rows whose
first column is `Unity.exe`. The fix applies the same parsing discipline to PID
lookup.

## Goals / Non-Goals

**Goals:**
- Liveness detection that does not depend on the OS display language.
- A unit test that locks locale-independence without spawning real processes.
- Zero behavior change on English hosts.

**Non-Goals:**
- No change to `taskkill`/stop flow control beyond what corrected liveness implies.
- No new cross-platform process backend (this code path is Windows `tasklist`).
- No change to `list_unity_pids` (already correct).

## Decisions

### Decision 1: Determine liveness from a parsed CSV PID row, not an English sentinel

Reuse the `csv.reader` parsing pattern from `list_unity_pids`: a PID is alive iff
the `tasklist /FI "PID eq <pid>"` CSV output contains a data row whose PID column
(index 1) equals the queried PID. The `INFO:` / localized no-match line is not a
valid CSV data row with an integer PID column, so it is naturally excluded.

- Rationale: CSV structure is locale-stable; the informational/no-match text is
  not. This mirrors the already-correct `list_unity_pids`, keeping the module
  internally consistent.
- Robustness: match on the numeric PID column rather than image name, since the
  filter is by PID and the image can be any process. Guard `int()` parsing with
  `try/except` exactly as `list_unity_pids` does.

### Decision 2: Test through the parsing seam with captured `tasklist` outputs

Add a unit test that exercises the parsing logic against representative
`tasklist /FO CSV` outputs — a real PID row, an English "no tasks" line, and a
localized (e.g. Chinese) "no tasks" line — asserting `True` only for the PID-row
case and `False` for both no-match forms.

- Approach: inject the command output (monkeypatch `subprocess.run` or factor a
  pure `_pid_is_present_in_tasklist_csv(output, pid)` helper that the test calls
  directly). A pure helper is preferred: it isolates the locale-sensitive logic
  from process spawning and keeps the test deterministic and fast.
- Alternative considered: integration test that kills a process and checks
  liveness. Rejected — slow, racy, and cannot exercise the localized-output path
  on an English CI runner.

## Risks / Trade-offs

- [A localized `tasklist` could, in theory, also localize CSV quoting] →
  Mitigation: CSV field structure and the numeric PID column are stable across
  Windows locales; only the free-text informational line is localized.
- [PID reuse: a recycled PID belonging to a non-Unity process reads as alive] →
  Accepted and pre-existing; `/FI "PID eq"` matches any process by PID, and the
  callers already treat the session PID as Unity-owned. Out of scope here.

## Migration Plan

- Pure code-and-test change; revertable by restoring the prior one-liner. No data
  or workflow migration.

## Open Questions

- None. The fix is mechanical and mirrors an existing, proven pattern in the same
  module.
