## 1. Root-Cause Investigation

- [ ] 1.1 Trace the shared decoding boundary: read `unity_puer_exec.run_cli` (or its equivalent), the `failed` envelope construction in `unity_puer_exec_runtime.py`, and every place subprocess stdout/stderr is passed to `json.loads`. Verify: the map names the exact `json.loads` call that raised, and the code path that turned the exception into the caller-facing `error`.
- [ ] 1.2 Determine where the empty body comes from — the bridge server returned nothing, the transport closed early, or the CLI's own subprocess invocation produced no output. Verify: the finding names the source with evidence (log, request capture, or reproduction), not inference.
- [ ] 1.3 Write a deterministic reproduction (unit-level preferred: an empty/whitespace body reaching the decoder) that produces the raw decode message today. Verify: the reproduction fails on current code and asserts on the caller-facing `error` field, not only on an internal exception.
- [ ] 1.4 Enumerate the command families that pass through the same boundary and confirm the fix belongs there rather than in `exec` alone. Verify: the finding states which commands share the decoding path.
- [ ] 1.5 Record the confirmed root cause in `design.md`'s Decisions section, replacing the placeholder text. Verify: a reader can see the empty-body source, the decode site, and why the fix is placed there.

## 2. Fix and Regression Coverage

- [ ] 2.1 Replace the raw decode failure with a structured, branchable non-success payload (named status, operation, exit-code meaning, `next_steps`) at the shared boundary. Verify: the reproduction from 1.3 passes and no success payload shape changes.
- [ ] 2.2 Ensure an empty body is never surfaced as a bare interpreter message in any command family that shares the boundary. Verify: a sweep over the command registry shows the decode path is centralized.
- [ ] 2.3 Add regression tests for the empty/non-JSON body case at the shared boundary, plus one command-level assertion. Verify: the regression fails without 2.1's fix.
- [ ] 2.4 Confirm that a genuinely unexpected process-level failure still exits with its formal non-zero code and remains distinguishable from the new empty-body state. Verify: the fix does not collapse distinct failures into one generic code.

## 3. Validation and Closeout

- [ ] 3.1 Run the focused Python suites relevant to the decoding boundary and command envelopes (`tests.test_unity_session_cli`, `tests.test_unity_puer_session`, `tests.test_direct_exec_client`, `tests.test_cli_version`). Verify: green.
- [ ] 3.2 Re-run the real-host case that surfaced it (`test_exec_rejects_legacy_fragment_script_against_real_host`) and, if the empty body reproduces, confirm it now yields the structured state rather than the raw message. Verify: the caller-visible failure mode is the structured one.
- [ ] 3.3 Run `openspec validate diagnose-empty-response-parse-error` and confirm the change is archive-ready; revise the provisional delta if investigation concluded the durable text itself needs strengthening. Verify: the delta matches the implemented behavior.
- [ ] 3.4 Complete the required apply closeout review and record either `No new follow-up work identified` or human-discussed follow-up candidates in an allowed category. Verify: the closeout separates this defect from `diagnose-exec-missing-after-auto-refresh` and `diagnose-recovery-readiness-timeout`.
