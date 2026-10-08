## Why

The real-host suite's two control-port rollover cases cannot run in the condition they exist
to validate. Both `skipTest` when another project's Editor already holds the preferred
control port:

```
tests/test_real_host_integration.py:2047
    self.skipTest("preferred control port {} is held by an unrelated service".format(...))
tests/test_real_host_integration.py:2135  (same, in the discovery case)
```

But that is the precondition, not the absence of one. The durable requirement already says
so:

> #### Scenario: Contributor validates rollover when the preferred control port is occupied
> - **WHEN** a contributor runs the real-host validation **with the preferred control port
>   already occupied** at the time an interactive control service starts
> - **THEN** the validation asserts the interactive control service becomes ready on a later
>   port in the bounded range rather than failing the whole scan
> - **AND** the validation asserts the ready health identity reports the later selected port
>   and its base URL

So the suite skips precisely when the spec's scenario is satisfied, and the scenario is
**unreachable on any host that has another Unity project open** — the same multi-Editor
condition under which this defect family (`diagnose-exec-endpoint-misroute`,
`diagnose-recovery-readiness-timeout`, the refresh-recovery defects) actually appears.

Observed during `diagnose-recovery-readiness-timeout`'s real-host run: ports 55231 and 55232
were held by `c3-client-tree3` and `c3-client-tree5`, both cases skipped for that reason, and
the confirmation had to come from a purpose-built probe instead of the suite. The suite
silently reports green while asserting nothing.

The second gap is the mirror image: after a warm-up that reported success, the case's own
oracle failing to find the host's ready endpoint is treated as "cannot stage rollover" and
skipped — a `skip` for what is a product-observable condition, which the repository's own
result table calls a fail.

## What Changes

- Make the rollover cases assert the spec's scenario when the preferred port is already
  occupied by another project's Editor, instead of skipping. The rollover is already real in
  that environment (the host binds a later port); only the binder-staged mid-reload race is
  not, and only that sub-assertion may be omitted.
- Separate the two properties the cases currently conflate: that the service becomes ready on
  a later port when the preferred port is occupied (assert unconditionally), and that the
  service rebinds across a domain reload while the preferred port is held by a binder (assert
  only when that staging was actually achieved).
- Turn the "suite cannot see the host's own ready endpoint after a successful launch" skips
  into failures after a bounded retry, so a product-observable condition is not reported as a
  missing prerequisite.
- Correct the run instructions' skip policy for these cases, which currently documents the
  inverted condition.
- Ride-along test-fidelity fix: `_scan_for_project_endpoint_any_status` is named for a
  capability it cannot have (only a `ready` payload carries `project_path`), and the unit test
  that covers it asserts against a `compiling` payload shape the bridge never emits. Align the
  name and the premise with the real payload shape, collapsing the function into
  `discover_project_endpoint` if they are in fact equivalent.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `validation-host-integration`: sharpens "Real-host validation covers control-port binding
  behavior" so an unrelated Editor occupying the preferred port is named as that
  requirement's scenario precondition and cannot be treated as a missing prerequisite, and so
  a suite that cannot observe the host's own ready endpoint after a bound launch fails rather
  than skips.

## Impact

- Affected code: `tests/test_real_host_integration.py` (the two rollover cases, their shared
  `_stage_rollover` helper, and the discovery/rollover assertions),
  `openspec/specs/validation-host-integration/how-to-run.md` (skip policy), with a
  test-fidelity follow-through in `cli/python/unity_session.py` and
  `tests/test_unity_session.py`.
- Affected behavior: real-host validation coverage only. No product behavior changes.
- Inherited from `diagnose-recovery-readiness-timeout`: that change fixed the readiness
  resolver so a wait falls back to range-scan discovery when its held candidate cannot be
  confirmed, and widened the CLI scan bound to the service's actual bind range
  (55231–55250). Both findings remain true. This change addresses the validation gap that
  change recorded but did not fix: the suite could not exercise the rollover path it
  depended on for evidence.
- Not this change: the `diagnose-exec-missing-after-auto-refresh` request-recovery defect and
  the `diagnose-empty-response-parse-error` parse defect.
