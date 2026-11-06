# Proposal

## Why

`exec-import-support` carries eleven durable requirements, including three that specify
`--import-base-url` resolution and one that specifies `--reset-jsenv-before-exec` clearing the
module cache. `tests/test_real_host_integration.py` — 52 cases against a live Editor — covers
**neither flag**. A grep for either string in that file returns nothing.

That gap became load-bearing during `support-puerts-2x-jsenv`. The one place a PuerTS major
could plausibly diverge was module loading: 2.2.2's `JsEnv` gates ESM detection on
`loader is IModuleChecker` (`Runtime/Src/Default/JsEnv.cs:110`) while `PuerExecLoader`
implements only `ILoader`, and the harness specifier `puer-exec://harness/<request-id>` carries
no extension for a fallback check to read. The only way to answer it was to hand-drive both
flags against both hosts through a scratch probe at `.tmp/puerts2_e2e_probe.py`. It worked —
relative imports resolved and a rewritten module was reloaded after an explicit reset on 2.2.2
and 3.0.0 alike, so no `IModuleChecker` was needed — but `.tmp/` is gitignored. The evidence
that retired a real design risk is not repeatable, not reviewable, and will not notice the next
regression.

## What Changes

- The probe's import and reset steps become real-host cases in
  `tests/test_real_host_integration.py`, inside the existing shared-device class so they add
  cases and not Editor launches.
- The reset case is written to discriminate the **explicit** flag from the default staleness
  recovery that already resets a changed module in-invocation. Asserting only "a changed module
  is reloaded" would pass without the flag ever being exercised, because the default
  `--stale-module-policy` already does that. The discriminator is `ctx.globals` continuity: an
  explicit reset clears state a unchanged-module exec would otherwise preserve.
- The import case covers a filesystem `--import-base-url` with a relative import, and asserts the
  imported value crosses the bridge into `result`, which is what makes it a resolution test
  rather than a "did not throw" test.
- Fixtures are written under the host's temp area and cleaned up by the existing per-case reset,
  so the cases leave no residue in a host project that is under version control.
- The scratch probe is retired once the cases exist, and the change records where its evidence
  moved to.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `validation-host-integration`: adds a coverage requirement in the house style already used by
  "Real-host runtime validation covers critical CLI workflows" and "Real-host validation covers
  control-port binding behavior", naming ES module import resolution and explicit JsEnv reset as
  real-host-covered surfaces. The existing requirement that suite cost scales with cases rather
  than host relaunches is not amended, and the new cases must satisfy it.

## Impact

- Tests: `tests/test_real_host_integration.py` gains cases; suite runtime grows by roughly the
  cost of a few exec round-trips against an already-launched Editor, not by a launch.
- No product surface changes: no CLI behavior, no Unity package, no payload, no exit code.
- Tooling: `tests/test_real_host_reset.py` may need a matching mocked case if the new cases add
  device state the reset path must restore; that is discovered during apply, not assumed here.
- Hosts: exercised against the 2.2.2 host and a 3.0.0 host, since the whole point is that the
  surface is version-sensitive. Both were already wired and verified during
  `support-puerts-2x-jsenv` (archived `2026-11-06`), whose `validation-evidence.md` holds the
  manual results these cases replace.
- Follow-up to `support-puerts-2x-jsenv`. That change deliberately kept the probe in `.tmp/`
  because it was evidence for one decision, not a permanent harness.
