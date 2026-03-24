## Why

Prompt B authoring through `exec --file` still has a sharp first-pass failure mode: if the script does not export `default function (ctx)`, the run fails with `missing_default_export`. The requirement is documented today, but the current guidance is still easy to miss in normal task flow.

## What Changes

- Improve the published `exec --file` guidance so the required module entry shape is harder to miss.
- Tighten the corresponding runtime error messaging around missing default export.
- Validate the change with a `gpt-5.4-mini subagent` Prompt B rerun that checks whether first-pass script authoring still falls into `missing_default_export`.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `agent-cli-discoverability-validation`: Prompt B validation can measure whether file-based script authoring converges with less first-pass failure.

## Impact

- Reduces avoidable first-attempt failures during file-based `exec` usage.
- Improves both human and agent usability without changing the script execution model.
- Produces Prompt B evidence about whether better guidance translates into fewer authoring mistakes.
