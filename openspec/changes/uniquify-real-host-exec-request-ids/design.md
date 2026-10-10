# Design

## Context

See proposal.md — Why. Inherited from `harden-real-host-per-case-reset`:

- The server accepts a repeated `request_id` with the same code as the existing job and does not run the script again (`TryAcceptExecRequest` returns `accepted` with `isNewRequest` false).
- `test_resolve_blocker_cancel_is_rejected_for_save_scene_against_real_host` now builds its id with `time.time_ns()`. A same-process run of that case three times passed after the change.
- These call sites in `tests/test_real_host_integration.py` still use only `os.getpid()`: `sync-`, `modal-modified-`, `disconnect-recover-`, `modal-save-scene-`, `resolve-modified-`, `resolve-save-scene-`, `unknown-dialog-`, and `open-panels-`.

## Goals / Non-Goals

**Goals:**

- One helper builds a real-host exec request id that changes on every call in the same process.
- Every exec id in that module uses the helper.
- A unit test fails if a request id in that module is built only from the process id.

**Non-Goals:**

- Changing server replay of an identical `request_id`.
- Making ids unique across processes beyond what a timestamp or random value already provides.
- Re-running the real-host suite. The failure mode is the id, and the unit test locks the source.

## Decisions

### D1. One helper, called at each submission

Add `_unique_request_id(prefix)` next to the other module helpers. It returns `prefix` plus a value that changes per call (`time.time_ns()` is enough). Each of the eight `os.getpid()` sites, and the save-scene cancel site that already calls `time.time_ns()`, calls the helper at the moment it builds the CLI argument. Do not cache the id on the class.

### D2. Lock the source, not the Editor

`tests/test_real_host_reset.py` reads the module source and asserts that an exec `--request-id` is not formatted from `os.getpid()` alone, and that two helper calls differ. That runs in the default unit suite.

## Risks / Trade-offs

- A test that wanted a stable id across two CLI calls in one case would break. None of the listed sites do that. Each id is one submission.
- Source inspection can miss an id built in a helper. The assertion should search the module for `request_id` assignments and `--request-id` arguments that interpolate `os.getpid()`.

## Migration Plan

Test-only. No host asset or protocol migration.

## Open Questions

None.
