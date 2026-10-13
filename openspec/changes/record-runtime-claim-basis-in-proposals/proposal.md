# Proposal

## Why

A proposal can rest its rationale on a concrete runtime claim (a call count, a probe count, a
number of resolution passes) that was assumed rather than observed. When that assumption is
wrong, the discovery only lands mid-apply, after planning effort is already committed. The
`cache-base-url-log-path-resolution` change is the concrete case: it proposed caching a base-url
log path because "`_resolve_log_path` can be called more than once per base-url command", but
measurement showed the resolution runs exactly once per invocation, so the stated premise did not
hold and the change was marked `assumption_state: invalid` before any code was written.

## What Changes

- Add a durable `repository-governance` recommendation: when a proposal's rationale depends on a
  concrete runtime behavior, the proposal records whether that claim is measured or an unverified
  hypothesis, and names the measurement when it exists.
- The rule is advisory (`SHOULD`), not a gate. A claim that rests on human observation which
  cannot be collected automatically may be recorded as an unverified hypothesis instead, and the
  apply tasks must verify it before implementation.
- No new tooling and no automated enforcement: this change records the expectation, it does not
  add a checker.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `repository-governance`: adds a requirement that proposal runtime claims carry their basis
  (measured vs. unverified hypothesis), as an advisory rule rather than an apply gate.

## Impact

- Affected artifact: `openspec/specs/repository-governance/spec.md` (durable requirement added on
  archive).
- Affected behavior: none in product code or CLI. This is a planning-discipline rule for proposals.
- Upstream context: apply closeout of `cache-base-url-log-path-resolution`, which was marked
  `assumption_state: invalid` for an unmeasured runtime premise.
