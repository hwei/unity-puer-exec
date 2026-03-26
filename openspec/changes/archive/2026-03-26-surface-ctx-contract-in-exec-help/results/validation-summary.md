## Summary

This change surfaced the exec script-context contract on the first-pass Quick Start path rather than leaving it only in `exec --help-args`. The new Quick Start line now says that only `ctx.request_id` and `ctx.globals` are guaranteed, and it points directly to both `exec --help-args` and `--help-example derive-project-path-from-unity-api`.

The targeted help-only Prompt B rerun moved in the intended direction. A `gpt-5.4-mini` subagent stayed inside the published help boundary, consulted the inline derivation example, derived the project root from `UnityEngine.Application.dataPath` plus `System.IO.Path.GetDirectoryName(...)`, and completed CLI-native verification without assuming undocumented ctx helpers.

## Comparison Against The 2026-03-25 Haiku Probe

- The `2026-03-25` haiku probe still assumed `ctx.getProjectRoot()`, which is the exact gap this change was opened to fix.
- The new rerun did not assume `ctx.getProjectRoot()`, `ctx.project_path`, or another undocumented ctx field.
- The rerun instead followed the published derivation path from Quick Start into `--help-example derive-project-path-from-unity-api`, so the specific script-context misunderstanding did decrease.

## Remaining Notes

- Final verification stayed inside the CLI observation surface through `wait-for-log-pattern`; there was no fallback to direct `Editor.log` inspection.
- Compile and refresh recovery still remained part of the Prompt B workflow, so the run is best classified as `recoverable` rather than `clean`.
- The user interrupted the subagent's final deletion attempt, but closeout cleanup removed the temporary Editor C# residue afterward.

## Closeout Finding Summary

No new follow-up work identified.
