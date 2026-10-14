# Design

## Context

See proposal.md - Why. Two workflows reference third-party actions: `.github/workflows/release.yml`
(`actions/checkout@v4`, `actions/setup-python@v5`) and `.github/workflows/unit-tests.yml` (same
majors). Both jobs run on `windows-latest` (GitHub-hosted, no self-hosted runners).

The durable specs do not pin action versions:

- `openspec/specs/unit-test-github-action/spec.md` constrains the test selection and runner
  prerequisites, not the action majors.
- `openspec/specs/openupm-release-pipeline/spec.md` constrains the published package contents and
  tagging, not the action majors.

## Goals / Non-Goals

**Goals:**

- Remove the Node.js 20 deprecation annotation by moving both actions onto a Node.js 24 runtime.
- Preserve the current step graph, inputs, and triggers exactly.

**Non-Goals:**

- Adopting the newest available majors (`actions/checkout@v7`, `actions/setup-python@v7`).
- Switching to immutable SHA pins for supply-chain hardening.
- Adding or changing workflow triggers (for example, adding `workflow_dispatch` to `release.yml`).
- Changing the unit-test selection or the OpenUPM publish flow.

## Decisions

### Decision 1: Pick the lowest major whose runtime is Node.js 24

`runs.using` was read per tag from each action's `action.yml`:

| Action | v4 | v5 | v6 | v7 |
| --- | --- | --- | --- | --- |
| `actions/checkout` | node20 | **node24** | node24 | node24 |
| `actions/setup-python` | node16 | node20 | **node24** | node24 |

Chosen: `actions/checkout@v5` and `actions/setup-python@v6`.

Alternatives considered:

- **Jump to the latest majors (`v7`)** - rejected. The task is to clear a runtime deprecation, and
  each additional major widens the behavioral surface to review for no runtime benefit. Both `v5`
  and `v7` run on Node.js 24.
- **SHA-pin all actions** - rejected for this change. It is a defensible hardening policy, but it is
  a repo-wide convention decision, not part of removing the warning; folding it in would obscure the
  diff.

### Decision 2: Bump both workflows in one change

The two workflows share the same two action references and produce the same annotation; splitting
them would leave half the warning in place and add ceremony without reducing risk.

## Risks / Trade-offs

**[`actions/checkout@v5` and `actions/setup-python@v6` require runner >= v2.327.1]** → The repository
uses only GitHub-hosted `windows-latest` runners, which are well above that minimum, and declares no
self-hosted runners. No mitigation needed.

**[`release.yml` only triggers on `v*` tag pushes, so its bump cannot be exercised by a normal
push]** → Verify `.github/workflows/unit-tests.yml` on the next push to `main` (it shares both
action bumps) and confirm `release.yml` on the next real release. If no release has happened by
archive time, record the unverified `release.yml` run as a `validation-gap` in closeout.
