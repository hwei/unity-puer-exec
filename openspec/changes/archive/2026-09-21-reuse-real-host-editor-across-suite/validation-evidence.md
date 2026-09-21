# Real-host validation evidence — one Editor per suite

Host: `c3-client-tree2/Project`, Unity 2022.3.62f2, zh-CN Editor.
Wiring: `tools/prepare_validation_host.py` reported `embedded_package_shadowing: false`.
Command: `UNITY_PUER_EXEC_RUN_REAL_HOST_TESTS=1 python -m unittest tests.test_real_host_integration`,
run through a timed runner that records each case's wall-clock (setUp + body + tearDown).

## Premise: the per-case relaunch dominated the suite

Recorded on the per-case-relaunch harness (before any change), 35 cases, 3114.5s:

```
per case:
  _ensure_clean_test_boundary(project)   stop the host        ~1s
  prepare_validation_host.main(...)      wire the manifest    <1s
  cleanup_validation_temp_assets(...)    reset fs state       <1s
  _warm_up_project_exec(...)             launch + import      ~75-90s   <-- dominant
  <assertions>                                                 ~2-10s
```

34 of 35 cases paid a full Editor launch; the launch was ~2.8ks of the 3.1ks total.
Identical outcome counts: 1 FAIL, 5 SKIP, 29 PASS.

## After: one Editor per class, per-case reset

The same 35 cases on the shared-host harness (one Editor per class, per-case state
reset, pristine-process opt-out):

| Run | Total | Outcome |
|---|---|---|
| Baseline (per-case relaunch) | 3114.5s | 1 FAIL, 5 SKIP, 29 PASS |
| Shared host (after) | **1336.7s** | 1 FAIL, 3 SKIP, 31 PASS (+1 intermittent flake, below) |

**−57% wall-clock, and the cost no longer scales with the case count.** Adding a case
now costs a ~2-20s reset instead of a ~80s launch. The 35-case average drops from ~89s
to ~38s.

Representative per-case deltas (baseline → after):

| Case | Baseline | After |
|---|---|---|
| `test_exec_checkpoint_observation_chain` | 88.2s | 15.7s |
| `test_exec_globals_are_visible_across_requests` | 85.3s | 12.6s |
| `test_cli_launched_host_is_observed_through_a_project_private_log` | 88.7s | 6.2s |
| `test_resolve_blocker_cancels_modified_scene_prompt` | 84.1s | 14.4s |
| `test_control_port_rolls_over_when_preferred_port_occupied` | 86.5s (SKIP) | 64.9s (PASS) |
| `test_exec_discovers_rolled_over_control_port` | 80.8s (SKIP) | 71.0s (PASS) |
| `test_cold_launch_retries_on_transient_failure` | 79.0s | 92.1s |

In this run port 55231 was free, so the two rollover cases **ran for real** on the
shared harness and passed — the first real exercise of the `running` opt-out's
perturb-then-adopt-restore path. Cases still near baseline cost are the ones that force
a recompile or recover from a deliberate compile error (`test_compile_error_safe_mode`
~85s, `test_unknown_modal_dialog` ~106s); they paid that cost as launch import before.

## Failure analysis

- `test_base_url_automatic_refresh_and_wait_for_compile_against_real_host` **fails in
  the baseline too** (`exec` returns `status: missing`, exit 13, "no recoverable record
  exists for request_id" after the probe's automatic refresh domain-reloads). Pre-existing,
  unrelated to this change. It is the first case in the class and the most
  launch/recovery-timing-sensitive.
- `test_batch_mode_process_follows_uniform_activation_rule…` **skips** because unrelated
  Unity processes hold the project lock (this machine has several Unity projects open for
  other work). Same skip in the baseline.
- `test_safe_mode_dialog_reports_buttons…` and `test_script_updater_consent_dialog_recovery…`
  skip because those dialogs cannot be produced on this host/Unity version. Same skips in
  the baseline.
- `test_exec_rejects_legacy_fragment_script` **intermittently fails** with a CLI response
  JSON parse error (`Expecting value: line 1 column 1 (char 0)`) — the CLI subprocess
  returned an empty body. It passed in the baseline and in other runs of the modified
  harness. This is a CLI/transport flake, not shared-host state.
- `test_cold_launch_retries_on_transient_failure…` **intermittently fails** on a
  launch-recovery flake: the CLI's `wait-for-exec` reports `running` for the full 240s
  budget with `no endpoint matched the target project yet` even though the Editor logs
  `Ready on port 55234`. Same launch-recovery family as the pre-existing first-case
  failure; it involves no shared-host state (the case owns a stopped host). It passed in
  the other runs of the modified harness.

Across four runs of the modified harness the failure set was never the same twice, while
the pre-existing `test_base_url_automatic_refresh` failure was constant — consistent with
a machine shared with several other Unity Editors, not with a systematic reuse defect.

## Cases that needed their own boundary

Four cases are named in `RealHostIntegrationTests.OWN_HOST_BOUNDARY_TESTS`; they are the
only ones that did not ride the shared Editor:

| Case | Boundary | Why |
|---|---|---|
| `test_batch_mode_process_follows_uniform_activation_rule…` | `running` → stops lazily | one-shot `Unity.exe -batchMode` needs the exclusive project lock |
| `test_control_port_rolls_over_when_preferred_port_occupied…` | `running` | stages an occupy-then-rebind reload window |
| `test_exec_discovers_rolled_over_control_port…` | `running` | stages the same rollover, asserts range-aware discovery |
| `test_cold_launch_retries_on_transient_failure…` | `stop` | asserts the cold-launch retry boundary itself |

## Findings that changed the implementation

Two behaviours only appeared once the Editor was reused, and both are handled in the
per-case reset (documented in
`openspec/specs/validation-host-integration/how-to-run.md`):

1. **A file deletion is not a compile-triggering change.** A compile-error case deletes
   its broken source on the way out, but the tracker never sees the deletion, so a reused
   Editor stays stuck on the stale error and every subsequent exec is refused by the
   compile gate. The reset now touches a repository-owned probe to force the recompile and
   waits it out.
2. **A reload can rebind the control port.** The reset re-resolves the endpoint on every
   attempt rather than holding a `base_url` captured before a reload.

A third: a modal dialog a case leaves up (the save-scene cases only report it) survives a
reused process where a relaunch dropped it, so the reset resolves a residual blocker with
an explicit cancel-like click.
