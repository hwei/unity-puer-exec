## Summary

The deferred editor-interaction track remains worth preserving, but the latest repository-side probe changes how it should be framed. The current CLI can complete the Prompt B style Selection/menu/GUID workflow through a fully CLI-native path: write the editor script, recover after compile, invoke the menu command, and confirm the emitted GUID through `wait-for-log-pattern` started from the returned `log_offset`.

That means this scenario no longer proves that the CLI lacks a viable verification path. It now behaves more like a harder comparison track whose remaining friction comes from editor-interaction timing and script-authoring ergonomics rather than from a total absence of CLI-native verification.

## Comparison Against Earlier Prompt B Evidence

- `2026-03-23` current baseline: Prompt B still succeeded, but final confirmation escaped to direct `Editor.log` inspection and the whole run remained clearly `recoverable`.
- `2026-03-24` log-workflow rerun: a clean help-only subagent already showed that Prompt B could stay inside `exec` plus `wait-for-log-pattern` when it consulted the new ordinary log-workflow example.
- `2026-03-24` operator probe in this change: the same task still works through the CLI-native checkpointed path, which confirms that the no-host-log result is not isolated to one archived rerun.

## Remaining Product-Facing Friction

- The workflow name `exec-and-wait-for-log-pattern` appears in top-level help as a common workflow, but it is not an executable subcommand. Users must discover that it is a `--help-example` target instead.
- File-based `exec` scripts still have an easy first-pass failure mode if the author misses the required `export default function (ctx) { ... }` entry shape.
- The observed `ctx` contract was narrower than a task author might assume. In this probe it exposed `request_id` and `globals`, but not `project_path`, which forced the script to derive host file paths through Unity APIs.
- Editor compile recovery still remains part of the task because importing the generated script required `wait-until-ready` before the menu invocation step.

## Decision

Keep `revalidate-editor-interaction-workflows` as a deferred validation track, not as the mainline baseline. The new evidence says the CLI can close this workflow natively, but the scenario still mixes:

- editor compile and selection timing
- script-authoring and script-context discoverability
- ordinary log-observation workflow guidance

Those concerns should stay separated from the cleaner Prompt A and Standard Prompt C baseline tracks.

## Future Rerun Checkpoints

Run the deferred editor-interaction comparison again only when all of the following are true:

- Prompt A and Standard Prompt C are stable enough that verification-closure regressions are no longer the main open question.
- The ordinary log-observation guidance still points agents toward `exec` plus `wait-for-log-pattern` with explicit checkpoint capture.
- The rerun protocol explicitly names a deterministic selected asset, cleanup expectations, and how compile recovery is scored so reviewers do not mistake harness ambiguity for product behavior.

## Prompt Wording Decision

Reuse the existing Prompt B wording when the goal is historical comparison against archived Prompt B evidence. If the repository later wants a cleaner or narrower editor-interaction task, add it as a new named prompt instead of rewriting Prompt B in place.
