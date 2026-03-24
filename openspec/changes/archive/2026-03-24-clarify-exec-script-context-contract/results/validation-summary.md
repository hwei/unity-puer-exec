## Summary

This change clarified the published `exec` script context contract without expanding the runtime surface. The help now states that the guaranteed initial `ctx` fields are `request_id` and `globals`, explicitly warns against assuming undocumented fields such as `ctx.project_path`, and adds a publishable example showing project-root derivation through `UnityEngine.Application.dataPath` plus `System.IO.Path.GetDirectoryName(...)`.

The targeted Prompt B rerun also moved in the intended direction. A `gpt-5.4-mini` subagent stayed inside the published help boundary, consulted the new path-derivation example, and completed the Selection/menu/GUID workflow without ever assuming `ctx.project_path`.

## Comparison Against The 2026-03-24 Operator Probe

- The earlier operator probe needed a failed write attempt that assumed `ctx.project_path` before it switched to Unity API path derivation.
- The new subagent rerun started with the published `ctx` contract, used only `ctx.request_id`, and derived the project root from `Application.dataPath` immediately.
- That means the specific script-context misunderstanding this change targeted did decrease in the new evidence.

## Remaining Friction

- Compile recovery still remains part of Prompt B. The refreshed verification attempt returned `running` with `phase = compiling`, and the workflow still depended on `wait-for-exec`.
- The first verification attempt before refresh still produced an unready selection state, so the run remained `recoverable` rather than `clean`.
- Final confirmation stayed inside the CLI surface through `wait-for-log-pattern` started from the returned checkpoint; there was no fallback to direct `Editor.log` inspection.

## Closeout Finding Summary

No new follow-up work identified.
