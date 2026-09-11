## 1. Retry transient launch failures

- [x] 1.1 Classify a transient cold-launch failure (`unity_start_failed`, or the launched Editor exits before ready) versus a persistent or non-launch failure
- [x] 1.2 Add a bounded retry around the project-scoped warm-up launch that re-confirms the clean boundary before each attempt and stops on success or a non-transient failure

## 2. Observability and guardrails

- [x] 2.1 Record attempt count, last launch status, and the boundary result so a flake is distinguishable from a persistent regression
- [x] 2.2 Verify non-launch failures and genuine assertion failures are never retried
- [x] 2.3 Exercise the retry against the validation host (including an intentionally contended launch) and record the evidence
