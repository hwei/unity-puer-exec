## Context

Durable specs are updated by archiving changes, so a broken durable requirement is
normally fixed by a change that MODIFYs it. Two requirements in
`openspec/specs/repository-governance/spec.md` are pointer requirements — each delegates
to a canonical requirement in another durable spec and says it adds no additional
constraints — and both fail the validator:

```
ERROR requirements.4.scenarios   Requirement must have at least one scenario
ERROR requirements.10.scenarios  Requirement must have at least one scenario
WARNING requirements[4]   "Apply-closeout findings require human discussion before promotion" should contain SHALL or MUST
WARNING requirements[10]  "Superseded changes are archived rather than deleted" should contain SHALL or MUST
```

Every other durable requirement (291 of 293) already has a scenario and a normative
keyword, so this is a two-requirement shape problem, not a systemic one.

## Goals / Non-Goals

**Goals:**

- Make the two requirements verifiable (a normative keyword and at least one scenario)
  while keeping their role as governance-level restatements of a canonical rule.
- Make this class of drift fail the default unit suite rather than sit as a validator
  warning.

**Non-Goals:**

- No reorganization of the durable specs, no new governance rules, and no change to the
  canonical requirements the two pointers restate.
- No product, package, or CLI change.

## Decisions

### Decision 1: Keep the pointers, give them normative shape

Deleting the two requirements would drop governance-level rules (closeout findings need
human disposition; superseded changes are archived not deleted) from the governance spec
that the repository tells contributors to trust, and would leave the cross-references as
the only record. Instead each requirement gains a `SHALL`/`MUST` sentence and scenarios
that restate the canonical rule, with the pointer to the canonical requirement kept so the
two do not diverge.

The wording deliberately adds no constraint beyond the canonical spec: the scenario is an
illustration of a rule that already exists elsewhere, which is what a pointer requirement
is for. This satisfies the validator without creating a second source of truth that could
drift.

### Decision 2: A pure-Python structural guard, not a CLI shell-out

The regression to prevent is structural: a durable requirement that has no scenario or no
normative keyword. The `openspec` CLI validates this, but it is not guaranteed to be on
PATH in the default CI workflow (the unit workflow installs Python only), and a test that
shells a missing tool would either fail spuriously or need a skip that makes it useless.

So the guard is a small pure-Python test over `openspec/specs/**/spec.md` that asserts, per
requirement, at least one `#### Scenario:` and a `SHALL`/`MUST`. It intentionally mirrors
only those two stable structural rules rather than re-implementing the validator; the CLI
remains the authority for everything else, and the run docs say so.

## Risks / Trade-offs

**[The guard drifts from the real validator]** → It checks only two rules that have been
stable and that the validator reports as errors/warnings today. If OpenSpec changes them,
the guard is updated; it does not attempt full validation, so it cannot silently accept
something the CLI rejects beyond those two rules.

**[The guard blocks a legitimate requirement with no scenario]** → If a future requirement
genuinely cannot carry a scenario, the fix is to shape it like these two (a normative
sentence plus an illustrating scenario) or to adjust the guard deliberately. Failing the
unit suite is the intended prompt to make that choice consciously.

## Migration Plan

1. Apply the `repository-governance` MODIFIED delta (two requirements) via this change.
2. Add `tests/test_openspec_spec_hygiene.py` and register it in the default suite and the
   run docs.
3. Confirm `openspec validate --all` reports no failed durable spec and the mock suite
   passes; archive the change.

Rollback: revert the delta and drop the test; the durable spec returns to its prior shape.
