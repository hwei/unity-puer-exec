## Why

The published agent-facing CLI help surface currently teaches an incorrect PuerTS usage pattern in its `component-detection` example (static Unity API access is wrapped in `puer.$typeof(...)` when that wrapper is only needed for `System.Type` parameter positions), carries an inconsistent shorthand in a top-level workflow summary, returns an unhelpfully generic error for a common `get-log-briefs` indices mistake, and gives no "did you mean" hint when a script author forgets the `puer.` prefix on `$typeof`/`$ref`. None of this was caught by the existing test suite because component-example tests only assert that help text renders, not that the example script actually executes against a real host. Together these are small but compounding sources of agent friction on the CLI surface that is supposed to be self-sufficient without repository-only context.

## What Changes

- Fix the `component-detection` help example: replace the incorrect `puer.$typeof(CS.UnityEngine.SceneManagement.SceneManager)`-wrapped static member access with direct `CS.UnityEngine.SceneManagement.SceneManager.GetActiveScene()`; keep `puer.$typeof(...)` only where a `System.Type` parameter is actually required (e.g., the existing `TryGetComponent` call in the same example already does this correctly).
- Fix the `component-detection` top-level workflow summary (`help_surface.py:89`) to read `puer.$typeof + puer.$ref` instead of the bare `$typeof + $ref`, consistent with the rest of the help surface's notice text.
- Add a real-host execution test for the `component-detection` example script (copy the documented script body verbatim and run it against the validation host) so a future regression of this kind is caught by test execution, not only by text-rendering assertions.
- Introduce `--indexes` as the primary flag name on `get-log-briefs` for selecting 1-based brief indices; retain `--include` as a backward-compatible alias with identical behavior. Update the associated usage error to name `--indexes`, spell out the accepted format ("comma-separated 1-based brief indices, e.g. `--indexes 3,5`"), and note that these positions correspond to `brief_sequence` positions.
- Add a narrowly-scoped guidance hint: when `exec` or `wait-for-exec` fails with a `ReferenceError` whose message indicates a bare `$typeof` or `$ref` reference (missing the `puer.` prefix), the response `situation` text SHALL include a "did you mean `puer.$typeof` / `puer.$ref`" hint. This inspects only the `error` field, only to augment `situation` text for the `failed` status — it does not touch `next_steps` candidate selection or inspect `result`, so it stays consistent with the existing constraint that `next_steps` candidates are determined by command and status alone.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `formal-cli-contract`: the "Help includes a component-detection example" requirement is corrected so the example demonstrates the static-access-vs-`System.Type`-parameter distinction accurately, and extended so the example script is verified to execute successfully against a real host as part of its acceptance evidence (not just that help renders it).
- `log-brief`: the `get-log-briefs` command requirement is updated to add `--indexes` as the primary 1-based index-selection flag, `--include` as a compatibility alias, and clearer usage-error text.
- `runtime-guidance`: a new additive requirement covers a targeted `situation` hint for `exec`/`wait-for-exec` `failed` responses whose `error` text matches the bare `$typeof`/`$ref` `ReferenceError` pattern.

## Impact

- `cli/python/help_surface.py`: component-detection example script body, top-level workflow summary text, notice text.
- `cli/python/unity_puer_exec_surface.py`: `--indexes` argparse addition, `--include` retained as alias.
- `cli/python/unity_puer_exec_runtime.py`: `get-log-briefs` error text; `exec`/`wait-for-exec` situation construction for the new ReferenceError hint.
- `tests/test_unity_session_cli.py`: new real-host execution test for the component-detection example; updated/added tests for `--indexes`/`--include` and the ReferenceError hint.
- `openspec/specs/formal-cli-contract/spec.md`, `openspec/specs/log-brief/spec.md`, `openspec/specs/runtime-guidance/spec.md`: delta specs for the above.
