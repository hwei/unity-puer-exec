## Why

`test_base_url_automatic_refresh_and_wait_for_compile_against_real_host` fails
deterministically on the validation host. It is not environment noise: it fails the same
way on the per-case-relaunch harness and on the shared-host harness, and it is the one
failure that stayed constant across four full real-host runs (see
`openspec/changes/reuse-real-host-editor-across-suite/validation-evidence.md`).

Observed, on the first case after a cold launch:

```
write Assets/__codex_validation_temp/BaseUrlAutomaticRefreshProbe.cs
exec --base-url <host>            (the probe starts an automatic refresh)
  -> response is non-terminal, request_id accepted
wait-for-exec --request-id <id> --wait-timeout-ms 240000
  -> exit 13, status "missing"
     error: "no recoverable record exists for request_id"
     log_range: {start: 1690261, end: 1690261}
```

The write correctly makes the project dirty and the automatic refresh correctly starts a
compile-plus-domain-reload. The defect is what happens across that reload: the accepted
`exec` request stops being recoverable and the CLI surfaces a terminal-looking `missing`
instead of settling the cycle and returning the script result.

This violates the durable contract "Automatic refresh is a non-terminal phase of the
accepted exec request", whose scenario requires that "the terminal response carries the
script result, not a refresh confirmation". The caller never gets a script result.

Two facts from existing, already-shipped behavior sharpen the question rather than answer
it:

- `implement-pending-exec-artifact-lifecycle` made *expired or malformed* pending
  artifacts surface as non-recoverable `missing` **by design**. So `missing` is not itself
  a bug — the question is whether the automatic-refresh reload is incorrectly producing an
  expired/malformed artifact, or whether the recovery path simply never resubmits.
- The CLI's own resubmit gate, `_running_or_timed_out_response`, returns true only for
  `status == "running"` or `not_available + error == "timed out"`. A `missing` response is
  never resubmitted, so there is no code path that turns this back into a running request.

## What Changes

- Root-cause the accepted-`exec` lifecycle across an automatic-refresh-triggered domain
  reload: determine whether the pending artifact is lost/invalidated by the reload, or
  whether it survives and the recovery/resubmit path is the gap. The observed
  `log_range.start = 1690261` (a stale offset that recurs across runs) suggests the
  artifact may be carrying pre-reload log offsets that no longer resolve.
- Decide the correct durable behavior: the accepted request must remain recoverable across
  the refresh it triggered, or the CLI must resubmit as a new attempt and return the script
  result — never a bare terminal `missing` for a request the CLI itself caused to reload.
- Make the minimal fix at the identified site and add regression coverage at the unit
  layer, plus real-host confirmation of the previously failing case.
- The durable contract delta below is **provisional**: it names the observed case as an
  explicit scenario without changing the requirement's normative text. If investigation
  finds the requirement text itself needs different substantive changes, this delta is
  revised before tasks are finalized.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `formal-cli-contract`: adds one explicit scenario to the existing "Automatic refresh is
  a non-terminal phase of the accepted exec request" requirement, naming the exact
  observed case (an automatic-refresh-triggered domain reload must not turn the accepted
  request into a non-recoverable `missing` with no script result). This does not change
  the requirement's normative text — the "terminal response carries the script result"
  language already covers it — it makes the case explicit and testable.

## Impact

- Affected code (investigation targets): `cli/python/unity_puer_exec_runtime.py`
  (`_settle_after_automatic_refresh`, `_settle_base_url_after_refresh`,
  `_running_or_timed_out_response`, the `exec`/`wait-for-exec` recovery branches) and
  `cli/python/unity_session_logs.py` (pending exec artifact lifecycle).
- Affected behavior: project-scoped accepted `exec` recovery across an automatic-refresh
  domain reload; `wait-for-exec` behavior when the pending record is gone.
- Affected validation: `tests/test_real_host_integration.py`
  (`test_base_url_automatic_refresh_and_wait_for_compile_against_real_host`) plus unit
  coverage for the settle/resubmit path.
- No change to the non-terminal refresh contract itself, the code-only refresh boundary, or
  the batch/rollover behavior covered by other changes.
