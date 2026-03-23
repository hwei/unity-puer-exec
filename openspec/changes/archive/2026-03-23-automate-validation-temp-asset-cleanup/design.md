## Context

The immediate upstream finding came from `improve-agent-verification-closure`: the third-slice rerun reached the intended product flow for Standard Prompt C, but the host Unity project still retained validation-created assets such as `Assets/CodexValidation/AddIntsValidation.cs` and temporary scene folders after the run. That residue is not a product contract issue for `unity-puer-exec`; it is a validation-harness hygiene gap.

This change therefore belongs in workflow and harness design rather than in the product CLI contract. The validation host is external to this repository, but the repository still owns the rerun workflow, its cleanup policy, and the durable evidence written into OpenSpec result files.

## Goals / Non-Goals

**Goals:**
- Make validation cleanup harness-owned rather than subagent-owned.
- Define a stable cleanup inventory for temporary assets created by validation prompts and control probes.
- Ensure cleanup runs after validation attempts regardless of pass or fail outcome.
- Record cleanup outcome in durable validation evidence so later reviewers can see whether the host project returned to a known-clean state.

**Non-Goals:**
- Do not add new product CLI commands for deleting validation assets.
- Do not require subagents to author teardown logic as part of the measured task.
- Do not attempt to clean arbitrary user-created assets outside the repository-owned validation temp inventory.

## Decisions

### Harness owns cleanup, not the subagent

The rerun harness will perform cleanup after each validation task or rerun batch. This keeps the measured task focused on product workflow discovery rather than on whether the agent remembered to remove temporary files.

Alternative considered:
- Ask the subagent to delete its artifacts.
  Rejected because it changes the benchmark target and makes cleanup quality depend on agent behavior instead of harness guarantees.

### Cleanup inventory is explicit and path-based

The first version will clean only repository-owned temporary asset locations and naming conventions used by validation workflows, such as:
- `Assets/CodexValidation/*`
- `Assets/__codex_validation_temp/*`
- other explicitly declared validation-temp roots if later added by change-owned prompts or probes

Alternative considered:
- Generic heuristic cleanup of anything that looks temporary.
  Rejected because it increases the chance of removing unrelated host-project files.

### Cleanup uses a harness-side manifest plus verification

The harness should know both:
- static cleanup roots that are always safe to clear
- optional per-run discovered files that were explicitly created during the task

After cleanup, the harness should verify whether residue remains and write that status into the durable result record.

Alternative considered:
- Blind best-effort delete with no verification.
  Rejected because it hides partial cleanup failures and weakens later diagnosis.

### Cleanup status is durable validation evidence

Cleanup belongs in workflow governance, so the durable OpenSpec validation record should include whether cleanup succeeded, partially succeeded, or was skipped, plus a concise residue summary when anything remains.

Alternative considered:
- Keep cleanup reporting only in transient console output.
  Rejected because the repository would lose evidence about host contamination across reruns.

## Risks / Trade-offs

- [Static cleanup roots become outdated] → Keep the cleanup inventory small, explicit, and change-owned; update it when new validation prompts add new temp roots.
- [Cleanup deletes something valuable in the host project] → Restrict cleanup to repository-owned validation temp roots and require explicit additions before broadening scope.
- [Cleanup on failed runs masks useful debugging artifacts] → Record what was removed and allow temporary raw probes under `.tmp/` in the repository; do not rely on host-project residue as the durable debugging surface.
- [Partial cleanup failures are ignored] → Verify residue after cleanup and persist the outcome in validation results.
