## ADDED Requirements

### Requirement: Real-host validation covers control-port binding behavior

The repository SHALL maintain repeatable real-host validation expectations that prove the Unity control-port binding contract, covering both batch-mode service suppression and occupied-preferred-port rollover. These expectations SHALL run only under the existing opt-in real-host gate and SHALL skip cleanly when Unity, the host project, or the required process state is unavailable, so the default mocked/unit workflow is unaffected.

#### Scenario: Contributor validates that a batch-mode process suppresses the control service

- **WHEN** a contributor runs the real-host validation against a host project loaded by a batch-mode Unity process
- **THEN** the validation asserts the batch-mode process log records that the control service was skipped for a batch-mode process
- **AND** the validation asserts the batch-mode process log records no successful control-port bind and no whole-range bind failure
- **AND** the validation asserts no control-range port is held by the batch-mode process

#### Scenario: Contributor validates rollover when the preferred control port is occupied

- **WHEN** a contributor runs the real-host validation with the preferred control port already occupied at the time an interactive control service starts
- **THEN** the validation asserts the interactive control service becomes ready on a later port in the bounded range rather than failing the whole scan
- **AND** the validation asserts the ready health identity reports the later selected port and its base URL

#### Scenario: Prerequisites for binding validation are absent

- **WHEN** the real-host gate is disabled, or Unity / the host project / the required process state is unavailable
- **THEN** the binding-behavior validation skips with a machine-usable reason
- **AND** it does not report a failure that would be indistinguishable from a real binding regression
