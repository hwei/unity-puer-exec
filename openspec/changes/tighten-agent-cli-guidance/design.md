## Context

This change was scoped from an external agent-feedback review (`fable5_feedback_session7ae0557b.md`) that identified five concrete inaccuracies/gaps in the agent-facing `unity-puer-exec` CLI help and error surface, all clustered in `cli/python/help_surface.py`, `cli/python/unity_puer_exec_surface.py`, and `cli/python/unity_puer_exec_runtime.py`:

1. `help_surface.py:89` top-level workflow summary says bare `$typeof + $ref`; the rest of the help surface says `puer.$typeof` / `puer.$ref`.
2. The `component-detection` example (`help_surface.py:676`) wraps a static member access, `SceneManager.GetActiveScene()`, in `puer.$typeof(...)`. Per PuerTS's own JS-to-C# documentation, static access should use `CS.UnityEngine.SceneManagement.SceneManager` directly; `puer.$typeof(...)` is only needed where a `System.Type` value is required as a parameter, which the same example already does correctly for `TryGetComponent(puer.$typeof(CS.UnityEngine.MeshFilter), mf)`.
3. `ReferenceError: $typeof is not defined` / `$ref is not defined` (the runtime error a script author gets from forgetting the `puer.` prefix) has no corrective hint anywhere in the guidance surface.
4. `get-log-briefs --include` (`unity_puer_exec_surface.py:121`, error at `unity_puer_exec_runtime.py:1503`) uses a generic flag name and a generic error message ("--include must be comma-separated integers") with no mention of 1-based indexing or `brief_sequence` correspondence.
5. All existing `component-detection` tests (`tests/test_unity_session_cli.py`) assert only that help text renders; none execute the example script, which is how issue 2 went unnoticed.

Items 1, 2, and (extended) 5 anchor to the existing `formal-cli-contract` requirement "Help includes a component-detection example". Item 4 anchors to the existing `log-brief` requirement that defines `get-log-briefs --include`. Item 3 has no existing anchor and is a new additive requirement under `runtime-guidance`.

## Goals / Non-Goals

**Goals:**
- Make the `component-detection` example and its surrounding text accurate against real PuerTS static-vs-`System.Type`-parameter semantics.
- Give `get-log-briefs` callers a self-correcting error path for the indices flag.
- Give script authors a self-correcting hint when they forget the `puer.` prefix.
- Close the test gap that let an incorrect example ship silently: the component-detection example must be executed against a real host, not merely rendered.

**Non-Goals:**
- Not renaming or restructuring the guidance-matrix architecture (`(command, status)` keying) described in `runtime-guidance`.
- Not adding general-purpose error-message pattern matching across all commands; the `ReferenceError` hint is a single narrowly-scoped addition, not a new matching framework.
- Not auditing other help examples for PuerTS accuracy beyond `component-detection`; if the same static-vs-`$typeof` mistake exists elsewhere, that is follow-up work, not this change.
- Not changing `--include`'s existing behavior or removing it; it remains a fully functional alias indefinitely (no deprecation timeline is being introduced here).

## Decisions

### 1. Fix the example in place; do not add a second "corrected" example

The existing `component-detection` example is edited directly (`SceneManager.GetActiveScene()` called on the bare `CS.UnityEngine.SceneManagement.SceneManager` class; `puer.$typeof(...)` retained only around the `TryGetComponent` type argument). No second example is introduced. Rationale: the requirement text in `formal-cli-contract` names this as *the* component-detection example; a parallel "corrected" example would create the same ambiguity this change is trying to remove.

### 2. `--indexes` is primary, `--include` is a permanent compatibility alias

Both flags populate the same destination (`include_indices` semantics unchanged); `--indexes` becomes the name shown in help/error text, `--include` continues to work identically with no deprecation warning. Considered making `--include` emit a soft deprecation notice, but rejected — the proposal and existing `log-brief` spec give no indication this is being deprecated, only that a clearer primary name is being introduced. Adding deprecation messaging would be scope creep not requested by the source feedback.

