## 1. Durable closeout governance

- [x] 1.1 Add the new `apply-closeout-review` durable spec to `openspec/specs/`.
- [x] 1.2 Update repository governance requirements to require human discussion before apply-closeout follow-up candidates are promoted into further work.
- [x] 1.3 Update `openspec/project.md` to describe apply closeout as requiring both follow-up review and commit/archive recommendations.

## 2. Agent guidance updates

- [x] 2.1 Update `AGENTS.md` to require an explicit closeout finding summary after apply work.
- [x] 2.2 Document the allowed follow-up categories: `product-improvement`, `workflow-improvement`, `tooling-improvement`, and `validation-gap`.
- [x] 2.3 Document that agents should recommend the `git commit` -> `openspec archive` -> `git commit` sequence when the change state is ready, but should not execute it without human confirmation.

## 3. Validation

- [x] 3.1 Run OpenSpec validation for the new change.
- [x] 3.2 Run `openspec validate --specs` to confirm the long-lived workflow rules remain consistent.
