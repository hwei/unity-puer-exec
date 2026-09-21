## 1. Measure the current cost

- [ ] 1.1 Record the per-case and total wall-clock of `RefreshOnChangeRealHostTests` and `ValidationHostRealHostTests` as they run today, and attribute the time between host launch, per-case setup, and assertions. Verify: the record names how much of the total is host launch, so the change's premise is measured rather than assumed.

## 2. Class-level host fixture

- [ ] 2.1 Add a class-level fixture that establishes the clean starting boundary and brings the host up once through the existing `real_host_retry.warm_up_with_retry` path, exposing the resolved base URL to cases. Verify: a case can resolve `_base_url` without performing a launch itself.
- [ ] 2.2 Stop the host and remove repository-owned validation temp assets in class teardown, including when a case fails. Verify: a deliberately failing case does not leave a running Editor behind for the next suite invocation.
- [ ] 2.3 Reduce per-case setup to the cheap reset only; no case stops or relaunches the host for ordinary execution. Verify: running two ordinary cases performs exactly one host launch.

## 3. Per-case isolation reset

- [ ] 3.1 Reset repository-owned validation temp assets (including probe subdirectories) between cases. Verify: a case that writes temp assets does not affect the next case's assertions.
- [ ] 3.2 Return the Editor to edit mode between cases and fail loudly if it cannot. Verify: a case that leaves play mode behind does not make the next case run against a play-mode Editor.
- [ ] 3.3 Reset test-owned change-signal state between cases so a case that leaves candidates or a synthetic pending change behind does not gate the next case. Verify: the refresh cases run in any order against a shared host.

## 4. Pristine-process cases

- [ ] 4.1 Give the batch-mode activation cases and the preferred-port rollover case an explicit opt-out that owns its own launch and stop boundary. Verify: each such case reports its own boundary result and is not forced onto the shared host.
- [ ] 4.2 Confirm a shared host that dies mid-suite is either re-established within the retry budget or failed with machine-usable launch diagnostics. Verify: the failure path records attempt count and last launch status and does not report a pass.

## 5. Validation and closeout

- [ ] 5.1 Run the full real-host suite on the shared host and record wall-clock before/after together with any case that depended on the old per-case relaunch. Verify: the evidence states whether the host relaunch was the dominant cost, and names any case that needed its own boundary.
- [ ] 5.2 Update `openspec/specs/validation-host-integration/how-to-run.md` to describe the reuse model and the per-case isolation guarantees. Verify: a contributor can tell which cases reuse the host and which own their boundary.
