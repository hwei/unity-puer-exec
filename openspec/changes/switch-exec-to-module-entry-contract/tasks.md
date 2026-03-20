## 1. Contract And Wrapper Redesign

- [ ] 1.1 Replace the Unity-side exec wrapper so script input is validated and executed as a module-shaped default-export entry instead of an injected function-body fragment.
- [ ] 1.2 Introduce the minimal script context object with `request_id` and same-service `globals`, and remove default `host.log` / `triggerValidationCompile` exposure from the primary script contract.
- [ ] 1.3 Detect invalid module shape, missing/non-function default export, Promise return values, and non-serializable immediate results with stable machine-readable failure payloads.

## 2. CLI Surface And Guidance

- [ ] 2.1 Update `exec` help text and workflow examples to require the default-exported module entry shape and immediate-result semantics.
- [ ] 2.2 Update long-running workflow guidance so async completion is documented through `console.log` result markers plus `wait-for-result-marker`, not implicit Promise awaiting.

## 3. Validation

- [ ] 3.1 Update unit and integration-oriented tests that currently rely on fragment-style `return ...;` scripts to use the new module entry contract.
- [ ] 3.2 Add coverage for explicit failures on legacy fragment input, Promise-returning entry functions, and cross-exec `globals` visibility within one service lifetime.
- [ ] 3.3 Run the relevant Python/unit test suites and record any remaining real-host validation gap before archive readiness.
