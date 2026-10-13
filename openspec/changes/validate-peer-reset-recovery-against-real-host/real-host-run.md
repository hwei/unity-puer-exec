# Real-host run transcript — validate-peer-reset-recovery-against-real-host

Command:
```
UNITY_PUER_EXEC_RUN_REAL_HOST_TESTS=1 python -m unittest tests.test_real_host_integration -v
```

Result: **Ran 42 tests — OK (skipped=3) — 2126.888s**

## Prerequisites (task 1.1), observed values

| Prerequisite | Observed |
|---|---|
| `UNITY_PROJECT_PATH` | `F:\C3\unity-puer-exec-workspace\c3-client-tree2\Project` (from process env, overrides `.env`) |
| Host prepared | `prepare_validation_host.py --dry-run` → `"status": "unchanged"` |
| Dependency wiring | `file:../../../unity-puer-exec/packages/com.txcombo.unity-puer-exec` |
| `testables` | `["com.txcombo.unity-puer-exec"]` |
| `embedded_package_shadowing` | **`false`** — no shadowing copy under `Project/Packages/` |
| Editor | `E:\Program Files\Unity\Hub\Editor\2022.3.62f2\Editor\Unity.exe` |
| Preflight compile | `"status": "passed"`, `exit_code: 0`, no `error CS` diagnostics |
| Host lockfile | `Temp\UnityLockfile` absent at start |

## Play-mode cases (task 1.2 / 1.3)

All six `PlayModeCompileBlockRealHostTests` cases **ran and passed**:

| Case | Result |
|---|---|
| `test_play_settles_a_pending_change_then_reaches_playing` | **ok** — the case that originally produced `[WinError 10054]` |
| `test_play_mode_compile_block_then_settles_after_play_exit` | ok |
| `test_deferred_play_exit_compile_settles_from_a_generation_baseline` | ok |
| `test_play_pause_play_resumes_against_real_host` | ok |
| `test_play_aborts_on_a_compile_error_without_entering_play_mode` | ok |
| `test_stop_settles_the_deferred_compile_against_real_host` | ok |

`test_play_settles_a_pending_change_then_reaches_playing` reached `playing` with exit code 0
(the suite reports a bare `ok`, which under `unittest` means no assertion fired — that
assertion is the one that failed originally). No `status: "failed"` / exit 1 payload was
observed on the play path.

## Skips (task 1.1 — recorded as skips, not passes)

1. `test_batch_mode_process_follows_uniform_activation_rule_against_real_host` —
   `'host project appears open in an interactive Editor (unity pids=[112100, 61972]); batch-mode launch needs the exclusive project lock'`
   Boundary record: `{"mode": "running", "stopped": false, "perturbed": false, "boundary": "batch_mode_one_shot_processes", "interactive_pids": [112100, 61972]}`
2. `test_safe_mode_dialog_reports_buttons_and_keeps_cancel_against_real_host` —
   `'no Safe Mode dialog is currently showing on the host'`
3. `test_script_updater_consent_dialog_recovery_against_real_host` —
   ScriptUpdater consent dialog could not be triggered on Unity 2022.3.62f2 (incremental
   compilation, no interactive source rewrite prompt).

None of the three is related to the peer-reset boundary. All three are pre-existing
conditional skips documented in `openspec/specs/validation-host-integration/how-to-run.md`.

## Task 2.1 — `OSError` breadth check on a live endpoint

**No unattributed `not_available` was observed.** Every boundary record in the run resolved to
a specific attributed cause:

- `cold_launch_retry`: host reached `{"status": "completed"}` after `attempt_count: 2`, boundary
  result `{"ok": true, "status": "stopped"}`
- `preferred_port_rollover`: `preferred_port: 55231` held by `foreign_endpoint`, host rolled to
  `55232`, `mid_reload_rebind: "not_staged"` (an attributed disposition, not a mask)
- `preferred_port_rollover_discovery`: `discovery_exit_code: 0`

The broadened `OSError` catch did not convert any live condition into an unattributed
`not_available` in this run. This is a negative observation over one run, not a proof.

## Task 2.2 — did a real peer reset occur?

**No.** No transport reset occurred during this 35-minute run. Therefore the payload shape for
a real reset — `status: "not_available"`, exit 12, errno text in `error`,
`transport_detail.reason` — was **not** observed live. It remains verified only against the
constructed `RemoteDisconnected` in the mocked boundary test.

## Evidence strength — read this before quoting the run

| Claim | Supported by this run? |
|---|---|
| No regression on the play path against a live Editor | **Yes** |
| The six play-mode cases, including the originating one, pass live | **Yes** |
| The broadened `OSError` catch masked nothing live, in this run | **Yes, weakly** (negative over one run) |
| A real peer reset is now classified correctly on a live endpoint | **No.** Not observed. |
| The reset recovery branch works end to end on a real socket | **No.** Mocked only. |

Per design Decision 1, this run is **"no regression observed"**, not **"the reset path is
confirmed"**. The originating failure was a single occurrence; a clean run that reproduces no
reset says little about that specific path. The fix's live confirmation is still outstanding.