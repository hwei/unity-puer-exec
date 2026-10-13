# Design

## Context

See `proposal.md` - Why. The durable apply-closeout and repository-governance specs already govern
how findings are surfaced and disposed of. What they do not govern is the basis of a proposal's own
runtime claims. This design covers only how that gap is closed in the durable spec; the upstream
finding is the invalidated `cache-base-url-log-path-resolution` premise.

## Goals / Non-Goals

**Goals:**

- Make the measured-vs-hypothesis basis of a proposal's runtime claim visible at propose time.
- Keep the rule advisory in effect: unverified hypotheses stay allowed when measurement is
  impractical.

**Non-Goals:**

- Automated enforcement or a checker that parses proposals.
- Requiring a reproducible measurement for every proposal claim.
- Changing apply-closeout or backlog behavior.

## Decisions

### Decision 1: Regulate disclosure, not evidence collection

The requirement binds the *statement* of a claim's basis, not the existence of an automated
measurement. This is what lets a hand-observed premise be recorded honestly as an unverified
hypothesis instead of being silently promoted to fact. A rule that demanded collected evidence
would be unimplementable for human observations, which is exactly the case the finding is about.

### Decision 2: Home the rule in `repository-governance`

The rule is a planning-discipline rule, not a product behavior or a backlog-triage rule. It
belongs beside the existing OpenSpec-first, retrospective-disposition, and closeout-discussion
requirements so a fresh reader finds all proposal-governance rules in one spec. No new capability
is introduced.

### Decision 3: No new tooling

The repository already validates artifacts and reviews proposals by hand. Adding a parser to
detect uncited runtime claims would be brittle and would exceed the finding's scope, so this
change records the expectation only.

## Risks / Trade-offs

**[A purely advisory rule is easy to ignore]** → The requirement is normative about disclosure, so
apply tasks still catch a misstated claim at the point where the change's own tasks require
verification; the rule shortens the feedback loop rather than adding a gate.

**[Over-broad reading could force a basis statement onto every sentence]** → The rule is scoped to
concrete runtime behaviors (counts, passes, probes), not to general rationale, mirroring the
upstream case it came from.
