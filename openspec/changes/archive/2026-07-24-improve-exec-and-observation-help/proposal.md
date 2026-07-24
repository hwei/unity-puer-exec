## Why

A 2026-07-23 external agent validation session, and the follow-up interview that reconstructed it from transcript evidence, surfaced friction that help text could have removed. Three items were misattributed to missing capabilities and are addressed by `enforce-cli-version-compatibility`; what remains is genuine help-content absence, verified against current source rather than against the stale executable the agent ran.

The agent spent effort discovering by experiment that `exec` scripts cannot see the game's own JavaScript globals and modules, and eventually reached the running game by creating a shared `GameObject` sentinel that the game's main loop recognized. Help never states this boundary. It documents `ctx.globals` as "mutable same-service shared state" without saying that the exec environment is separate from the game runtime's, nor that the shared C#/Unity object graph is the supported way across.

Three smaller gaps came from the same session. Help nowhere states that a PlayMode transition is a request rather than a completed state change — the interview confirmed the transport is healthy across the transition, with `session_marker` unchanged, so this is purely a timing expectation. Help teaches `log_range.start` for `--start-offset` without distinguishing it from `log_range.end`, and the agent used `.end` — correctly, for its intent — with no documentation supporting the choice. And `--start-offset` and `--expected-session-marker` are each listed without stating that they protect against different failures, so a caller has no basis for using both.

## What Changes

- State the exec environment boundary in help: `exec` scripts run in an environment separate from the game runtime's JavaScript environment, cannot see its globals, module-level state, or singletons, and reach the running game through the shared C#/Unity object graph instead.
- Document the generic cross-environment coordination pattern that follows from that boundary: place or read shared C#/Unity state that both sides can see, and observe the outcome through log-based verification.
- State explicitly that framework-specific UI technique — widget-tree traversal, event invocation conventions, and game-specific operations — is out of scope for this CLI's help and belongs in a project-local skill, so callers know where that knowledge is expected to live.
- Document that entering or exiting PlayMode is an asynchronous request: the `exec` that sets it returns as soon as the request is issued, and readiness of game-layer systems must be established separately. Provide the generic three-stage shape (request the transition, confirm the state flipped, then wait for the specific readiness signal the task needs).
- Distinguish `log_range.start` from `log_range.end` by observation intent: `.start` when waiting for output the originating `exec` itself produced, `.end` when observing activity that follows it.
- State what `--start-offset` and `--expected-session-marker` each protect against — matching stale output from an earlier window, and observing a different Editor session — so that using both is understood as covering two distinct failures rather than as redundancy.
- Promote the existing PowerShell `$`-expansion note from `exec --help-args` into `exec --help`, so it is visible before a caller composes an inline `--code` value rather than only after opening the argument tier.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `formal-cli-contract`: adds help requirements for the exec environment boundary, the cross-environment coordination pattern, the project-local-skill scope boundary, PlayMode transition asynchrony, and log-offset selection semantics; modifies the existing PowerShell `$`-expansion help requirement so the note appears in `exec --help` rather than only in `exec --help-args`.

## Impact

- `cli/python/help_surface.py`: exec help and `--help-args` sections, `wait-for-log-pattern` help and `--help-args` sections, the `exec-and-wait-for-log-pattern` help example, and top-level workflow text.
- Possible new help example covering the PlayMode request-then-confirm shape.
- `tests/test_unity_session_cli.py`: help-rendering assertions for the new content and for the relocated PowerShell note.
- No runtime behavior, response shape, status, or exit code changes.
