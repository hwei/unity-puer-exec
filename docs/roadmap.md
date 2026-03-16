# Roadmap

## Rules

- Task IDs are hierarchical and stable, for example `T1`, `T1.2`, `T1.2.1`.
- `T` means `Task`.
- Dots indicate hierarchy only.
- Parent tasks are summary nodes by default.
- A child task belongs to exactly one parent task.
- A parent task is complete only when all direct child tasks that are not `draft` and not `dropped` are `done`.
- Same-level sibling tasks are linearly ordered by default. Higher same-level IDs depend on lower same-level IDs unless explicitly stated otherwise.
- Required task fields are:
  - `Status`
  - `Parent`
  - `Depends on`
  - `Plan`
  - `Done means`
- Supported task states are:
  - `draft`
  - `planning`
  - `ready`
  - `in_progress`
  - `blocked`
  - `done`
  - `dropped`
- `draft` means the issue is recorded but the scope is not stable yet.
- `planning` means the task has been accepted for further work and discussion or plan writing is underway.
- `ready` means the task has a confirmed plan and can begin implementation.
- `in_progress` means implementation is underway.
- `blocked` means the task cannot currently complete.
- `done` means implementation, validation, and distillation are complete.
- `dropped` means the task is explicitly not being pursued.
- `draft` tasks do not count toward parent completion.
- `docs/roadmap.md` is a live planning document, not a historical ledger.
- `done` and `dropped` tasks may be removed after their stable conclusions have been distilled into long-lived documentation or source comments.

## Active Work

## T1 Productize Unity Package And CLI

- Status: planning
- Parent: none
- Depends on: none
- Plan: none
- Done means: `unity-puer-exec` ships as a formal Unity package plus a formal CLI, with skill docs no longer acting as the primary product surface

### T1.1 Define Product Boundary And Naming

- Status: done
- Parent: T1
- Depends on: none
- Plan: none
- Done means: the formal product boundary is documented, including the Unity package name, CLI name, repo responsibilities, and the validation host's remaining role
- Output: docs/decisions/0004-product-boundary-and-naming.md

#### T1.1.1 Define Validation Host Operating Model

- Status: done
- Parent: T1.1
- Depends on: none
- Plan: none
- Done means: the validation host's operating model is documented, including the baseline branch expectation, the rule that product code lives outside the host, and how local-only test injection works without turning host-local changes into product commits
- Output: docs/decisions/0003-validation-host-operating-model.md

### T1.2 Migrate Unity Package Out Of Validation Host

- Status: planning
- Parent: T1
- Depends on: T1.1 T1.1.1
- Plan: none
- Done means: the Unity-side package currently living in the validation host is moved into this repository, renamed away from the validation-only identity, and consumed by the validation host as an external package instead of host-carried source

#### T1.2.1 Create Formal Package Home In `unity-puer-exec`

- Status: done
- Parent: T1.2
- Depends on: T1.1 T1.1.1
- Plan: none
- Done means: a formal Unity package home exists in `unity-puer-exec/`, with package metadata, assembly identity, and namespaces moved away from the validation-only identity while preserving the current Unity-side capability baseline
- Output: packages/com.txcombo.unity-puer-exec/

#### T1.2.2 Rewire Validation Host To Consume Local Package

- Status: planning
- Parent: T1.2
- Depends on: T1.2.1
- Plan: none
- Done means: the validation host no longer carries the Unity package source as committed host-local product code, consumes the migrated local package through the operating model defined for host validation, and has a minimal host-side validation path for that wiring

##### T1.2.2.1 Rewire Validation Host Manifest To Local Package

- Status: done
- Parent: T1.2.2
- Depends on: T1.2.1
- Plan: none
- Done means: the validation host operating model clearly specifies a clean host baseline from the `unity-puer-exec` fork point and a local-only `manifest.json` injection path that points at `unity-puer-exec/packages/com.txcombo.unity-puer-exec/`, with the resulting workflow documented clearly enough for repeatable local use
- Output: docs/decisions/0005-validation-host-local-package-injection.md

##### T1.2.2.2 Run Minimal Host Validation Against Local Package

- Status: done
- Parent: T1.2.2
- Depends on: T1.2.2.1
- Plan: none
- Done means: the validation host can import the rewired local package and pass at least one minimal runtime validation path that proves the host is consuming the formal package instead of a host-carried source copy
- Output: docs/decisions/0006-minimal-host-validation-proof.md

