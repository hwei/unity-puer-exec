## Why

After executing a Unity operation, agents have no CLI-native way to see what log activity occurred during that operation. Diagnosing C# compile errors or unexpected runtime warnings requires falling back to direct `Editor.log` inspection, which takes agents outside the formal CLI surface. This is the root cause behind the repeated `Editor.log` fallback observed in Prompt B validation runs archived under `improve-wait-for-log-pattern-stall-guidance`.

## What Changes

- `exec` and `wait-for-exec` responses automatically include `log_range` (start and end offset of the observation window) and `brief_sequence` (a compact level string such as `"IIW?EI"` representing log activity during the operation).
- New command `get-log-briefs` returns structured brief entries for a given offset range, with optional filtering by level and index.
- **BREAKING**: `log_offset` (previously opt-in via `--include-log-offset`) is replaced by the automatic `log_range` field. The `--include-log-offset` flag is removed.
- Log entries are parsed into semantically typed briefs using section-aware rules (C# compiler output, runtime Unity log, fallback traceback); unrecognized entries are grouped and represented as `"unknown"` briefs.

## Capabilities

### New Capabilities
- `log-brief`: Defines the log-brief data shape, the `get-log-briefs` command contract, and the `log_range` + `brief_sequence` fields on exec and wait-for-exec responses.

### Modified Capabilities
- `formal-cli-contract`: `log_offset` and `--include-log-offset` are removed; `log_range` and `brief_sequence` are added to exec and wait-for-exec responses; `get-log-briefs` is added to the flat command tree.

## Impact

- `exec` and `wait-for-exec` response schema gains `log_range` and `brief_sequence`; callers relying on `log_offset` must migrate to `log_range.start`.
- New `get-log-briefs` command added to the CLI.
- If validation confirms that agents no longer need to fall back to `Editor.log` for compile and operation diagnostics, `improve-wait-for-log-pattern-stall-guidance` can be archived as superseded by this change.
