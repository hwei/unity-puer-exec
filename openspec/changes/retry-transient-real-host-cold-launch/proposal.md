## Why

A full real-host run had one case fail with `unity_start_failed: Unity exited before ready with code 0` during a CLI-driven cold launch, and the same case passed on isolated re-run. Each case force-stops the host in `setUp`, so a fresh launch can race the previous Editor's shutdown; a single transient launch failure then fails the case with no retry. These false negatives obscure real regressions and waste a full suite run.

## What Changes

- Add a bounded, explicit retry for transient cold-launch failures in the real-host harness: when a project-scoped launch fails because the CLI could not bring the host up (`unity_start_failed`, or the launched Editor exits before ready) and the clean-boundary check passes, retry a small number of times before failing.
- Record attempt count, last launch status, and the boundary result so a flake is distinguishable from a persistent launch regression.
- Never retry genuine assertion failures or non-launch product failures.
- Keep the retry harness-scoped so the default mocked/unit workflow is unaffected.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `validation-host-integration`: real-host validation SHALL tolerate a bounded number of transient cold-launch failures instead of failing a case on the first attempt, without masking persistent failures.

## Impact

- `tests/test_real_host_integration.py` launch/warm-up helpers and boundary handling.
- Possibly a small shared retry helper under `tests/`.
- No product code change.
