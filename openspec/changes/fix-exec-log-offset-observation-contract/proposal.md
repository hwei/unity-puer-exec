# Proposal

## Why

Real Unity host validation against `c3-client-tree2/Project` showed that the new result-marker workflow is only partially correct in practice. `exec --include-log-offset` returned `log_offset = 0` even though the Unity Editor log already contained substantial content, while `wait-for-result-marker` still succeeded by effectively scanning from the beginning of the log.

That means the formal observation contract is not yet reliable: the value returned by `exec` does not currently line up with the log source that CLI observation commands actually read. This weakens the intended `exec -> wait-for-result-marker` and `exec -> wait-for-log-pattern` workflows and leaves the low-level extraction path without real-host proof.

## What Changes

- align the `log_offset` returned by `exec --include-log-offset` with the actual log source observed by CLI log-wait commands
- verify the corrected contract in a real Unity host, not only in Python-level tests
- tighten the formal CLI contract around what `log_offset` means and how callers should rely on it
- add or update host-validation evidence for both the high-level result-marker path and the low-level extraction path
