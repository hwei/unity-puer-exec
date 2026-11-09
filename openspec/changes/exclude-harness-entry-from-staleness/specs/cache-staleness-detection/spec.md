# Spec Delta

## MODIFIED Requirements

### Requirement: Server tracks source file modification times

The C# execution server SHALL maintain a JsEnv-scoped mapping from every local filesystem
module successfully read by `PuerExecLoader` to the file existence and
`File.GetLastWriteTimeUtc` observed at that read. Paths SHALL be normalized absolute paths.
The mapping SHALL include entry files and transitively imported local files, SHALL exclude
virtual, HTTP/HTTPS, and resource-backed modules, and SHALL be cleared when the JsEnv is
disposed or reset.

The mapping SHALL also exclude the temporary entry modules the server writes for its own
request framing. When `--import-base-url` names a filesystem directory, the server writes
`__puer_exec_entry_<request-id>.js` into that directory and deletes the previous one, so those
files are read by the loader and would otherwise be recorded like caller modules. A module the
server generated is not a module the caller changed, and the server SHALL record its ownership
at the moment it writes the file rather than inferring it from the file name alone.

#### Scenario: Loader records an entry and transitive local module

- **WHEN** an exec entry file imports a local module and `PuerExecLoader` successfully reads both files
- **THEN** the server records a fingerprint for the normalized absolute path of each file

#### Scenario: Timestamps are cleared on JsEnv reset

- **WHEN** `ResetJsEnv()` is called through an exec-scoped reset or the `/reset-jsenv` endpoint
- **THEN** the entire local module fingerprint mapping is cleared
- **AND** the fresh JsEnv records new fingerprints as it loads modules

#### Scenario: Non-filesystem modules are not tracked

- **WHEN** `PuerExecLoader` reads a virtual, HTTP/HTTPS, or resource-backed module
- **THEN** that module is not added to the local filesystem fingerprint mapping

#### Scenario: Server-generated entry module is not tracked

- **WHEN** an exec uses a filesystem `--import-base-url`
- **AND** the server writes its own `__puer_exec_entry_<request-id>.js` into that directory
- **AND** `PuerExecLoader` reads that file
- **THEN** the server does not record a fingerprint for that path
- **AND** the next exec does not report it as a stale module

#### Scenario: Caller module in the import base directory is still tracked

- **WHEN** an exec uses a filesystem `--import-base-url`
- **AND** the caller has their own module in that same directory, including one whose name
  begins with `__puer_exec_entry_`
- **AND** `PuerExecLoader` reads that module
- **THEN** the server records a fingerprint for it exactly as for any other caller module
- **AND** a later change to it is still detected as stale
