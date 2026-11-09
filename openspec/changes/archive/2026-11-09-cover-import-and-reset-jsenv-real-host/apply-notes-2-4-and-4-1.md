# Apply notes: tasks 2.4 and 4.1

## 2.4 — no new device state, so no mocked reset case was invented

Task 2.4 is conditional: extend `tests/test_real_host_reset.py` **if** the new cases
introduce device state the mocked reset tests must know about; otherwise record that
no device state was added rather than inventing a case.

Finding: **no device state was added.** Reasons, each checkable:

- Neither new case is in `OWN_HOST_BOUNDARY_TESTS`, so neither owns a launch/stop
  boundary. Both ride the shared host exactly like the neighbouring
  `test_exec_globals_are_visible_across_requests_against_real_host`.
- Neither launches, stops, perturbs, or rebinds an Editor process, and neither
  changes the control port. They only issue `exec` requests.
- Neither enters play mode, stages a modal blocker, or writes a compile-triggering
  file. The fixture is a `.js` module in a `~`-suffixed folder, which Unity's asset
  pipeline ignores entirely, so no refresh, no compilation, and no change-signal
  state is created.
- The only on-disk state is the fixture directory plus the server's own
  per-request entry module, both under the **already-declared** validation-temp
  root `Assets/__codex_validation_temp/`. The existing per-case reset
  (`_reset_shared_host_state` → `_cleanup_temp_assets` →
  `cleanup_validation_temp_assets`) removes that whole root, so no new reset step
  is required. This is the mechanism task 2.3 asks for.
- The JsEnv reset the second case exercises is server-owned and per-request; it
  leaves no state for a later case, and `ctx.globals` is process-scoped JS state
  that the reset itself clears.

Verification run:

```
python -m unittest tests.test_real_host_reset
Ran 22 tests in 0.768s
OK
```

`tests/test_real_host_reset.py` was **not** modified, and it contains no reference
to `import_fixture`, `_exec_with_import_context`, or `ctx.globals` — confirmed by
grep. The suite that matters (`tests.test_real_host_integration`) went from 52 to
54 cases, and `RealHostIntegrationTests` from 27 to 29; the mocked default suite
still reports `Ran 877 tests ... OK`.

## 4.1 — retiring `.tmp/puerts2_e2e_probe.py`

The scratch probe written for `support-puerts-2x-jsenv` drove the real CLI in
process against each host through five steps. Each step is now covered by a
committed real-host case, so the evidence no longer depends on a gitignored
scratch file.

| Probe step | What it asserted | Replaced by |
|---|---|---|
| 1. `exec-inline` | an inline body reaches `status: completed` and `result.sum == 2`, proving a JsEnv was constructed at all on 2.2.2 | Already covered before this change by the many inline-`exec` cases in `RealHostIntegrationTests`, e.g. `test_exec_globals_are_visible_across_requests_against_real_host` and `test_exec_script_args_are_visible_against_real_host` |
| 2. `exec-import-base-url` | a relative `import` resolves through a filesystem `--import-base-url` and the imported value crosses into `result` | **`test_exec_resolves_relative_import_through_import_base_url_against_real_host`** (new, task 2.1) |
| 3. `exec-reset-jsenv-reloads-module` | after rewriting the module, `--reset-jsenv-before-exec` shows the new value rather than the cache | **`test_reset_jsenv_before_exec_clears_globals_with_an_unchanged_module_against_real_host`** (new, task 2.2) — see the strengthening note below |
| 4. `play` | `play` reaches `play_state: playing` | Already covered: `test_play_settles_a_pending_change_then_reaches_playing` asserts `play_state == "playing"`; `test_play_pause_play_resumes_against_real_host` covers `playing`/`paused`/`playing` |
| 5. `stop` | `stop` returns `play_state: edit` | Already covered: `test_stop_settles_the_deferred_compile_against_real_host` asserts `play_state == "edit"` after `play` |

### Step 3 was strengthened, not merely ported

The probe's step 3 **rewrote** the module and then asked for a reset. That form
cannot discriminate the flag: the default `--stale-module-policy auto-reset`
already resets the JsEnv when `CheckModuleStaleness()` reports a changed module,
so the probe's expectation would have been met with `--reset-jsenv-before-exec`
completely ignored. The ported case removes that ambiguity by keeping the module
**unchanged** (its bytes are compared before and after inside the case) and
discriminating on `ctx.globals` continuity plus `recovery.reason ==
"explicit_request"`, a value only the flag can produce. See
`baseline-and-discriminator.md` for the derivation.

The probe therefore leaves behind strictly more than it had: its step-3 result was
weaker evidence than the case that replaces it.

### Ordering of the deletion

`.tmp/puerts2_e2e_probe.py` is **deliberately still present** at the time of
writing. Until tasks 3.1 and 3.2 have run the two new cases against the 2.2.2 and
3.0.0 hosts and recorded the responses, the probe is the only artifact that has
ever demonstrated this behavior end to end on both PuerTS majors. Deleting it
before the replacement cases have passed would destroy evidence and leave nothing
in its place. Delete it once group 3 is recorded; this mapping is the committed
record that keeps the `support-puerts-2x-jsenv` trail resolvable after `.tmp/` is
cleaned, which is what the task actually requires.
