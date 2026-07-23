## 1. Bridge publishes its own log path

- [ ] 1.1 Thread `cachedConsoleLogPath` from `UnityPuerExecServer` health handling into `UnityPuerExecProtocol.BuildHealthResponseJson` as `console_log_path`, omitting the field when the path is empty rather than emitting a guessed default.
- [ ] 1.2 Add source-level assertions that the ready health payload carries `console_log_path` and that the empty case omits it, following the shape used for `bridge_version`.
- [ ] 1.3 Verify against the validation host that `/health` reports a `console_log_path` equal to the log file that Editor is actually writing to.

## 2. CLI resolution precedence

- [ ] 2.1 Add the bridge-reported path as a resolution tier in `unity_session_logs.resolve_effective_log_path`, ranked below explicit `--unity-log-path` and below the session artifact `effective_log_path`, and above the platform default.
- [ ] 2.2 Thread the health-reported path from the point a ready health payload is available into session construction, so the tier has a value to use without an extra probe where one was already taken.
- [ ] 2.3 Record the resolved path in the session artifact so subsequent commands keep observing the same file once a session exists.
- [ ] 2.4 Report the resolution tier in the `get-log-source` result so a caller can distinguish a path the Editor named from the platform-default fallback.
- [ ] 2.5 Add unit tests covering all four tiers in order, including that an unreachable control service falls through to the platform default rather than failing.
- [ ] 2.6 Add a unit test confirming the session-artifact tier still wins when the control service is unreachable, so log observation does not become dependent on service reachability.

## 3. Project-private launch log

- [ ] 3.1 Give launch-driven project-scoped sessions a default log path under the target project's `Temp/` directory when no `--unity-log-path` was supplied, passing it through the existing `launch_unity` `-logFile` parameter.
- [ ] 3.2 Ensure the directory is created before launch and that an existing file is appended to or rotated deliberately rather than failing the launch.
- [ ] 3.3 Confirm `--unity-log-path` still overrides the project-private default.
- [ ] 3.4 Add unit tests asserting the launch argument list carries `-logFile` with a project-local path by default, and the caller-supplied path when one is given.
- [ ] 3.5 Verify against the validation host that a CLI-launched Editor writes to the project-local log and that `console_log_path` reports that same path, closing the loop between sections 1 and 3.

## 4. Invalidated offset reporting

- [ ] 4.1 Detect in the log-reading path that a caller-supplied `start_offset` exceeds the current end of the observed log, keeping the existing rescan-from-zero read behavior.
- [ ] 4.2 Surface the condition in the response, naming the observed log path, and confirm an observation that supplies no offset cannot trip it.
- [ ] 4.3 Add `--help-status` or guidance coverage for the condition so a caller meeting it is told what invalidated the offsets.
- [ ] 4.4 Add unit tests for offset-beyond-EOF, offset-absent, and normal-offset cases.

## 5. Documentation and harness

- [ ] 5.1 State in `validation-host-integration/how-to-run.md` that an unrelated Unity Editor shares the platform default per-user log, what that does to byte-offset observation, and how host-private logging removes the hazard.
- [ ] 5.2 Describe the symptom — a log-observation wait timing out with no matched content — so a contributor can recognize it without bisecting the product.
- [ ] 5.3 Ensure the real-host suite brings the host up through the project-private log path so individual cases need no log-path flag.

## 6. Validation and closeout

- [ ] 6.1 Run the repository unit suite and confirm no regressions.
- [ ] 6.2 Re-run `test_exec_checkpoint_observation_chain_against_real_host` and `test_exec_timeout_recovery_avoids_disconnect_noise_against_real_host` with an unrelated Unity Editor deliberately open, and record whether the isolated log resolves them. If either still fails, report it as a distinct finding rather than folding it into this change.
- [ ] 6.3 Run the full real-host suite against the validation host and record the result.
- [ ] 6.4 Run `openspec validate isolate-validation-host-editor-log` and confirm the change remains valid.
- [ ] 6.5 Record the apply closeout finding summary, stating either `No new follow-up work identified` or `New follow-up candidates identified`.
