## Purpose

Define the first-round validation protocol for testing whether an agent can discover and operate the published `unity-puer-exec` CLI surface in a real Unity Editor workflow without relying on repository-only implementation context.

## Scope

- Target surface: the published `unity-puer-exec` CLI help interface plus actual CLI execution.
- Target environment: Unity Editor workflows addressed through `--project-path`.
- Target outcome: real task completion in the validation host, not command naming alone.

## Allowed Discovery Surfaces

The validating agent may:

- run `unity-puer-exec --help`
- run `<command> --help`
- run `<command> --help-args`
- run `<command> --help-status`
- run `unity-puer-exec --help-example <example-id>`
- execute the CLI against the target Unity project
- inspect the target Unity project and other publishable runtime artifacts produced during the task
- inspect Unity plugin source if it is discoverable from the published project surface

## Disallowed Discovery Surfaces

The validating agent must not rely on:

- repository-only source under this product repository
- repository tests
- OpenSpec change artifacts as task hints
- maintainer-provided command-level guidance beyond the task prompt itself

Unity plugin source is not forbidden if the agent independently finds it through the publishable project surface, but task success must not depend on that discovery path.

## Validation Rules

1. The operator provides only the task prompt, the target project path, and the path to the CLI entry point.
2. The operator does not explain which command or flags to use.
3. The agent is free to explore the CLI through the allowed help surface and to execute commands.
4. The agent must demonstrate the requested Unity-side outcome, not merely produce a plausible command.
5. First-round tasks should avoid relying on Unity-native modal confirmation flows such as unsaved-scene dialogs.
6. Every trial must begin from the repository-owned baseline reset procedure.
7. If the run is blocked by runtime or environment issues, record the blockage rather than silently relaxing the discovery restrictions.

## First-Round Focus

The first round intentionally excludes:

- `--base-url` workflows
- deliberately constructed low-frequency exception scenarios
- full harness automation

The first round focuses on whether the current publishable help surface is enough for a moderately capable agent to become useful quickly in real Unity Editor work.

## Modal Dialog Guardrail

- Prefer tasks that operate on an explicit temporary asset path instead of the unnamed current scene.
- Prefer verification that stays inside CLI-driven execution and observation instead of editor shutdown or scene-switch workflows.
- If a Unity-native modal dialog still appears, pause the trial, record the dialog as a runtime blocker, and do not count any operator click-through as agent success.

## Cleanup Guardrail

- Every trial must record what state it leaves behind.
- Do not let one trial's temporary scene, dirty state, or open editor instance become the implicit baseline for the next trial.
- If retained evidence is needed, keep it intentionally and note it in the result record; otherwise remove temporary validation artifacts during cleanup.

## Operator Checklist

Before each trial:

- confirm the validation host project path
- confirm the CLI entry path available to the agent
- confirm the Unity host is in a known starting state for the task
- confirm no repository-only hints are placed in the prompt

After each trial:

- record the result using the standard result template
- separate CLI discoverability gaps from runtime/environment blockers
- note whether the agent needed any boundary exception to finish
