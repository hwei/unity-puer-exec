## 1. Confirm the base-url source path

- [x] 1.1 Confirm `get-log-briefs` currently rejects `--base-url`, and that `get_log_source(base_url=...)` / `get-log-source --base-url` resolves an Editor-reported console log path through `/health`. Verify: reproduced/observed with a mocked health payload, not inferred.
- [x] 1.2 Confirm the inconsistency: a base-url `exec`/`wait-for-exec` response captures its `log_range` offsets from `default_editor_log_path()` while `get-log-source --base-url` reports the Editor-named path. Verify: the two differ when the endpoint reports a custom path.

## 2. Implement base-url support

- [x] 2.1 Make `get-log-briefs` selector-driven in the parser (`_add_selector_args`), replacing the bare `--project-path`. Verify: `--base-url` parses and supplying both selectors reports `address_conflict`.
- [x] 2.2 Add a base-url branch to `_resolve_log_path` that resolves through `unity_session.get_log_source(base_url=...)`, so base-url `log_range` offset capture and `get-log-briefs` read the same Editor-named path, with the platform default as the last resort. Verify: the advertised `log_range` and the briefs resolve the same path when the endpoint reports a custom path.
- [x] 2.3 Resolve the base-url log source in `run_get_log_briefs` via the same helper, reject `--unity-log-path` with `validate_project_mode_only`, and report `no_observation_target` when no source resolves. Verify: base-url briefs parse the reported file; absent source reports `no_observation_target`.
- [x] 2.4 Remove `get-log-briefs` from `_PROJECT_PATH_ONLY_COMMANDS` so the selector-variant construction gives the completed error-sweep candidates a base-url argv. Verify: a base-url completed response carries `--base-url`, `--range`, and `--levels error,warning`, and the drift test passes.
- [x] 2.5 Document the `--base-url` argument and the `no_observation_target` failure on the `get-log-briefs` help surface. Verify: `--help-args` and `--help-status` name both.

## 3. Validation and Closeout

- [x] 3.1 Add regression coverage: base-url `get-log-briefs` reads the reported path; `--unity-log-path` with `--base-url` is a usage error; absent source reports `no_observation_target`; a base-url response's `log_range` and brief source resolve the same Editor-named path; base-url completed guidance carries a runnable error sweep; project-path behavior is unchanged. Verify: base-url assertions fail without 2.2/2.3/2.4.
- [x] 3.2 Confirm the durable success-path requirement is restored (no base-url carve-out) and the base-url log-source contract is present. Verify: `openspec validate support-base-url-get-log-briefs --strict` clean.
- [x] 3.3 Run `tests.test_unity_session_cli`, `tests.test_unity_session_modules`, and `tests.test_openspec_spec_hygiene`, then the full `tests/` suite. Verify: green, no pre-existing guarantee relaxed.
- [x] 3.4 Complete the required apply closeout review and record the finding with allowed categories.

## Closeout

**Finding: New follow-up candidates identified** (surfaced for human discussion; not promoted
into work).

- `product-improvement` — base-url observation now resolves its log path through `/health` on
  demand. `_resolve_log_path` may be called more than once per base-url command (in addition to
  the bridge guard's probe), so the same endpoint is probed repeatedly within one invocation.
  Caching the resolved log path per invocation would remove the redundant probes without changing
  behavior.
- `validation-gap` — no real-host check was run this session. Unit coverage exercises the
owned-point, health-reports-none fallback (to the default path), and no-source
`no_observation_target` cases, but only a real host can prove the path the Editor reports
matches the file it actually writes. A real-host run (`exec --base-url …`, then
`get-log-briefs --base-url …` with the returned `log_range`, ideally against a custom `-logFile`)
would close this.

**Explicitly not follow-ups from this change:**

- Remote / cross-machine Editor log transfer remains an explicit non-goal; the endpoint is
  assumed to share the caller's filesystem.
- `get-log-source` routing through `probe_health_payload` is behavior-neutral: that function is a
  one-line delegation to `_probe_health`, so timeout, retry, and error mapping are unchanged, and
  only the base-url branch is affected.

**Evidence:** `python -m unittest discover -s tests` → 727 tests OK (3 skipped);
`tests.test_unity_session_cli` (248), `tests.test_unity_session_modules`, and
`tests.test_openspec_spec_hygiene` green inside that run;
`openspec validate support-base-url-get-log-briefs --strict` clean; `openspec validate --all` →
34 passed, 0 failed. The pre-fix inconsistency (base-url `log_range` from the platform default
versus the Editor-named path) was confirmed with a mocked health payload during task 1.2.
