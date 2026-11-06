# Proposal

## Why

`unity-puer-exec exec --help` states there is "no supported way to call into the host
application's JavaScript runtime directly" (`cli/python/help_surface.py:347`), and
`formal-cli-contract` currently requires that help describe no such mechanism. That claim is
false on **both** PuerTS majors, and it has been costing agents a working technique:

- 2.x — `puer.loadType('Puerts.JsEnv').jsEnvs` lists the host application's own environments
  (`com.tencent.puerts.core/Runtime/Src/Default/JsEnv.cs:26`), and `env.Eval(code)` runs in one.
- 3.x — the same shape under `Puerts.ScriptEnv.scriptEnvs`.

GitHub issue #4 reported this from a 2.2.2 host and found it "very useful for UI
verification". It is reached through the C# bridge the help already names as the supported
route, so the help is currently self-contradictory: it points at the bridge and then denies
that the bridge can reach the thing it reaches.

## What Changes

- `exec` help stops asserting that no mechanism exists, and instead names the host-environment
  enumeration reachable through the bridge.
- The naming is explicitly **bounded**: the static field is PuerTS-internal and its name
  differs per major (`JsEnv.jsEnvs` vs `ScriptEnv.scriptEnvs`), so help presents it as an
  observed escape hatch outside this CLI's contract, not as a guaranteed interface. The
  environment-separation statement stays — it is true and it is the reason the escape hatch is
  needed at all.
- The `formal-cli-contract` requirement that forbids help from describing such a mechanism is
  amended, and a new requirement fixes what the bounded naming must and must not claim.
- Help-text pinning tests are updated so the corrected wording cannot silently regress to the
  absolute denial.

**Decision this proposal makes, and the alternative.** The recommendation is to document the
route as *observed but outside the CLI contract*. The alternative is to adopt it as a
supported capability, which would make this repository the owner of a PuerTS internal whose
name has already changed once between majors and which no test in this repository currently
exercises. Adopting it means committing to tracking it across PuerTS releases. If that is
wanted, this proposal's spec delta should be widened before apply rather than after.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `formal-cli-contract`: the requirement "Help documents a cross-environment coordination
  pattern" currently forbids help from describing any mechanism for calling into the host
  application's JavaScript runtime. That prohibition is relaxed to a bounded naming, and a new
  requirement states what the naming must claim and disclaim.

## Impact

- Code: `cli/python/help_surface.py` (the exec script-authoring guidance block).
- Tests: the help-surface pinning tests that assert the current wording. No test currently
  pins the exact sentence, so the risk is a *missing* pin rather than a broken one; adding it
  is part of this change.
- No change to CLI behavior, exit codes, payloads, or the Unity package. This is a
  documentation-contract change only.
- Follow-up to `support-puerts-2x-jsenv` (archived `2026-11-06`), which established the
  two-major support that makes the version-specific field name worth stating explicitly. That
  change's evidence confirmed both majors work end to end but deliberately left this side note
  out of scope.
