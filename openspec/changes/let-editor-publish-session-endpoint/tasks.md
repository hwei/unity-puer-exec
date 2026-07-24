## 1. Resolve the open design questions first

- [ ] 1.1 Confirm that a control-service activation switch passed on the Unity command line is readable via `Environment.GetCommandLineArgs()` and survives a domain reload, so process-launched activation needs no persistence of its own.
- [ ] 1.2 Confirm that `UnityEditor.SessionState` retains a mid-session activation across a domain reload and is cleared when the Editor process ends, and record what happens on an Editor crash.
- [ ] 1.3 Confirm that write-to-temp-then-rename produces an atomic replacement on Windows that a concurrently reading CLI never observes as truncated, and record the fallback if it does not.
- [ ] 1.4 Determine whether the service can reliably remove its own publication on domain reload and on Editor quit, or whether the CLI must rely on the lockfile to classify a stale publication as residue. Record the answer in design; it decides whether the residue branch is the normal path or the exception.
- [ ] 1.5 Verify whether `EditorApplication.OpenProject` can relaunch the Editor with `-logFile` and the activation switch. If it cannot, drop the "Restart with CLI Control" menu action from scope and say so in design.

## 2. Editor publishes its own endpoint

- [ ] 2.1 Write `Temp/UnityPuerExec/endpoint.json` when the control service binds, sourcing every field from the running process: bound port, `Process.GetCurrentProcess().Id`, project path from `Application.dataPath`, session marker, and `Application.consoleLogPath`.
- [ ] 2.2 Make the write atomic per 1.3, so a reader never observes a partial record.
- [ ] 2.3 Republish when the bound port changes across a domain reload, so the publication always names the currently bound port.
- [ ] 2.4 Remove the publication when the service stops, to the extent 1.4 establishes is reliable.
- [ ] 2.5 Add source-level or Editor-side assertions that no field is derived from a machine-wide process listing.

## 3. Control-service activation becomes explicit and uniform

- [ ] 3.1 Gate service startup on an explicit activation request, replacing the current implicit start and the batch-mode-only suppression at `UnityPuerExecServer.cs:275`.
- [ ] 3.2 Read the activation switch from the process command line.
- [ ] 3.3 Add an Editor menu action that activates the service for the current process only, backed by `SessionState`, and confirm it does not restore on the next project open.
- [ ] 3.4 Warn at the point of mid-session activation that this Editor's log was fixed at launch and cannot be isolated, naming the log it is actually bound to.
- [ ] 3.5 Add the "Restart with CLI Control" menu action if 1.5 confirmed it is possible; otherwise record the decision not to.
- [ ] 3.6 Pass the activation switch from `launch_unity` on every CLI-driven launch, so CLI callers observe no behavior change.
- [ ] 3.7 Update the batch-mode real-host case so it asserts the uniform activation rule rather than a mode-specific exception, including that a batch process launched *with* activation does start the service.

## 4. CLI discovers sessions from project-local state

- [ ] 4.1 Add endpoint publication reading, and a session-state decision that uses only the project lockfile and the publication.
- [ ] 4.2 Implement the four-way state table from design D2, including the crashed-or-killed residue case.
- [ ] 4.3 Replace `validate_artifact_endpoint` and the artifact-driven recovery and launch-conflict branches in `unity_session.py` with endpoint-driven equivalents.
- [ ] 4.4 Remove `session.json` entirely: `SESSION_RELATIVE_PATH`, its read/write helpers, and the ~85 references to `session_data` / `read_session_artifact`.
- [ ] 4.5 Demote the control-port scan to the error path only, so a normal command makes one direct connection.
- [ ] 4.6 Confirm that no remaining code path derives a project's session identity from `list_unity_pids()` ordering.
- [ ] 4.7 Add unit tests for each cell of the state table, including that unrelated Unity processes do not change the outcome.
- [ ] 4.8 Add a unit test that a recycled process id cannot make an ended session look live.

## 5. Log-source resolution and stop semantics

- [ ] 5.1 Revise the resolution tiers to explicit flag, then published path, then platform default, removing the session-artifact tier.
- [ ] 5.2 Keep the published path usable when the control service does not answer a request, so observation does not degrade to the platform default on a momentary probe failure.
- [ ] 5.3 Rewrite `ensure_stopped`'s project-mode decision to use the lockfile and the publication, and make a kill target only the published process id.
- [ ] 5.4 Add unit tests that `ensure-stopped` reports stopped with unrelated Editors running, does not report stopped while the lockfile is held, and never targets a foreign process id.
- [ ] 5.5 Update `get-log-source` tier reporting and its help text for the revised tier list.

## 6. Reporting an Editor that did not opt in

- [ ] 6.1 Add the distinct non-success status for a held lockfile with no publication, with an exit code that does not collide with launch or readiness failures.
- [ ] 6.2 Make the guidance actionable: state the ways forward, and name an explicitly drivable address when the error-path scan can identify one owning the project.
- [ ] 6.3 Report observation reliability for a controllable session before the first observation, per design D4, distinguishing a project-private log from the platform default and from the platform default with other Editors running.
- [ ] 6.4 Add `--help-status` coverage for the new status and for the degraded-observation report.
- [ ] 6.5 Add unit tests for the status, the guidance content, and all three reliability classifications.

## 7. Documentation

- [ ] 7.1 Update `validation-host-integration/how-to-run.md` for the activation requirement and the revised boundary rule, replacing the parts that assume an implicitly started service.
- [ ] 7.2 Document the three launch modes and what each yields — control, isolation, or both — so a contributor can tell which one they are in.
- [ ] 7.3 State in the durable spec why the publication is Editor-authored, so a later reader does not reintroduce CLI-side writing as a convenience.

## 8. Validation and closeout

- [ ] 8.1 Run the repository unit suite and confirm no regressions.
- [ ] 8.2 Verify against the validation host that a CLI-launched Editor publishes an endpoint whose every field matches the live process, and that a single direct connection replaces the port scan.
- [ ] 8.3 Verify the Hub-launched path on the real host: an Editor opened without activation is reported as not under CLI control, the guidance is actionable, and the menu action then makes it controllable with a correctly reported non-private log.
- [ ] 8.4 Verify the batch-mode path both with and without activation.
- [ ] 8.5 Verify that `ensure-stopped` reports correctly with an unrelated Editor open, and that it never targets that Editor's process id.
- [ ] 8.6 Verify the crashed-or-killed residue case: kill the Editor, confirm the publication survives, and confirm the CLI reports the session as ended while the published log remains readable.
- [ ] 8.7 Run the full real-host suite and record the result.
- [ ] 8.8 Run `openspec validate let-editor-publish-session-endpoint` and confirm the change remains valid.
- [ ] 8.9 Record the apply closeout finding summary, stating either `No new follow-up work identified` or `New follow-up candidates identified`.
