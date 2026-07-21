## ADDED Requirements

### Requirement: Failed exec responses hint at the puer. prefix for bare $typeof/$ref ReferenceErrors

When `exec` or `wait-for-exec` completes with `status = "failed"` and the `error` field is a `ReferenceError` indicating an undefined bare `$typeof` or `$ref` identifier (a script author omitted the `puer.` prefix), the response `situation` text SHALL include a hint suggesting `puer.$typeof` / `puer.$ref`. This inspection SHALL be limited to augmenting `situation` text for this specific error shape; it SHALL NOT alter `next_steps` candidate selection, and SHALL NOT inspect the script-authored `result` field. This is consistent with, and does not reverse, the existing requirement that `next_steps` candidates are determined by command and status alone.

#### Scenario: exec fails on a bare $typeof reference

- **WHEN** an `exec` script throws `ReferenceError: $typeof is not defined`
- **THEN** the response has `ok: false`, `status: "failed"`
- **AND** the `situation` text includes a hint that the script likely meant `puer.$typeof`

#### Scenario: exec fails on a bare $ref reference

- **WHEN** an `exec` script throws `ReferenceError: $ref is not defined`
- **THEN** the response has `ok: false`, `status: "failed"`
- **AND** the `situation` text includes a hint that the script likely meant `puer.$ref`

#### Scenario: wait-for-exec surfaces the same hint for a recovered failure

- **WHEN** `wait-for-exec --request-id ...` recovers a terminal `failed` response whose `error` is `ReferenceError: $typeof is not defined`
- **THEN** the `situation` text includes the same `puer.$typeof` hint as the equivalent direct `exec` failure

#### Scenario: Unrelated failures do not receive the hint

- **WHEN** an `exec` script fails with an error that does not match the bare `$typeof`/`$ref` `ReferenceError` shape (for example, a `TypeError` or an application-authored error mentioning `$typeof` in a longer message)
- **THEN** the `situation` text does not include the `puer.$typeof`/`puer.$ref` hint

#### Scenario: next_steps candidates remain unaffected

- **WHEN** the `puer.$typeof`/`puer.$ref` hint is added to `situation` for a failed response
- **THEN** the response's `next_steps` candidates are identical to what they would be for any other `("exec", "failed")` or `("wait-for-exec", "failed")` response
