## 1. Contract Design

- [ ] 1.1 Define the public execution identity and how it appears in `exec` responses.
- [ ] 1.2 Decide how callers recover after `not_available` or transport timeout without blindly retrying side-effecting scripts.
- [ ] 1.3 Decide how the public execution identity relates to script-provided `correlation_id` and `log_offset`.

## 2. Surface Design

- [ ] 2.1 Specify the public follow-up surface for accepted-request observation or status recovery.
- [ ] 2.2 Update help and examples so callers can distinguish safe retry from recovery-oriented observation.
- [ ] 2.3 Define the operator-facing recovery workflow for ambiguous timeout cases.

## 3. Validation

- [ ] 3.1 Add or update tests for the new timeout-recovery contract.
- [ ] 3.2 Validate the new recovery workflow against the real Unity host or equivalent contract coverage.
- [ ] 3.3 Verify that the published help is sufficient for help-only discovery of the timeout-recovery workflow.
