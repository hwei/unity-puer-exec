## Why

The exploratory change `improve-agent-log-observation-guidance` concluded that ordinary log-pattern verification is the leading guidance gap: agents can find `wait-for-log-pattern`, but the published help surface still gives them only one first-class long-workflow example, `exec-and-wait-for-result-marker`. As a result, agents must compose the ordinary log-verification path themselves and may still fall back to direct `Editor.log` inspection under task pressure.

## What Changes

- Add a first-class published workflow example for ordinary log-oriented verification, parallel to the existing result-marker example.
- Teach that ordinary log verification should capture an observation checkpoint from `exec` and then start `wait-for-log-pattern` from the returned `log_offset`.
- Add minimal supporting help text so the ordinary log example is discoverable from the same surfaces that already point agents toward result-marker workflows.
- Revalidate the relevant help-only baseline workflow to measure whether the new example reduces host-log fallback before considering a contract change such as default `log_offset`.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `formal-cli-contract`: help and examples should expose a first-class ordinary log-pattern workflow alongside the result-marker workflow.
- `agent-cli-discoverability-validation`: validation should explicitly measure whether the ordinary log workflow example reduces host-log fallback in the representative log-verification baseline.

## Impact

- Affects the published CLI help and `--help-example` workflow surface.
- Affects tests that cover help rendering and example discoverability.
- Affects validation evidence for Prompt B style log-verification tasks.
