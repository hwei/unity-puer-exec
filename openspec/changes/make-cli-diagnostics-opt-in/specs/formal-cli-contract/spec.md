## MODIFIED Requirements

### Requirement: Formal command results are machine-readable JSON

All formal command results SHALL be machine-readable JSON. Successes and expected non-success machine states that an agent can branch on MUST be emitted on stdout. Default machine payloads SHOULD remain focused on branchable contract data rather than debug-oriented diagnostics. Diagnostics that are not required for ordinary machine branching SHOULD be exposed through explicit opt-in command behavior instead of appearing by default.

#### Scenario: Caller consumes the normal machine contract

- **WHEN** a caller invokes a formal command without requesting diagnostics
- **THEN** the default payload contains the stable machine contract needed for normal branching
- **AND** debug-oriented diagnostics are not required to parse ordinary success or expected non-success states
