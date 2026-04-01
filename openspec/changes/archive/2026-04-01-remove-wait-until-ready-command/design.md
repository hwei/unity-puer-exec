## Context

The CLI currently exposes both `wait-until-ready` and `exec --project-path` as public entry points that can trigger project-scoped readiness and recovery work. That split made sense earlier when readiness needed a more explicit command boundary, but the current product surface no longer treats `wait-until-ready` as the normal path. The published help already positions `exec` as the primary project-scoped command and frames `wait-until-ready` as a supporting command for special cases.

That leaves the CLI in an inconsistent state:

- the formal command tree still grants `wait-until-ready` first-class status
- the main help tells callers not to use it as the default first step
- the runtime and specs already require `exec --project-path` to share the same readiness and duplicate-launch-avoidance behavior

The issue is not that readiness became unimportant. The issue is that readiness is no longer a distinct public primitive. It is now part of the main execution lifecycle.

## Decision

Remove `wait-until-ready` entirely from the public CLI surface, with no compatibility alias and no migration phase.

Readiness and recovery remain supported, but only as part of the mainline execution model:

- `exec --project-path` is the only public project-scoped entry for initial preparation and work
- `exec --refresh-before-exec` is the public path for post-import or post-compilation recovery before the next task
- `wait-for-exec --request-id ...` is the public continuation path when an accepted request is still running or recovering

The CLI will no longer expose a separate readiness-only top-level command.

## Why

### 1. `wait-until-ready` no longer provides a distinct public capability

The command does not own unique runtime behavior. The important readiness behavior already lives in the same product contract as `exec --project-path`: prepare Unity when needed, reuse or recover project-scoped runtime when possible, and avoid duplicate launch conflicts.

A separate command boundary is only justified when it exposes a distinct composable capability. Here it mostly exposes a narrower wrapper around behavior that the main work command already owns.

### 2. Keeping it creates a larger and less coherent command surface

A top-level command slot signals "this is a primary concept the caller should learn." But the current help must repeatedly explain that callers should usually start with `exec` instead. That is a structural smell: the surface advertises one thing while the workflow guidance teaches another.

Removing the command makes the public model simpler and more honest:

- work starts with `exec`
- accepted non-terminal work continues with `wait-for-exec`
- log or marker observation remains explicit and specialized

### 3. A pre-user product should optimize for final shape, not compatibility theater

The repository does not need a deprecated alias, compatibility shim, or staged migration. Those would preserve a command that the product does not want long-term, while forcing help, tests, and examples to keep carrying an obsolete concept.

Since there is no external user base to protect, the correct move is to enforce the intended final shape immediately.

## Public Workflow After Removal

### Initial project-scoped work

Before:
- caller may choose between `wait-until-ready --project-path ...` and `exec --project-path ...`

After:
- caller starts with `exec --project-path ...`

If Unity is not ready yet, readiness and recovery happen inside the execution lifecycle instead of through a separate readiness-only step.

### Post-import or post-compilation recovery

Before:
- some workflows can branch into an explicit `wait-until-ready` step between tasks

After:
- the next task uses `exec --refresh-before-exec`
- any resulting refresh or compile recovery remains attached to that request
- the caller follows with `wait-for-exec` if the request is accepted but not yet terminal

### Ongoing or ambiguous execution state

Before:
- callers may separately reason about "make Unity ready" versus "continue the accepted request"

After:
- readiness-oriented continuation is not a separate public concept
- if a request is already accepted, the caller stays on `wait-for-exec --request-id ...`

This keeps request ownership and recovery tied to the same execution identity.

## Alternatives Considered

### Keep `wait-until-ready` and only rewrite help

Rejected.

This would reduce some wording friction but keep the structural duplication. Callers would still face two top-level commands that can both prepare Unity for project-scoped work. The help would remain compensatory instead of reflecting a clean underlying model.

### Keep `wait-until-ready` as a deprecated or hidden alias

Rejected.

This would be useful only if compatibility mattered. In a pre-user repository, it adds surface area, testing burden, and conceptual drag without preserving important value.

### Replace it with a narrower `health` or `ping` command

Rejected for this change.

A pure service-observation command is a different product question. It should not be introduced merely to justify removing a redundant readiness wrapper. If future evidence shows that callers need a zero-work direct-service probe, that can be proposed separately with a narrower and clearer contract.

## Specification Changes

The durable CLI contract will change in three ways:

1. Remove `wait-until-ready` from the authoritative flat command tree.
2. Remove the standalone requirement that defines `wait-until-ready` as the explicit readiness shortcut.
3. Strengthen the `exec` requirement so that project-scoped readiness preparation is defined as part of the public execution entry, not as a separate top-level command.

The resulting formal model is:

- `exec` is the only public project-scoped entry for preparation plus work
- `wait-for-exec` is the continuation path for accepted non-terminal execution
- other observation or troubleshooting commands remain specialized and explicit

## Implementation Notes

This change should remove the command completely rather than leaving dead or hidden public paths behind.

Expected implementation work includes:

- remove parser registration and runtime dispatch for `wait-until-ready`
- remove `ensure-ready`
- remove related help pages, help-status pages, and top-level help mentions
- update examples and transcripts that currently instruct a readiness-only step
- replace tests that assert parser, help, or payload behavior for the removed command
- update real-host validation guidance so the mainline path starts from `exec`

## Risks

### Risk: some internal validation flows still depend on `wait-until-ready`

This is likely, because tests, examples, and real-host docs currently mention it.

Mitigation:
Treat those references as part of the removal scope rather than as compatibility constraints. The product should have one project-scoped mainline workflow after the change, so validation assets should be rewritten to match that final shape.

### Risk: callers lose an explicit "ready-only" action

This is a real removal, not a rename. That capability disappears from the public surface.

Mitigation:
Accept the loss unless evidence shows that "ready-only with no work" is a necessary long-term primitive. Current repository guidance does not justify keeping a full top-level command for that purpose.

### Risk: `exec` help becomes too overloaded

Removing `wait-until-ready` puts more explanatory responsibility on `exec`.

Mitigation:
Keep the public story strict and short:
- `exec --project-path` starts work and may prepare Unity
- `exec --refresh-before-exec` is for the next task after import/compile-triggering changes
- `wait-for-exec` continues accepted non-terminal requests

Do not recreate a readiness sub-language inside help text.
