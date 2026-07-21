## 1. Fix component-detection example and summary text

- [ ] 1.1 In `cli/python/help_surface.py`, edit the `component-detection` example script body so `SceneManager.GetActiveScene()` is called on direct `CS.UnityEngine.SceneManagement.SceneManager` access instead of `puer.$typeof(CS.UnityEngine.SceneManagement.SceneManager)`; leave the `puer.$typeof(CS.UnityEngine.MeshFilter)` argument to `TryGetComponent` unchanged (it is a correct `System.Type` parameter use).
- [ ] 1.2 Update the `component-detection` entry's `goal`/`notice` text in `help_surface.py` so it explains the static-access-vs-`System.Type`-parameter distinction instead of implying `puer.$typeof(CS.UnityEngine.X)` is the general pattern for reaching Unity types.
- [ ] 1.3 Fix `help_surface.py:89` (`TOP_LEVEL_WORKFLOWS["component-detection"]`) to read `puer.$typeof + puer.$ref + TryGetComponent + get_Item` instead of the bare `$typeof + $ref` form.
- [ ] 1.4 Update the existing render-only tests in `tests/test_unity_session_cli.py` that assert on the `component-detection` example text so they match the corrected script body and notice text.

## 2. Add real-host execution coverage for the component-detection example

- [ ] 2.1 In `tests/test_real_host_integration.py`, add `test_component_detection_example_executes_against_real_host` that imports the script body from `help_surface.COMMAND_HELP["component-detection"]["steps"][0]["script_body"]` (joined the same way the CLI would accept it via `--file`), executes it through `exec` against the real host, and asserts the response succeeds with a `result` containing an integer `rootCount` and a `results` array.
- [ ] 2.2 Run the new test with `UNITY_PUER_EXEC_RUN_REAL_HOST_TESTS=1 python -m unittest tests.test_real_host_integration.RealHostIntegrationTests.test_component_detection_example_executes_against_real_host` against the prepared validation host and confirm it fails against the pre-fix example (temporarily verify, e.g. by checking out the pre-fix script body) and passes against the corrected example.

## 3. Introduce --indexes with --include as a compatibility alias

- [ ] 3.1 In `cli/python/unity_puer_exec_surface.py`, add `--indexes` to the `get-log-briefs` subparser (`dest="indexes_str"` or shared dest with `--include`) alongside the existing `--include`, keeping both populate-able.
- [ ] 3.2 In `cli/python/unity_puer_exec_runtime.py::run_get_log_briefs`, update the index-parsing logic to accept either `args.indexes_str` or `args.include_str`, raise a usage error naming `--indexes` and describing the format ("comma-separated 1-based brief indices, e.g. `--indexes 3,5`, corresponding to `brief_sequence` positions") on invalid syntax, and raise a distinct usage error if both flags are supplied with differing values.
- [ ] 3.3 Update the `--full-text` requires-indices check (currently `full_text_requires_include`) to reference `--indexes` in its message while keeping the existing status code (or introduce an equivalent code name if the status code itself should be renamed — confirm against `runtime-guidance`'s `GUIDANCE_MATRIX` entries for `("get-log-briefs", "full_text_requires_include")` before renaming the status code, since that is a public contract value).
- [ ] 3.4 Update `cli/python/help_surface.py` argument/filter-rule text for `get-log-briefs` (`--include 1,3,5` bullet, Filter Rules) to document `--indexes` as primary with `--include` noted as an alias.
- [ ] 3.5 Add/update tests in `tests/test_unity_session_cli.py` covering: `--indexes` alone, `--include` alone (identical result), both supplied with matching values (allowed), both supplied with conflicting values (usage error), and the updated `--full-text` error message wording.

## 4. Add the ReferenceError situation hint

- [ ] 4.1 Determine the exact `ReferenceError` message text PuerTS/the embedded JS engine produces for a bare undefined `$typeof` / `$ref` reference by running a small real-host probe script (e.g., `export default function(ctx) { return $typeof; }`) and capturing the resulting `error` field.
- [ ] 4.2 In `cli/python/unity_puer_exec_runtime.py`, add a helper (e.g. `_maybe_hint_puer_prefix(payload)`) that, given a failed `exec`/`wait-for-exec` payload, checks `payload.get("error")` against a narrow pattern matching that exact bare `$typeof`/`$ref` `ReferenceError` shape, and if matched, appends a `puer.$typeof`/`puer.$ref` hint sentence to `payload["situation"]` (creating it if `_attach_guidance` did not already set one for this status).
- [ ] 4.3 Call this helper from the failure paths in `run_exec` and `run_wait_for_exec` after `_attach_guidance` runs, so it augments rather than replaces the existing `("exec"/"wait-for-exec", "failed")` situation text.
- [ ] 4.4 Add unit tests (mocked, in `tests/test_unity_session_cli.py`) covering: bare `$typeof` ReferenceError produces the hint, bare `$ref` ReferenceError produces the hint, an unrelated `TypeError` or an application error message that merely mentions `$typeof` in prose does NOT produce the hint, and `next_steps` remains unchanged when the hint is added.
- [ ] 4.5 Add a real-host test case (or extend an existing exec-failure real-host test) in `tests/test_real_host_integration.py` that runs the probe script from 4.1 through `exec` and asserts the hint appears in `situation`.

## 5. Spec and closeout

- [ ] 5.1 Confirm the delta specs in `openspec/changes/tighten-agent-cli-guidance/specs/` match the implemented behavior exactly (especially the confirmed `ReferenceError` message shape from 4.1 — update the scenario wording if the real message text differs from what was assumed during proposal/design).
- [ ] 5.2 Run the default mocked test suite (`python -m unittest tests.test_unity_session_cli` at minimum, full default suite per `openspec/specs/validation-host-integration/how-to-run.md` if time allows) and confirm it passes.
- [ ] 5.3 Run the new and existing real-host tests per `openspec/specs/validation-host-integration/how-to-run.md` and record pass/skip/fail results.
- [ ] 5.4 Produce the apply closeout finding summary per `AGENTS.md` ("Apply closeout") before recommending commit/archive.
