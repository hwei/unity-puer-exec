# Validation transcript (2026-11-06)

Host: c3-client-tree2 (Unity 2022.3.62f2), prepared with `prepare_validation_host.py --clear-embedded-shadow` then `prepare_validation_host.py`.

## Pre-change baseline (runtime at 1bbdaaf + new real-host cases)

`UNITY_PUER_EXEC_RUN_REAL_HOST_TESTS=1 python -m unittest -v tests.test_real_host_integration.EditorCrashSurfaceRealHostTests` -> FAILED (failures=2)

- play: exit 10 `running` after 201.1 s (`--timeout-seconds 180`), although the Editor crashed (`Crash_2026-11-06_050829373`).
- exec: exit 26, but no `started_at` / `crash_report_dir` (coerced journal key `started_at` was read as `started_at_utc`); report `Crash_2026-11-06_050458023` existed.

## Post-change (HEAD c95aca2)

`... EditorCrashSurfaceRealHostTests tests.test_real_host_integration.PlayModeCompileBlockRealHostTests` -> Ran 9 tests in 1087.8 s, OK

- play: exit 26 `editor_crashed_during_request` in 44.2 s, editor_pid 31636, crash_report_dir `Crash_2026-11-06_061903285`.
- exec: exit 26 in 12.2 s, editor_pid 25668, crash_report_dir `Crash_2026-11-06_061540663`.
- PlayModeCompileBlockRealHostTests: 7/7 ok (reload retry paths unaffected).

## Teardown

`cleanup_validation_host.py` (already_clean), `--restore-manifest` (restored), `--restore-embedded-shadow` (restored); host `git status --short` empty. tree3 Editor (pid 80124) untouched.
