## 1. Problem Framing

- [x] 1.1 Record the current evidence showing where agents probe bridge shape in Prompt A and Standard Prompt C
- [x] 1.2 Identify which parts of the current help surface already imply PuerTS-style usage and which parts remain too implicit
- [x] 1.3 Record the specific bridged collection confusion case, including why C# `Array` / `List<T>` should not be treated as plain JS arrays

## 2. Guidance Options

- [x] 2.1 Compare candidate guidance improvements such as explicit PuerTS terminology, a short bridge mental-model section, stronger examples, and an official reference link
- [x] 2.2 Decide which guidance changes belong in CLI help versus which should remain external references or user-authored skills
- [x] 2.3 Decide whether the help surface should include a short warning about bridged C# array/list semantics plus the official JS-to-C# reference link

## 3. Validation Framing

- [x] 3.1 Define how future validation should measure faster bridge recognition without conflating it with compile recovery or persistence confirmation
- [x] 3.2 Record the follow-up implementation targets, if any, only after the exploration output is clear

## 4. Implementation Artifacts

- [x] 4.1 Add spec deltas for `formal-cli-contract` covering explicit PuerTS-style bridge guidance, a bridge mental model, and array/list warnings in the published help surface
- [x] 4.2 Add spec deltas for `agent-cli-discoverability-validation` covering bridge-recognition-specific validation expectations
- [x] 4.3 Update proposal/design text where needed so the change is implementation-oriented rather than exploration-only

## 5. Help Surface Implementation

- [x] 5.1 Update the CLI help surface so `exec` or top-level help explicitly names the PuerTS-style bridge model and the role of `puer.loadType(...)`
- [x] 5.2 Add a concise warning that bridged C# arrays and `List<T>` values are not plain JS arrays
- [x] 5.3 Add or revise a help example so callers can discover bridge usage through a purpose-built example path
- [x] 5.4 Add the official JS-to-C# reference link as a supplement to repository-owned help

## 6. Validation and Closeout

- [x] 6.1 Extend CLI unit coverage for the new bridge guidance in help and examples
- [x] 6.2 Run the targeted help-surface tests
- [x] 6.3 Record apply closeout findings and recommend archive readiness if implementation and validation succeed