If both `--indexes` and `--include` are supplied in the same invocation with different values, this is a caller error and should fail loudly (`usage_error`) rather than silently preferring one — this needs an explicit scenario in the `log-brief` delta spec.

### 3. `ReferenceError` hint is a `situation`-only addition keyed on `error` text, not a `next_steps` change

`runtime-guidance` already establishes: "the CLI does not inspect script-authored `result` fields to filter or reorder [`next_steps`] candidates" (scoped explicitly to `next_steps` and to the `result` field). The new hint:
- Only ever augments `situation` text for `("exec", "failed")` / `("wait-for-exec", "failed")`.
- Only ever reads the `error` field (the thrown exception's message), never `result`.
- Never changes which `next_steps` entries are offered.

This keeps the addition consistent with the letter of the existing invariant. The match itself SHALL be a narrow regex anchored to the exact PuerTS-generated `ReferenceError` shape (e.g. `^\$typeof is not defined$` / `^\$ref is not defined$`, or the exact V8/PuerTS message format actually observed — confirm exact wording during implementation against a real host, since JS engines vary in exact phrasing), not a loose substring match, so it does not accidentally fire on unrelated user-authored errors that happen to mention `$typeof` in prose.

### 4. Real-host test sources the script body from `help_surface.py` directly, not a copy

The new test in `tests/test_real_host_integration.py` (pattern: `test_..._against_real_host`, per existing convention) imports `help_surface.COMMAND_HELP["component-detection"]["steps"][0]["script_body"]` and executes that exact script against the real host, rather than hand-copying the script into the test file. Rationale: a hand-copied script can drift from the documented example (this is arguably how the original bug shipped unnoticed alongside 100%-passing render-only tests); sourcing it directly guarantees the tested code and the documented code are byte-identical. This test is gated the same way as all other real-host tests (`UNITY_PUER_EXEC_RUN_REAL_HOST_TESTS=1`, skips silently without a prepared host).

### 5. Capability placement: extend `formal-cli-contract`'s existing requirement rather than adding a new validation capability

The real-host execution expectation for the component-detection example is added as a clause on the existing "Help includes a component-detection example" requirement (`formal-cli-contract`), not as a new capability or an addition to `agent-cli-discoverability-validation` (which governs a different thing: full help-only agent trial protocol, not per-example unit-level execution coverage).

## Risks / Trade-offs

- **[Risk]** The exact `ReferenceError` message text PuerTS/V8 produces for a bare `$typeof` reference may not be known until tested against a real host, so the regex in the delta spec's scenario may need adjustment during implementation. **Mitigation:** treat the exact message format as an implementation detail confirmed during `tasks.md` execution against the real host; the spec scenario should describe the semantic match (bare `$typeof`/`$ref` ReferenceError) rather than hard-coding an unverified literal string.
- **[Risk]** Introducing `--indexes` as the "primary" name while keeping `--include` working forever adds a small permanent surface-area cost (two names, one behavior, no sunset). **Mitigation:** accepted — the source feedback explicitly asked for `--include` to remain as a compatibility alias, not to be deprecated.
- **[Risk]** The new real-host test adds to real-host suite runtime and requires a scene with at least one root GameObject to produce a meaningful (non-trivially-empty) assertion. **Mitigation:** assert on structural shape (`rootCount` is a non-negative integer, `results` is an array, no thrown error) rather than requiring a specific scene layout, so the test is robust to whatever scene the validation host happens to have open.

## Migration Plan

No data or API migration. This is a documentation-accuracy and error-message fix plus one additive flag alias and one additive situation-text hint; all existing behaviors (`--include`, existing `next_steps`, existing response shapes) are preserved unchanged. Rollback is a plain revert of the affected files and spec deltas.
