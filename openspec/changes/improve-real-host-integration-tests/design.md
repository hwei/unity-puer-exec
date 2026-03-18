## Context

The repository already has good Python-level coverage for CLI parsing, payload shaping, exit-code mapping, and session/log-source rules. That coverage does not exercise the riskiest integration boundaries: launching or recovering a real Unity editor, talking to the host service over HTTP, reading the real Editor log, and proving that returned observation checkpoints work against the same log stream.

Recent manual validation against `c3-client-tree2/Project` showed these workflows can be proven in practice, but those checks are not yet packaged as a repeatable regression path. The design goal is to preserve the external-host boundary while making the critical happy-path integrations cheap enough to rerun when CLI behavior changes.

## Goals / Non-Goals

**Goals:**
- add a repository-owned real-host regression workflow that can be rerun against `UNITY_PROJECT_PATH`
- cover the highest-value CLI chain: host preparation, readiness, `exec --include-log-offset`, `wait-for-result-marker`, and `wait-for-log-pattern --extract-json-group`
- keep this workflow clearly distinct from mocked unit/contract tests and from one-off manual probes
- make failures isolate whether the break is in host preparation, readiness, transport, or log observation

**Non-Goals:**
- replacing the existing mocked Python tests
- turning every CLI command or every negative path into real-host automation
- moving the validation host into this repository or treating its source tree as product-owned
- changing the formal CLI contract in this change beyond validation expectations

## Decisions

### Add a dedicated opt-in real-host regression suite

Decision:
- Add a small repository-owned integration entry point under `tests/` that runs only when a usable validation host path is available.

Rationale:
- The existing suite stays fast and hermetic.
- Real-host coverage becomes discoverable and repeatable instead of living in session notes.

Alternatives considered:
- Expand the default unit test suite to always drive Unity.
  Rejected because it would make routine test runs slow and environment-dependent.
- Keep using ad hoc shell transcripts only.
  Rejected because regressions at the Unity/log boundary are exactly the failures that need repeatable execution.

### Test the critical observation chain end to end

Decision:
- The first regression scope should prove one project-scoped chain end to end: prepare host, wait until ready, execute a script that emits a correlation-aware result marker, then verify both `wait-for-result-marker` and `wait-for-log-pattern --extract-json-group` from the returned `log_offset`.

Rationale:
- This chain spans the highest-risk cross-process boundaries and directly exercises the contract that has changed most recently.
- It gives better value than broad but shallow coverage across many commands.

Alternatives considered:
- Focus only on `wait-until-ready`.
  Rejected because startup alone does not prove the observation contract.
- Focus only on low-level package tests.
  Rejected because the CLI-to-host-to-log integration is the unstable boundary.

### Keep host preparation explicit and repository-owned

Decision:
- Reuse the existing manifest wiring helper and make the real-host workflow call repository-owned preparation steps before asserting runtime behavior.

Rationale:
- This matches the existing `validation-host-integration` contract and keeps wiring proof separate from runtime proof.
- Contributors can rerun the same setup path locally without inventing side procedures.

Alternatives considered:
- Assume the host is already prepared.
  Rejected because that makes failures ambiguous and weakens reproducibility.

## Risks / Trade-offs

- [Environment fragility] -> Keep the suite opt-in and gate it on explicit host availability instead of making all test runs depend on Unity.
- [Slow runtime] -> Cover only the highest-value end-to-end flows first and leave broad expansion for later changes.
- [Host state drift] -> Run repository-owned preparation before validation and keep the host contract external but deterministic.
- [False confidence from a single happy path] -> Make the initial suite intentionally small but ensure it proves both high-level and low-level observation commands.
