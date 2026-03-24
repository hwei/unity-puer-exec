## Why

The existing editor-interaction validation scenario around Selection, menu execution, and GUID logging is still valuable because it exercises a realistic but fragile Unity Editor workflow. At the same time, the latest evidence suggests that this scenario currently mixes editor-timing traps with broader CLI workflow questions, so it should be preserved as a deferred validation track rather than as the main proof point for core agent workflow quality.

## What Changes

- Preserve a dedicated follow-up change for revalidating fragile editor-interaction workflows after the current core workflow issues are better understood.
- Record that this track depends on earlier clarification of verification closure and agent-facing log-observation guidance.
- Keep the scope focused on future validation design, not immediate implementation.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `agent-cli-discoverability-validation`: the repository may keep fragile editor-interaction scenarios as a deferred validation track distinct from the core baseline workflows.

## Impact

- Affects the future validation roadmap and how fragile Unity Editor interaction scenarios are staged.
- Preserves the Selection/menu workflow as an intentional later-stage validation target instead of dropping it.
- This change is deliberately blocked on earlier exploration and should remain deferred for now.
