## MODIFIED Requirements

### Requirement: Unity control service selects an available loopback port

The Unity-side project control service SHALL bind to a loopback HTTP endpoint by trying the preferred port first and then trying later ports in a bounded range when the preferred port is unavailable. The bound port SHALL be the authoritative service port for that Editor session. Rollover to a later candidate port SHALL occur whenever a bind attempt fails because the candidate port is already in use, regardless of which concrete exception type the host runtime raises for that condition (including a `SocketException` with `SocketError.AddressAlreadyInUse` under Unity's Mono runtime, as well as an `HttpListenerException`). The scan SHALL abort early only on a genuinely fatal error that is not a port-in-use condition.

#### Scenario: Preferred port is available

- **WHEN** a Unity Editor loads the package and the preferred control port is available
- **THEN** the control service binds the preferred loopback endpoint
- **AND** the health endpoint reports that selected port

#### Scenario: Preferred port is occupied

- **WHEN** a Unity Editor loads the package and another process already owns the preferred control port
- **THEN** the control service tries later loopback ports until an available port is bound or the configured range is exhausted
- **AND** it does not fail solely because the preferred port was unavailable

#### Scenario: Host runtime raises a socket-level port-in-use error

- **WHEN** a candidate port is already in use and the host runtime surfaces the conflict as a `SocketException` (Mono) rather than an `HttpListenerException`
- **THEN** the control service treats it as a port-in-use condition and continues to the next candidate port
- **AND** it does not abort the bounded scan after only the first occupied port

#### Scenario: Bounded range is exhausted

- **WHEN** every port in the bounded range is already in use
- **THEN** the control service reports a failure that reflects the full range it attempted
- **AND** the failure does not occur while later ports in the range were still untried

## ADDED Requirements

### Requirement: Control service runs only in the interactive Editor process

The Unity-side control service SHALL start only in the interactive Unity Editor process. It SHALL NOT start in non-interactive Unity subprocesses such as batch-mode asset-import workers, so that transient subprocesses never contend for or occupy the preferred control port reserved for the interactive Editor.

#### Scenario: Interactive Editor loads the package

- **WHEN** the package loads in an interactive Unity Editor process
- **THEN** the control service starts and binds a loopback endpoint

#### Scenario: Batch-mode asset-import worker loads the package

- **WHEN** the package loads in a batch-mode Unity subprocess (for example an asset-import worker)
- **THEN** the control service does not start
- **AND** the subprocess does not bind or occupy any port in the control port range
