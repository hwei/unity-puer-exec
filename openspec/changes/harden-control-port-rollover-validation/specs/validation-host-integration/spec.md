## MODIFIED Requirements

### Requirement: Real-host validation covers control-port binding behavior

The repository SHALL maintain repeatable real-host validation expectations that prove the Unity control-port binding contract, covering the uniform activation rule in batch mode (both with and without activation requested) and occupied-preferred-port rollover. These expectations SHALL run only under the existing opt-in real-host gate and SHALL skip cleanly when Unity, the host project, or the required process state is unavailable, so the default mocked/unit workflow is unaffected.

A process state that an expectation exists to exercise SHALL NOT be treated as a missing prerequisite. In particular, a control port already occupied by another project's Editor is the precondition of the occupied-preferred-port rollover expectation, so that condition SHALL cause the expectation to run, and SHALL NOT cause it to skip. Skipping SHALL be reserved for conditions under which the expectation cannot be evaluated at all — the gate being disabled, Unity or the host project being absent, the host project being unserviceable, or a required trigger that cannot be staged for reasons outside the suite's control. When an expectation is only partially stageable, the suite SHALL assert the part it can observe and state which part it could not stage, rather than skipping or reporting a pass for the whole expectation.

#### Scenario: Contributor validates that a batch-mode process without activation does not start the control service

- **WHEN** a contributor runs the real-host validation against a host project loaded by a batch-mode Unity process launched without activation requested
- **THEN** the validation asserts the batch-mode process log records that the control service was not activated for that process
- **AND** the validation asserts the batch-mode process log records no successful control-port bind and no whole-range bind failure

#### Scenario: Contributor validates that a batch-mode process with activation starts the control service

- **WHEN** a contributor runs the real-host validation against a host project loaded by a batch-mode Unity process launched with activation requested
- **THEN** the validation asserts the batch-mode process log records a successful control-port bind
- **AND** the validation asserts the batch-mode process log does not record that the control service was not activated

#### Scenario: Contributor validates rollover when the preferred control port is occupied

- **WHEN** a contributor runs the real-host validation with the preferred control port already occupied at the time an interactive control service starts
- **THEN** the validation asserts the interactive control service becomes ready on a later port in the bounded range rather than failing the whole scan
- **AND** the validation asserts the ready health identity reports the later selected port and its base URL

#### Scenario: Another Editor already occupies the preferred control port

- **WHEN** the real-host validation runs while another project's ready Editor already occupies the preferred control port
- **THEN** the occupied-preferred-port rollover expectation still runs and asserts that the host project's service is ready on a later port in the bounded range
- **AND** it asserts that a project-scoped command with no explicit base URL discovers that later-port endpoint
- **AND** it does not skip, and does not report a pass for any assertion it did not evaluate

#### Scenario: A reload-staging sub-assertion cannot be staged

- **WHEN** the real-host validation cannot stage the mid-reload rebind race because the preferred port is already held by something the suite cannot displace
- **THEN** the expectation still asserts the rollover behavior it can observe
- **AND** it records that the mid-reload rebind sub-assertion was not staged, distinguishing "not evaluated" from "passed"

#### Scenario: The suite cannot observe the host's own ready endpoint after a bound launch

- **WHEN** the real-host validation has launched or recovered the host project successfully
- **AND** the suite's own endpoint oracle then cannot find a ready endpoint owned by that project anywhere in the bounded control-port range, after bounded retries
- **THEN** the case fails rather than skipping
- **AND** the failure reports the bound launch outcome and the ports probed, so an endpoint-discovery regression is not reported as a missing prerequisite

#### Scenario: Prerequisites for binding validation are absent

- **WHEN** the real-host gate is disabled, or Unity / the host project / the required process state is unavailable
- **THEN** the binding-behavior validation skips with a machine-usable reason
- **AND** it does not report a failure that would be indistinguishable from a real binding regression
