## Context

The current published examples demonstrate `ctx.request_id`, but they do not clearly separate guaranteed fields from incidental or absent ones. Prompt B style task scripts are complex enough that an author may reasonably look for project-local context there.

## Goals / Non-Goals

**Goals:**
- Define the published `ctx` contract more explicitly.
- Show the supported path for project-local file access when a script needs host-project paths.
- Validate the effect through Prompt B.

**Non-Goals:**
- Do not promise a large or unstable `ctx` surface without implementation support.
- Do not expand this change into a general scripting API redesign.

## Decisions

### Decision: Clarify the contract before expanding it
The immediate fix should document the guaranteed `ctx` surface and point users toward Unity-native path APIs such as `Application.dataPath` when project-local file access is needed.

### Decision: Prompt B should verify the absence of bad assumptions
Acceptance should include a `gpt-5.4-mini subagent` Prompt B rerun that checks whether the authoring path still assumes `ctx.project_path` or similar unsupported fields.

## Risks / Trade-offs

- [A narrow documented contract may disappoint users who want richer context] → Acceptable for now because clarity is better than accidental, undocumented behavior.
