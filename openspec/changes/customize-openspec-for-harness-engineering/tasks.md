## 1. Durable governance updates

- [ ] 1.1 Update `openspec/project.md` to describe OpenSpec changes as the non-archived backlog surface and to reference the repository-owned change metadata convention.
- [ ] 1.2 Update durable repository governance artifacts to define discovery triage, change-type artifact policy, and superseded disposition rules.
- [ ] 1.3 Update `AGENTS.md` with the expected change metadata fields, change-state meanings, and the rule that agents should consult backlog tooling before selecting fresh work from a clean tree.

## 2. Change metadata and template support

- [ ] 2.1 Add a repository-owned `meta.yaml` template and document where it lives in each change directory.
- [ ] 2.2 Document the allowed values and semantics for `status`, `change_type`, `priority`, `blocked_by`, `assumption_state`, `evidence`, and `updated_at`.
- [ ] 2.3 Decide and implement how new changes receive `meta.yaml` with minimal manual setup.

## 3. Next-change tooling

- [ ] 3.1 Implement a repository-local tool that scans non-archived changes, reads `meta.yaml`, and filters out blocked and superseded changes.
- [ ] 3.2 Implement deterministic ranking using computable fields and derived unlock counts from `blocked_by` references.
- [ ] 3.3 Add filter views that at minimum support `status` and `change_type`, including a backlog view defined as `status=queued`.
- [ ] 3.4 Make the tool print ranking reasons so a maintainer or agent can review the ordering rather than treating it as opaque automation.

## 4. Validation and adoption

- [ ] 4.1 Add tests or fixture-based validation for metadata parsing, filtering, and ranking behavior.
- [ ] 4.2 Create or update at least one real change to use `meta.yaml` so the workflow is exercised in-repo.
- [ ] 4.3 Run OpenSpec validation and repository tests needed to show the new governance and tooling are ready to apply.
