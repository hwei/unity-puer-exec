## 1. Disconnect Semantics

- [ ] 1.1 Identify the accepted-request transport paths that currently emit noisy disconnect exceptions when the original client stops waiting.
- [ ] 1.2 Implement a graceful close or suppressed-noise path for recoverable accepted requests whose first response channel has ended.

## 2. Validation

- [ ] 2.1 Add targeted validation for the "initial wait ends, same request later recovers successfully" path.
- [ ] 2.2 Confirm that genuine transport failures still surface as actionable diagnostics after the graceful-disconnect change.
