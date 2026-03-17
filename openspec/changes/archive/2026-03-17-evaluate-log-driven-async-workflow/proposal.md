## Why

The current formal CLI contract treats async continuation as a token-driven workflow: `exec` may return `running`, and callers then use `get-result` with a `continuation_token`. That model gives the CLI and package a structured async result surface, but it also adds command surface, token routing, session continuity plumbing, and a package-owned job protocol that users may not actually want.

An alternative model is to make long-running work log-driven instead of token-driven. In that model, `exec` starts work and the script itself emits correlation-aware result markers into the Unity log, while `wait-for-log-pattern` observes those markers and extracts their payloads. This could remove `get-result`, reduce package coupling, allow cross-session observation, and make the solution friendlier to users who want minimal third-party code or their own server implementation.

This change starts as an evaluation change because the trade-off is not settled yet. The idea may simplify the product, but it may also weaken machine-readable result guarantees if the log protocol is underspecified.

## What Changes

- Evaluate replacing token-driven async continuation with a log-driven observation workflow.
- Evaluate removing `get-result` from the formal CLI surface if log-driven observation proves sufficient.
- Evaluate whether session affinity should become a general selector/guard concept on `exec`, `wait-for-log-pattern`, and related commands instead of being tied to `get-result`.
- Evaluate a correlation-aware result-marker convention such as `<result-<random-id>>payload</result-<random-id>>`.
- Evaluate whether helper code or documented snippets are sufficient for marker generation and parsing without retaining a package-owned async job system.

## Capabilities

### Modified Capabilities
- `formal-cli-contract`: Potentially replace `exec -> get-result` continuation with `exec -> wait-for-log-pattern` observation and generalize session checks across commands.

## Impact

- Affects the durable CLI contract under `openspec/specs/formal-cli-contract/spec.md`.
- Likely affects CLI help and examples under `cli/python/help_surface.py`.
- Likely affects CLI command routing in `cli/python/unity_puer_exec.py`.
- Likely affects package HTTP surface and async job handling in `packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecServer.cs`.
- Requires comparison against current structured result guarantees, session-stale handling, and multi-job correlation behavior before implementation begins.
