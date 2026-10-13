## MODIFIED Requirements

### Requirement: Stop reports the deferred compile outcome

`stop` SHALL report the deferred compile in the `wait-for-compile` vocabulary
(`compile_settled` or `no_compile_observed`), together with the edge the compile was observed
by. A compile failure SHALL NOT make the play-mode transition itself fail. It SHALL be reported
as a non-zero `compile_errors_total`, with a follow-up to read the errors. When the compile-error
total cannot be read — for example the control endpoint resets or answers without a usable
body — `stop` SHALL omit `compile_errors_total` and SHALL include
`compile_error_total_available: false` rather than reporting a default `0`.

#### Scenario: Deferred compile fails after stop

- **WHEN** the compile cycle after `stop` reports errors
- **THEN** the command reports `play_state: "edit"`, `compile.outcome: "compile_settled"`, and a `compile_errors_total` greater than zero
- **AND** its `next_steps` include `get-compile-errors`

#### Scenario: Compile-error total cannot be read

- **WHEN** the compile cycle settles but the follow-up read of the compile-error total cannot be read (for example the control endpoint resets, or answers without a usable body)
- **THEN** the compile block omits `compile_errors_total`
- **AND** it includes `compile_error_total_available: false`
- **AND** the command does not report `compile_errors_total: 0` for that failed read