### T1.3 Formalize Unity Package Structure

- Status: draft
- Parent: T1
- Depends on: T1.2
- Plan: none
- Done means: the Unity package has production-facing assembly layout, namespaces, metadata, and documentation suitable for distribution instead of host-local validation use

### T1.4 Formalize CLI As Primary Product Surface

- Status: planning
- Parent: T1
- Depends on: T1.1
- Plan: none
- Done means: the repository has a formal, product-owned CLI baseline with stable commands, machine-usable output, and complete `--help`, and repository docs treat the CLI as the authoritative usage contract instead of the current skill-specific entry

#### T1.4.1 Define Formal CLI Contract And Command Tree

- Status: done
- Parent: T1.4
- Depends on: T1.1
- Plan: none
- Done means: the formal CLI command tree, command roles, output contract, and baseline exit-code model are documented independently of any specific implementation language or packaging choice
- Output: docs/decisions/0007-formal-cli-contract.md

##### T1.4.1.1 Revise CLI Session Discovery And Lifecycle Contract

- Status: done
- Parent: T1.4.1
- Depends on: T1.4.1
- Plan: none
- Done means: the formal CLI contract is revised so session endpoint discovery, Unity launch responsibility, and command lifecycle behavior are explicit enough to guide `T1.4.2` without preserving the current `--base-url` and `--keep-unity` assumptions by accident
- Output: docs/decisions/0007-formal-cli-contract.md

##### T1.4.1.2 Explore Session-Aware CLI Contract

- Status: draft
- Parent: T1.4.1
- Depends on: T1.4.1.1
- Plan: none
- Done means: the roadmap records follow-up work to explore whether the CLI should grow an explicit user-visible session identity model for observation and other cross-call workflows beyond the internal async continuation token/session-marker model adopted in `T1.4.1.3`

##### T1.4.1.3 Revise Async Continuation Contract

- Status: done
- Parent: T1.4.1
- Depends on: T1.4.1.1
- Plan: none
- Done means: `docs/decisions/0007-formal-cli-contract.md` explicitly defines how async execution continuation proves session continuity for `exec` and `get-result`, so `session_missing` and `session_stale` are implementable without execution-time reinterpretation
- Output: docs/decisions/0007-formal-cli-contract.md

#### T1.4.2 Establish Product-Owned CLI Baseline

- Status: done
- Parent: T1.4
- Depends on: T1.4.1.1
- Plan: none
- Done means: the repository has a product-owned CLI implementation baseline outside the current skill-owned location, preserving current capability coverage without yet committing to the final packaging strategy or implementation language
- Output: cli/python/

#### T1.4.3 Implement Formal CLI Behavior Contract

- Status: done
- Parent: T1.4
- Depends on: T1.4.1.3 T1.4.2
- Plan: none
- Done means: the product-owned CLI baseline fully implements the non-help portions of `docs/decisions/0007-formal-cli-contract.md`, including selector rules, command responsibilities, machine states, stdout/stderr placement for structured payloads, and explicit exit-code behavior
- Output: cli/python/ packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecServer.cs tests/test_cli.py tests/test_unity_session_cli.py

#### T1.4.4 Implement Formal Help Surface

- Status: draft
- Parent: T1.4
- Depends on: T1.4.3
- Plan: docs/plans/T1.4.4-formal-help-surface.md
- Done means: `unity-puer-exec --help` and per-command `--help` fully implement the help contract defined in `docs/decisions/0007-formal-cli-contract.md`, so an AI agent can discover workflows, parameter rules, key machine states, and exit codes without relying on repository skill docs

#### T1.4.5 Rewrite Repository Docs To Point To The CLI

- Status: draft
- Parent: T1.4
- Depends on: T1.4.4
- Plan: none
- Done means: repository-facing usage docs point to the formal CLI contract as the primary entry surface, and skill-specific guidance no longer acts as the authoritative usage contract

#### T1.4.6 Add CLI Integration Validation

