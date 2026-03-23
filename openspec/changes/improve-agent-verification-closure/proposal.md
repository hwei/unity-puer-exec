## Why

Archived and current agent-validation evidence now agrees on one narrow product gap: the CLI can get a medium-capability agent to eventual success on the basic workflows, but it still does not consistently keep verification inside a clean, machine-usable CLI path. Prompt A still needed host-asset confirmation after startup and bridge-shape friction. The former Prompt B evidence is no longer the right primary baseline for this change because it mixes basic compile verification with Unity Editor interaction timing and log-observation behavior.

A direct manual control probe also showed that a simpler workflow already behaves better than the old Prompt B evidence suggested: writing a minimal C# static method and then immediately issuing a second `exec` to call that method succeeds without an explicit `wait-until-ready` between the two requests. That means the mainline verification-closure change should focus on Prompt A plus a new, cleaner basic compile-and-call validation track, while editor-interaction and log-observation follow-ups proceed separately.

## What Changes

- Improve the formal CLI verification workflow so agents can confirm basic workflow outcomes without leaving the intended CLI observation surface.
- Define the product-facing contract for verification-oriented follow-up after project-scoped `exec`, especially for slow startup acceptance and for basic C# write-compile-call verification.
- Evaluate Prompt A and a new basic C# compile-and-call track as separate acceptance tracks while keeping editor-interaction and log-observation issues out of the mainline baseline.
- Update validation guidance and representative evidence so future agent-evaluation rounds can distinguish clean CLI verification from host-side fallback confirmation.
- Sequence the work so Prompt A startup continuity is the first implementation slice, then add a second compile-recovery slice for Standard Prompt C so project-scoped `exec` can optionally refresh and wait through script compilation before executing the next verification step.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `formal-cli-contract`: basic project-scoped verification workflows should provide a cleaner CLI-native confirmation path after `exec`.
- `agent-cli-discoverability-validation`: baseline agent validation should explicitly distinguish clean CLI verification from host-side fallback confirmation and track Prompt A plus a cleaner basic C# compile-and-call workflow separately.

## Impact

- Affects CLI contract and help around post-`exec` verification workflows.
- Affects validation interpretation for whether a basic workflow stayed inside the intended CLI observation surface.
- Defers log-observation guidance and editor-interaction timing cases to linked follow-up changes instead of treating them as the mainline baseline here.
- Narrows each implementation slice to one concrete workflow problem at a time: first project-scoped startup continuity, then compile recovery before the next `exec`.
