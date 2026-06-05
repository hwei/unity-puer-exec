## Why

Runtime log-brief level classification is effectively blind in GUI Unity (`Editor.log`): real entries carry no `[Error]`/`[Warning]`/`[Exception]` header prefix, so `_runtime_entry_level` always falls through to `info`. Measured on a real validation-host `Editor.log` (1.5 MB), the current parser produced **565 briefs, 100% `info`** — every `Debug.LogError`/`Debug.LogWarning` silently downgraded — while the `[…]` prefix the classifier keys on appeared **0 times** in the file. `brief_sequence`, the health indicator agents scan instead of reading raw logs, therefore never shows `W`/`E` for GUI runtime activity. The level signal is already present in the entry: Unity always emits a `UnityEngine.Debug:LogError|LogWarning|LogException|LogAssertion|Log` stack frame (when stack-trace logging is enabled — the same regime brief grouping already requires).

## What Changes

- **NEW: derive runtime entry level from the `UnityEngine.Debug:Log*` stack frame when the header has no level marker.** The parser scans the entry's lines for the stable Unity logging API frame and maps it: `LogError`/`LogException`/`LogAssertion` → `error`, `LogWarning` → `warning`, `Log`/`LogFormat` → `info`. The existing header-marker path keeps priority, so this only fills the gap where the header is bare. Matching is anchored to the fully-qualified `UnityEngine.Debug:` token (tolerant of `:`/`.` separator and `*Format` suffixes), so arbitrary message text containing "Error" cannot flip a level.
- **NEW (secondary): uncaught-exception header recognition.** A bare header matching an exception signature (e.g. `^<Type>Exception:`) is classified `error`, covering exceptions surfaced without a `Debug:LogException` frame.
- This **refines** the prior `improve-log-brief-stacktrace-fidelity` decision "level from header line only." That decision was correct under its premise — *that the header carries the level* — which the validation-host sample proves false for GUI logs. Level is still **not** taken from arbitrary absorbed frame text; it is taken from one specific, stable API frame only when the header is silent.
- Validated reclassification on the real log: **46 `info`→`error` and 5 `info`→`warning`**, zero spurious flips (native-noise blocks have no `Debug:` frame and stay `info`).
- The stack-trace-disabled regime is unchanged: with no frames there is no signal to read, and the existing `!stacktrace-off` sentinel already guards that case — so this introduces **no new blind spot**.
- **Test hardening** with real-log shapes (Puer/TS project: indented JS frames with `<a href>` tags above the non-indented C# `Debug:Log*` frame; `LogError`/`LogWarning` entries with bare headers).

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `log-brief`: Tighten the Runtime Unity log level-derivation rule so that, when the header line carries no log-type marker, the level is derived from the entry's `UnityEngine.Debug:Log*` stack frame (and an exception-signature header), instead of unconditionally defaulting to `info`.

## Impact

- `cli/python/unity_log_brief.py` — `_runtime_entry_level` (or the entry-finalize path) consults the entry's stack frames for the `Debug:Log*` frame and an exception-header pattern; header markers retain priority.
- `tests/test_unity_log_brief.py` — real-log-shaped cases for header-less `LogError`/`LogWarning`/exception entries and negative cases (message text containing "Error", native-noise blocks).
- `openspec/specs/log-brief/spec.md` — durable requirement delta on runtime level derivation.
- No C# change required; no payload/transport change. Standalone `get-log-briefs --range` benefits automatically since the signal is pure text within the range.
- Verification dependency: confirm the reclassification delta still holds on the validation host after the change (`evidence: host-validation`).
