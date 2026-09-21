## Why

The real-host integration suite stops and relaunches the Unity Editor for every test
method. `RefreshOnChangeRealHostTests.setUp` calls `_ensure_clean_test_boundary` (which
stops the host), then `_warm_up_project_exec` (which launches it again). A launch is a
cold Unity start plus project import — tens of seconds, and minutes on a cold cache — so
suite wall-clock is dominated by relaunch rather than by the assertions. The 10-case
refresh-on-change class now takes ~906s, and roughly 90s of that is per case spent
before any assertion runs.

The cost is not merely annoying: it prices new coverage out of the suite. Every case
added to the class adds a full launch, so authors either stop writing real-host cases
or stop running the suite often enough for it to catch regressions. The isolation being
bought with the relaunch is real but does not require a relaunch — a fresh process is
one way to get per-case isolation, not the only way.

## What Changes

- **Launch once per suite, not once per case.** The real-host classes bring the host up
  in a class-level fixture and reuse it across methods, then stop it when the class
  finishes (including on failure, so a broken case cannot leak a running Editor).
- **Isolation becomes per-case state reset instead of per-case relaunch.** Between
  cases the suite removes repository-owned validation temp assets, returns the Editor to
  edit mode, and resets test-owned session/tracker state, so a case cannot observe
  another case's leftovers.
- **Pristine-process cases keep their own boundary.** Cases that genuinely need a fresh
  process — batch-mode activation checks and occupied-preferred-port rollover — opt into
  their own launch/stop rather than being forced onto the shared host.
- **Failure diagnostics are preserved.** A host that dies mid-suite is relaunched within
  the retry budget or the suite fails with the same attempt/launch diagnostics the
  current per-case boundary already reports.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `validation-host-integration`: the real-host workflow is required to reuse one Editor
  per suite and to achieve per-case isolation by resetting state rather than by
  relaunching the host, with an explicit opt-out for cases that need a pristine process.

## Impact

- `tests/test_real_host_integration.py` — class-level host fixture; per-case reset; the
  cases that must keep their own launch boundary.
- `tests/real_host_retry.py` — the transient cold-launch retry budget applies to the
  suite-level launch instead of one launch per case.
- `openspec/specs/validation-host-integration/how-to-run.md` — describe the reuse model
  and the isolation guarantees a contributor can rely on.
- No product (Editor package or CLI) behavior changes; this is test-harness cost and
  isolation only.
