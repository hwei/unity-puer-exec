# Tasks

## 1. Governance delta review

- [ ] 1.1 Confirm the delta adds exactly one requirement to `repository-governance` and that no existing requirement already states the rule. Verify: read `openspec/specs/repository-governance/spec.md` and the delta under `specs/repository-governance/spec.md`; the new requirement is `ADDED`, not a duplicate of the OpenSpec-first, retrospective-disposition, or closeout-discussion requirements.
- [ ] 1.2 Confirm the requirement is advisory in effect as designed: it binds the disclosure of a claim's basis (`measured` vs `unverified hypothesis`) and permits an uncollected observation to be recorded as a hypothesis. Verify: read the delta against design Decision 1; both scenarios (measured claim, uncollected observation) are present and the second routes verification into apply tasks.

## 2. Validation

- [ ] 2.1 Run `openspec validate record-runtime-claim-basis-in-proposals --strict` and `openspec validate --all`. Verify: both report clean.
- [ ] 2.2 Confirm the change touches no product, CLI, or test code. Verify: `git status` shows only artifacts under `openspec/changes/record-runtime-claim-basis-in-proposals/`.

## 3. Closeout

- [ ] 3.1 Complete the required apply closeout review and record the finding with allowed categories.

## Workflow follow-up

- Archive the change after review so the durable requirement lands in `openspec/specs/repository-governance/spec.md`.
- Verify the archived main spec contains the new requirement and that the delta directory is gone.
