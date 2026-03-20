## Why

`exec` currently treats user script input as an injected async function body fragment. That contract is implicit, fragile at the wrapper boundary, and easy to misunderstand as "normal JavaScript". Now that the CLI is still unpublished, this is the right point to replace that input model with an explicit module-shaped entry contract before more workflows depend on the fragment semantics.

## What Changes

- **BREAKING** Replace `exec` script input semantics from "async function body fragment" to "module-shaped source with a required default-exported entry function".
- **BREAKING** Remove support for legacy fragment-style scripts such as bare top-level `return ...;`.
- Require the default-exported entry function to return an immediate JSON-serializable value that becomes top-level `result`.
- Fail explicitly when the default-exported entry function returns a Promise/thenable instead of an immediate value.
- Introduce a minimal script context object with `request_id` and same-service `globals`.
- Remove validation-specific and wrapper-specific default script helpers such as `host.log` and `triggerValidationCompile` from the primary public script contract.
- Update help, examples, and tests so long-running async workflows use `console.log` result markers plus `wait-for-result-marker` instead of relying on auto-awaited return values.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `formal-cli-contract`: change the `exec` script-input contract to require a module-shaped default export with synchronous immediate result semantics and updated long-running workflow guidance.

## Impact

- Affected Unity package runtime files under `packages/com.txcombo.unity-puer-exec/Editor/`, especially wrapper construction and script execution entry handling.
- Affected CLI help and examples under `cli/python/help_surface.py`.
- Affected tests that currently assume fragment-style `return ...;` inputs.
- Affected validation guidance for long-running workflows and script-authored result markers.
