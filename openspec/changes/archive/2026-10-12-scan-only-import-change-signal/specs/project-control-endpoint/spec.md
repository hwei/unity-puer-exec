## REMOVED Requirements

### Requirement: Health response exposes whether a code change is pending refresh

**Reason**: The requirement named `unknown` as a legitimate pending state, caused by a
watcher error or a domain reload that reset watcher state. With the watcher removed there
is no invalidation source and no in-memory event state to reset, so a ready service always
has a definite answer. Keeping an unreachable degraded state in the contract would
describe a system that does not exist.

**Migration**: Replaced by the ADDED requirement below. A caller that treated `unknown`
as "probe again later" needs no special handling: the two live states (`pending`,
`not_pending`) are the same field with the same names, and callers that only distinguish
"refresh will happen" from "no refresh needed" are unaffected.

## ADDED Requirements

### Requirement: Health response exposes the pending refresh state

The Unity-side health endpoint SHALL report whether the control service currently
considers a compile-triggering change pending, so that a caller observing an Editor can
distinguish "no refresh needed" from "refresh will happen on the next exec" without
triggering an exec. The field SHALL be present on ready health responses. Because the
pending state is computed from the filesystem on each probe rather than from in-memory
event state, a ready service always has a definite answer: `pending` or `not_pending`.

#### Scenario: Caller probes health with no pending change

- **WHEN** a caller probes `/health` on a ready service
- **AND** no compile-triggering change is pending
- **THEN** the health response reports that no refresh is pending

#### Scenario: Caller probes health with a pending change

- **WHEN** a caller probes `/health` on a ready service
- **AND** a compile-triggering change is pending but not yet refreshed
- **THEN** the health response reports that a refresh is pending
