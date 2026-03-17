## 1. Evaluate replacement semantics

- [ ] 1.1 Compare the current `exec -> get-result` workflow with a candidate `exec -> wait-for-log-pattern` workflow and record the behavioral gaps.
- [ ] 1.2 Decide whether correlation-aware log envelopes can formally replace structured continuation results for the repository's target agent workflows.
- [ ] 1.3 Decide whether session identity should become a general optional command guard instead of a `get-result`-specific continuity rule.

## 2. Prototype and evidence

- [ ] 2.1 Prototype a long-running script pattern that emits single-line JSON terminal markers with random correlation ids into the Unity log.
- [ ] 2.2 Design `exec` so it returns the observation `log_offset` needed by result-marker waiting without requiring a separate checkpoint command.
- [ ] 2.3 Design `wait-for-log-pattern` extraction, including `--extract-json-group`, so callers do not need to hand-write brittle full-JSON regexes.
- [ ] 2.4 Design `wait-for-result-marker` as the high-level alias for the single-line JSON marker workflow, including `--start-offset`.
- [ ] 2.5 Validate the candidate model against at least single-job, concurrent-job, and session-replacement scenarios.

## 3. Formalization path if accepted

- [ ] 3.1 Update the formal CLI contract change-local spec with the accepted replacement semantics.
- [ ] 3.2 Update help examples to demonstrate the recommended long-job workflow without relying on hidden package state.
- [ ] 3.3 Identify CLI, package, and test changes required to remove or retain `get-result` based on evaluation findings.
