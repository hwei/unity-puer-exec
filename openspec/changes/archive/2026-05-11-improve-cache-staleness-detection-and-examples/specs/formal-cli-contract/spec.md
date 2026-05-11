## ADDED Requirements

### Requirement: Exec reports module_cache_stale when file mtime has changed

The formal CLI SHALL expose `module_cache_stale` as a documented non-success status for `exec`. This status indicates the source file has been modified since its last execution but the PuerTS module cache still holds the old compiled version. The CLI SHALL provide a `situation` explanation and `next_steps` candidates including a concrete `argv` for re-running with `--reset-jsenv-before-exec`.

#### Scenario: Agent receives module_cache_stale from exec

- **WHEN** `exec --file` is invoked and the source file's mtime has changed since its previous successful execution
- **THEN** the response has `status = "module_cache_stale"`
- **AND** `ok` is `false`
- **AND** the response includes `situation` explaining the staleness condition
- **AND** the response includes `next_steps` with a candidate carrying `--reset-jsenv-before-exec`

#### Scenario: module_cache_stale appears in --help-status

- **WHEN** an agent invokes `unity-puer-exec exec --help-status`
- **THEN** `module_cache_stale` is listed as a non-success status with its exit code and situation explanation

### Requirement: Help includes a component-detection example

The formal CLI help surface SHALL include a `--help-example` entry for component detection that demonstrates the standard PuerTS pattern for scene-inspection scripts: using `puer.$typeof(CS.UnityEngine.X)` for type resolution, `puer.$ref()` for out-parameter references, `TryGetComponent` for component probing, and `get_Item()` for C# indexer access.

#### Scenario: Agent discovers the component-detection example

- **WHEN** an agent invokes `unity-puer-exec --help-example component-detection`
- **THEN** the output includes a complete script body demonstrating `puer.$typeof(CS.UnityEngine.MeshFilter)`, `puer.$ref()`, `TryGetComponent`, and `get_Item()`
- **AND** the example notice text explains that `puer.$typeof(CS.XXX)` is more reliable than `puer.loadType` for component types
- **AND** the notice text explains that C# indexers require `get_Item()` syntax

### Requirement: --code help warns about PowerShell $ expansion

The `--code` argument help text SHALL include a note that PowerShell users should use single quotes (`'...'`) when the code contains `$` characters (such as `$typeof`), or use `--file` as an alternative.

#### Scenario: Agent reads --code help on PowerShell

- **WHEN** an agent reads `unity-puer-exec exec --help-args` on a Windows/PowerShell system
- **THEN** the argument help for `--code` mentions PowerShell single-quote usage for code containing `$`
- **AND** the help points to `--file` as the preferred alternative for multi-line or `$`-containing scripts
