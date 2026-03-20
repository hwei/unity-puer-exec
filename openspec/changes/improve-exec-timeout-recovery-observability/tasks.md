## 1. Contract Design

- [x] 1.1 Define caller-owned `request_id`, including automatic CLI generation, explicit `--request-id`, and accepted-response shape.
- [x] 1.2 Define idempotent replay semantics for same-`request_id` retries, including `request_id_conflict` and normalized request-equivalence rules.
- [x] 1.3 Define the single-active-request contract, including `busy` behavior and the relationship between `request_id`, script-provided `correlation_id`, and `log_offset`.

## 2. Surface Design

- [x] 2.1 Specify `wait-for-exec --request-id ...` as the public follow-up surface for accepted-request recovery without resubmitting script content.
- [x] 2.2 Update `exec` and top-level help/examples so callers can distinguish fresh requests, idempotent replay, and recovery-oriented follow-up.
- [x] 2.3 Define the operator-facing recovery workflow for ambiguous timeout cases, including the warning against fresh-request blind retry for side-effecting scripts.
- [x] 2.4 Remove or explicitly retire spawned-job public-to-script hooks if no concrete dependency is discovered during apply.

## 3. Validation

- [x] 3.1 Add or update tests for `request_id`, idempotent replay, `busy`, `request_id_conflict`, `missing`, and `wait-for-exec`.
- [x] 3.2 Validate the new recovery workflow against the real Unity host or equivalent contract coverage.
- [x] 3.3 Verify that the published help is sufficient for help-only discovery of the timeout-recovery workflow.
