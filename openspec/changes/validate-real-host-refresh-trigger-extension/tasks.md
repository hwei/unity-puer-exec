## 1. Confirm the gap and the watched set

- [x] 1.1 List every call site of `_write_compile_triggering_probe` and record the name each one passes. Verify: the inventory shows every call site already stages a watched extension, so the new validation breaks none of them.
- [x] 1.2 Read the durable help statement about which changes trigger automatic refresh and record the extensions it names. Verify: the finding cites the help text rather than restating it from memory.
- [x] 1.3 Confirm against the Editor-side change signal that the watched set is exactly those extensions, and record any extension one has and the other lacks. Verify: the finding names both sources and resolves the difference.
- [x] 1.4 Reproduce the failure locally: stage a probe without a watched extension and confirm the Editor reports `no_pending_change` rather than a refresh. Verify: reproduced against the host, so the fix targets the observed condition.

## 2. Validate the probe and sharpen the wait message

- [x] 2.1 Make `_write_compile_triggering_probe` reject a probe name outside the watched set before writing anything, naming the watched extensions. Verify: a mistyped probe fails with no Editor launch and no validation-host write.
- [x] 2.2 Source the watched set from the durable help statement rather than an inline literal, so the two cannot drift. Verify: a change to the help entry surfaces at staging time rather than silently accepting a name the Editor ignores.
- [x] 2.3 Make the `_wait_for_refresh_pending` failure name the watched extensions and the observed `skipped_reason`, keeping the existing distinct message for a control endpoint that never returned. Verify: a correctly staged but unobserved probe names the cause, and the endpoint-timeout path still reports a dropped endpoint.
- [x] 2.4 Add regression coverage for the staging rejection and the wait failure message. Verify: each fails without 2.1 or 2.3 respectively, and neither requires a live Editor for the staging rejection.

## 3. Validation and Closeout

- [x] 3.1 Run the real-host suite against the validation host and confirm the refresh cases still cross real reloads with the new validation in place. Verify: the refresh cases pass, and a probe written through the helper is rejected locally when its extension is wrong.
- [x] 3.2 Confirm no product code changed and no product output is affected. Verify: `git diff` touches only `tests/test_real_host_integration.py` and this change's artifacts.
- [x] 3.3 Run `openspec validate validate-real-host-refresh-trigger-extension --strict` and `openspec validate --all`. Verify: the delta matches the implemented behavior.
- [x] 3.4 Complete the required apply closeout review and record the finding with allowed categories, separating this staging gap from the guidance gap in `restore-base-url-exec-continuation-guidance` and from the intermittent launch-recovery and CLI empty-response flakes. Verify: the closeout names each candidate and its disposition.

## Findings

- **1.1** Seven call sites, every one already `.cs`: `BaseUrlRefreshContinuationProbe.cs`,
  `AutomaticRefreshProbe.cs`, `PlayBlockProbe.cs`, `GenerationBaselineProbe.cs`,
  `PlayPreSettleProbe.cs`, `StopDeferredProbe.cs`, `PlayModeRestoreProbe.cs`.
- **1.2** The durable statement is `exec --help-args`, "Automatic refresh: before each exec the
  server checks for compile-triggering code changes (`.cs`, `.asmdef`, `.asmref`, `.rsp`) …".
- **1.3** The Editor-side source is `UnityPuerExecImportChangeTracker.cs:33`
  (`CompileTriggeringExtensions = { ".cs", ".asmdef", ".asmref", ".rsp" }`). The two sets match
  exactly; no extension exists in one and not the other.
- **1.4** Reproduced against the host without the guard: a directly written
  `Assets/__codex_validation_temp/NoWatchedExtensionProbe` left the health `refresh.pending` at
  `not_pending` before and after the write (`.tmp/probe_no_extension_refresh.log`).

## Closeout

**Finding: New follow-up candidates identified** (surfaced for human discussion; not promoted
into work).

- `tooling-improvement` — two other harness helpers still restate the watched
  compile-triggering extension set inline: `_drop_latched_temp_scripts` and
  `_drop_unimported_compile_probes`. This change sourced the set from the durable `exec --help-args`
  statement only for `_write_compile_triggering_probe`, leaving a second and third copy that can
  drift. Their failure mode is a leftover probe rather than the misleading refresh message this
  change removes, so consolidating them is separate work.

**Explicitly not follow-ups from this change:**

- The guidance gap is already tracked as `restore-base-url-exec-continuation-guidance`.
- The intermittent launch-recovery and CLI empty-response flakes remain out of scope. The one
  real-host failure observed during this apply — `test_play_settles_a_pending_change_then_reaches_playing`
  failing with `[WinError 10054]` on the `play` transport — passed on immediate retry and belongs
  to that flake class, not to this change.

**Scope note for 3.2:** the regression coverage added for 2.4 lives in
`tests/test_real_host_reset.py`, following the existing default-suite helper-test pattern for
`tests/test_real_host_integration.py` helpers. `git diff` therefore touches two test modules plus
this change's artifacts; no product code (`cli/**`, `packages/**`) changed.

**Evidence:**

- Default suite green: `python -m unittest discover -s tests` → 719 tests, 0 failures
  (3 real-host skips).
- Real-host refresh cases green: `RefreshOnChangeRealHostTests` → 10/10 in 389.753s against
  `c3-client-tree2`, transcript `.tmp/realhost_refresh_run.log`.
- Remaining real-host classes: 31/32 green (3 skipped) in 1820.745s; the single failure
  (`test_play_settles_a_pending_change_then_reaches_playing`, `WinError 10054`) passed on retry in
  140.310s. Transcripts `.tmp/realhost_rest_run.log`, `.tmp/realhost_play_retry.log`.
- Task 1.4 reproduction transcript: `.tmp/probe_no_extension_refresh.log`.
- `openspec validate validate-real-host-refresh-trigger-extension --strict` valid;
  `openspec validate --all` → 33 passed, 0 failed.
