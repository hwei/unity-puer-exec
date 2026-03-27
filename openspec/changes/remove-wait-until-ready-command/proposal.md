## Why

`wait-until-ready` currently occupies a top-level CLI command slot, but it no longer represents a distinct long-term capability. The main project-scoped work command, `exec --project-path`, already owns the same readiness and recovery behavior needed to prepare Unity before work. Published help already teaches callers not to treat `wait-until-ready` as the normal first step, which means the public surface still exposes a command that the product itself describes as non-default.

That mismatch makes the CLI harder to learn than necessary. Callers must choose between two commands that can both trigger readiness work, even though only one of them is the intended mainline path. In a pre-user product, keeping that redundant public entry adds maintenance and cognitive cost without preserving meaningful compatibility.

This change removes `wait-until-ready` entirely, with no compatibility alias and no migration path. Readiness and recovery remain part of the product, but they are exposed only through the primary project-scoped execution flow: `exec --project-path`, `exec --refresh-before-exec`, and `wait-for-exec`.

## What Changes

- Remove `wait-until-ready` from the formal CLI command tree.
- Remove the legacy `ensure-ready` alias instead of preserving a compatibility wrapper.
- Remove the standalone explicit-readiness contract from durable specs.
- Re-express readiness-oriented guidance through:
  - `exec --project-path` for initial project-scoped preparation and work
  - `exec --refresh-before-exec` for post-import or post-compilation recovery before the next task
  - `wait-for-exec --request-id ...` for continuing an accepted request that is still running or recovering
- Update help, examples, tests, and validation docs so the public workflow no longer branches through a separate readiness-only command.

## Scope

This change is about the public CLI surface, not the underlying Unity readiness machinery.

In scope:

- command removal
- help and example rewrites
- durable spec updates
- test updates
- validation workflow updates

Out of scope:

- redesigning the internal readiness or recovery implementation
- adding a new replacement top-level readiness command
- preserving compatibility behavior for a command that is not intended to survive

## Expected Outcome

The CLI will have a single project-scoped mainline workflow:

1. start work with `exec --project-path ...`
2. if the request is non-terminal, continue with `wait-for-exec`
3. if project changes require refresh or compile recovery, keep that recovery attached to the next `exec --refresh-before-exec`
4. use log- or marker-based observation commands only when the script's workflow calls for them

After this change, the product will no longer present a separate readiness-only top-level command that overlaps with the primary work entry.
