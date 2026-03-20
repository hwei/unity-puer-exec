## 1. Contract Definition

- [x] 1.1 Define the CLI contract for `resolve-blocker` including supported selectors, action set, and structured failure states.
- [x] 1.2 Define the expected caller flow after resolution so blocked exec requests continue through `wait-for-exec`.

## 2. Runtime Resolution

- [x] 2.1 Extend host-side blocker support with targeted cancel interaction for the two supported Windows dialogs.
- [x] 2.2 Add project-scoped runtime/CLI plumbing for `resolve-blocker`.
- [x] 2.3 Confirm successful resolution by polling for dialog disappearance with a fixed internal timeout.
- [x] 2.4 Update CLI help and exit behavior guidance for the new resolution command.

## 3. Validation

- [x] 3.1 Add unit coverage for no-blocker, multiple-blocker, and resolution-failure outcomes.
- [x] 3.2 Add or update real-host validation to resolve both supported blocker dialogs and continue observing the blocked exec flow.
- [x] 3.3 Summarize remaining unsupported actions or dialog classes before closeout.
