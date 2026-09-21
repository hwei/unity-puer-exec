# diagnose-exec-missing-after-auto-refresh — apply session evidence (2026-09-21)

Environment: validation host `c3-client-tree2/Project` (`UNITY_PROJECT_PATH` from
repository `.env`), repository package wired via manifest
(`embedded_package_shadowing: false`, dependency
`file:../../../unity-puer-exec/packages/com.txcombo.unity-puer-exec`), host launched by
the suite with `UNITY_PUER_EXEC_UNITY_LAUNCH_ARGS=["-force-gles30"]`.

## 1. Root cause (tasks 1.1–1.5)

Owning call site: `_post_refresh_ready_timeout_seconds`
(`cli/python/unity_puer_exec_runtime.py:890`) derived the automatic-refresh settle budget
from `--wait-timeout-ms`. That option bounds one HTTP wait for an already-accepted job, not
a compile plus the domain reload it ends with. The failing real-host case passes
`WAIT_TIMEOUT_MS = 1000`, so the settle window was **1.0 s**; no compile+reload meets it, so
`wait_for_compile_cycle` returned `settle_timeout`, `_settle_after_automatic_refresh`
returned `None`, and `_run_exec_impl:1332` returned `running`/`refreshing` **without
resubmitting**.

That becomes a non-recoverable `missing` because the server returns the refreshing phase
*before* `TryAcceptExecRequest` (`UnityPuerExecServer.cs:659` vs `:684`): the job was never
accepted, so `Requests` never held the `request_id` — with or without a reload. Base-url mode
writes no client-side record (every pending-artifact read/write is guarded by
`selector == "project_path"`) and `_run_wait_for_exec_impl` sets `pending = None` for
base-url, so `wait-for-exec --base-url` is a pure server lookup that answers `missing`.

Rejected alternative — "the pending artifact is lost or invalidated by the reload" —
refuted by: (a) base-url mode writes no artifact; (b) the `log_range` in the failing payload
is CLI-injected observation metadata (`_apply_log_range_and_brief_sequence`), i.e. the
resolved Editor.log size, not an artifact field; (c) `PENDING_EXEC_RETENTION_MS` is 24 h, so
a reload cannot expire an artifact.

Reproduced locally against unchanged code, toggling only the budget:

```
wait_timeout_ms=1000    exit=10  invokes=1 status=running    phase=refreshing log_range={'start': 1690261, 'end': 1690261}
wait_timeout_ms=300000  exit=0   invokes=2 status=completed  phase=None       log_range={'start': 1690261, 'end': 1690261}
```

The `1690261` is this machine's resolved Editor.log size — the same value the real-host
failure reported, which is what made it look like a replayed offset.

Corroboration inside the same real-host class: `_exec_script` already uses
`REFRESH_WAIT_TIMEOUT_MS = 300_000` with the comment that an exec that may trigger an
automatic refresh "has to give the CLI's internal settle+resubmit loop enough budget", and
those cases pass. Only the `WAIT_TIMEOUT_MS = 1000` case failed deterministically.

## 2. Fix (tasks 2.1–2.4)

`_post_refresh_ready_timeout_seconds` now returns the compile-scale readiness budget
(`unity_session.DEFAULT_READY_TIMEOUT_SECONDS`, 180 s) — the same budget
`wait-for-compile --settle-timeout-seconds` gives the identical cycle. Both consumers
(`_settle_base_url_after_refresh`, `_ensure_project_session_ready_after_refresh`) get the
correct budget from the one site. The `missing` classification is untouched.

Reproduction: `tests/test_unity_session_cli.py::AutomaticRefreshBaseUrlTests::
test_base_url_automatic_refresh_settles_cycle_longer_than_wait_timeout`. It models the
compile cycle as a clock the health probe reads, so it exercises the settle loop's own
budget arithmetic rather than mocking the settle. It fails on the pre-fix code
(`AssertionError: 1 != 2`, one invoke, no resubmit) and passes after.

## 3. Verification (tasks 3.1–3.2)

Unit suites green, 556 tests:

```
tests.test_cleanup_validation_host_tool tests.test_cli_version tests.test_direct_exec_client
tests.test_editor_log_isolation tests.test_openspec_backlog tests.test_openspec_change_meta
tests.test_openspec_spec_hygiene tests.test_package_layout tests.test_prepare_validation_host_tool
tests.test_refresh_change_signal tests.test_unity_log_brief tests.test_unity_puer_session
tests.test_unity_session tests.test_unity_session_cli tests.test_unity_session_modules
tests.test_response_file_output tests.test_unity_modal_blockers
-> Ran 556 tests in 43.472s OK
```

The pending-artifact rules that must not regress are specifically confirmed green:
`test_wait_for_exec_expired_pending_artifact_is_cleaned_and_missing_is_returned`,
`test_logs_read_pending_exec_artifact_cleans_expired_file`,
`test_logs_read_pending_exec_artifact_cleans_malformed_file`,
`test_logs_sweep_pending_exec_artifacts_removes_only_expired_and_malformed_siblings`.

Real host, `RealHostIntegrationTests.
test_base_url_automatic_refresh_and_wait_for_compile_against_real_host`, same host and same
session, only the settle-budget line toggled:

| Budget | Result |
|---|---|
| pre-fix (`--wait-timeout-ms`) | `FAILED (failures=1)` — `AssertionError: 13 != 0 : status 'missing'`, `error 'no recoverable record exists for request_id'`, `log_range {'start': 1690261, 'end': 1690261}` (81 s) |
| post-fix | `OK` (191 s cold, 151 s re-run) |

The pre-fix failure reproduces the originally observed payload verbatim, so the previously
deterministic failure is attributable to the fix and is confirmed against a real reload
rather than a mock.

`openspec validate diagnose-exec-missing-after-auto-refresh` (default and `--strict`):
valid. Investigation showed the requirement's normative text already covers the fix, so the
delta is confirmed as-is (design Decision 3).

## 4. Apply closeout finding

**New follow-up candidates identified.** Neither candidate was promoted; both need human
disposition. The separately-observed intermittent flakes are *not* part of this change and
already have their own changes: launch-recovery wait timeouts →
`diagnose-recovery-readiness-timeout`; CLI empty-response JSON parse →
`diagnose-empty-response-parse-error`. Neither flake was observed in this session's runs.

1. **`product-improvement`** — base-url `exec` still has no usable continuation on the
   branches where the settle does not complete in time. With the budget corrected the
   *deterministic* path into `missing` is closed, but a genuinely stuck Editor (or the
   `refresh_attempts >= 1` cap, or a post-settle `compiling` response from the resubmit)
   still returns `running`/`refreshing` for a base-url request whose server-side record
   never existed, so the advertised `wait-for-exec --base-url --request-id` continuation
   answers `missing`. Not observed on the host in this session. Options: keep the settle
   bounded and make base-url mode resubmit instead of handing back an unreachable
   continuation, or carry a client-side record so the continuation is real.
2. **`product-improvement`** — `exec` help ("Timeout Rules") does not state that an
   automatic refresh settles on its own compile-scale budget, so `--wait-timeout-ms` no
   longer bounds that phase. A caller passing a small wait budget can now block for up to
   the settle budget when a refresh triggers. Documentation only; no durable help
   requirement is currently violated.

Ready to close: working tree carries only this change's edits
(`cli/python/unity_puer_exec_runtime.py`, `tests/test_unity_session_cli.py`,
`openspec/changes/diagnose-exec-missing-after-auto-refresh/**`); recommend a checkpoint
`git commit`, then `openspec archive diagnose-exec-missing-after-auto-refresh`, then a final
`git commit` — not executed here.