- Status: draft
- Parent: T1.4
- Depends on: T1.4.3
- Plan: none
- Done means: the repository has at least one repeatable integration validation path that runs the product-owned CLI against the validation host consuming the local `com.txcombo.unity-puer-exec` package, proving the formal CLI contract against a real Unity-side execution service instead of a fake server, including at least one direct `exec`, one `exec -> running -> get-result --continuation-token` flow, and one non-exec command such as `get-log-source` or `ensure-stopped`

### T1.5 Decide CLI Packaging Strategy

- Status: draft
- Parent: T1
- Depends on: T1.4
- Plan: none
- Done means: after the product-owned CLI baseline exists, the repository has an explicit decision for how that CLI is distributed with minimal host-environment assumptions, including whether to keep adapting the baseline or replace it with a self-contained or AOT-built executable

### T1.6 Define OpenUPM Distribution Story

- Status: draft
- Parent: T1
- Depends on: T1.3 T1.4
- Plan: none
- Done means: package publishing, versioning, installation, and compatibility expectations are documented for OpenUPM consumers

### T1.7 Define End-To-End Validation Entry

- Status: draft
- Parent: T1
- Depends on: T1.1.1 T1.2 T1.4
- Plan: none
- Done means: the repository has a normalized repo-level E2E validation entry that proves the formal package and formal CLI work together against the validation host

## T2 Improve Repository Workflow And Planning

- Status: planning
- Parent: none
- Depends on: none
- Plan: none
- Done means: repository workflow and planning rules support deterministic execution by distinguishing discussion, decision planning, implementation planning, and exploration planning

### T2.1 Tighten Planning Workflow For Decision Certainty

- Status: done
- Parent: T2
- Depends on: none
- Plan: none
- Done means: workflow and planning rules make agreed constraints explicit, require key downstream-shaping decisions to be resolved before execution planning, and allow subagent review to send work back to discussion
- Output: docs/workflow.md docs/planning.md docs/plan-template.md

### T2.2 Minimize Agent Token Cost For Documentation Workflow

- Status: dropped
- Parent: T2
- Depends on: T2.1
- Plan: docs/plans/T2.2-doc-structure-token-minimization.md
- Done means: repository documentation is reorganized so an agent can load only the minimum document slice needed for the current workflow state without changing the underlying workflow semantics

### T2.3 Clarify Governance-Plan Boundaries

- Status: done
- Parent: T2
- Depends on: T2.1
- Plan: none
- Done means: workflow and planning rules replace `Decision Plan` with `Governance Plan`, make it explicit that `Governance Plan` is for changes whose main output is project-management documentation rather than final product artifacts, and clarify when such a plan may directly modify long-lived governance documents without requiring a follow-up implementation task
- Output: docs/workflow.md docs/planning.md docs/plan-template.md

### T2.4 Minimize Agent Token Cost For Documentation Workflow Under Clarified Planning Rules

- Status: done
- Parent: T2
- Depends on: T2.3
- Plan: none
- Done means: repository documentation is reorganized so an agent can load only the minimum document slice needed for the current workflow state without changing the underlying workflow semantics
- Output: AGENTS.md docs/index.md docs/workflow.md docs/workflow-closeout.md docs/planning.md docs/planning-rules.md docs/status.md

### T2.5 Keep `ReadMe.md` User-Facing And Move Developer Guidance To `AGENTS.md`

- Status: draft
- Parent: T2
- Depends on: T2.3
- Plan: none
- Done means: `ReadMe.md` serves final users rather than repository developers, and developer guidance consistently points to `AGENTS.md` instead of treating `ReadMe.md` as the primary development entry

### T2.6 Propagate Durable Decisions Into Successor Task Descriptions

- Status: done
- Parent: T2
- Depends on: T2.1 T2.3
- Plan: none
- Done means: when a task produces a durable decision that a direct successor must follow, workflow and planning rules require the successor task's roadmap description to be updated so a fresh session can see that decision as an implementation input without reconstructing it from dependency edges alone
- Output: docs/workflow.md docs/planning.md

### T2.7 Enforce Plan-First Implementation Workflow

- Status: done
- Parent: T2
- Depends on: T2.1 T2.3 T2.4
- Plan: none
- Done means: repository entry guidance and workflow documents make the pre-implementation plan requirement explicit enough that a fresh session is unlikely to skip plan creation for substantial work, and closeout guidance clearly defines how to recover when a task was implemented before its plan existed
- Output: AGENTS.md docs/index.md docs/workflow.md docs/workflow-closeout.md
