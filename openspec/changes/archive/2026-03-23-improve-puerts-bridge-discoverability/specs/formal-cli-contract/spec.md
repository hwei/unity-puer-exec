## ADDED Requirements

### Requirement: Help explicitly frames script authoring as a PuerTS-style bridge workflow
The formal CLI help surface SHALL explain that `unity-puer-exec` script authoring uses a PuerTS-style JavaScript-to-C# bridge for Unity and .NET API access. This explanation SHALL be discoverable from published help without requiring repository-only artifacts.

#### Scenario: Agent reads help to understand how JavaScript reaches Unity APIs
- **WHEN** an agent reads the published help surface for `unity-puer-exec` script authoring
- **THEN** the help explicitly names the PuerTS-style bridge model
- **AND** the help identifies `puer.loadType(...)` as a normal way to load Unity or C# types
- **AND** the help does not force the caller to infer the bridge model only from incidental workflow examples

### Requirement: Help includes a concise bridge mental model
The formal CLI help surface SHALL provide a short bridge-oriented mental model near script authoring guidance so callers can distinguish bridged .NET values from ordinary JavaScript values.

#### Scenario: Agent reads exec help before writing a verification script
- **WHEN** an agent reads `unity-puer-exec exec --help`, `exec --help-args`, or a directly related published example
- **THEN** the help explains that Unity and C# APIs are accessed through bridged .NET types rather than ordinary JS modules
- **AND** the help keeps that explanation concise enough to remain part of the normal CLI discovery path

### Requirement: Help warns that bridged arrays and generic lists are not plain JS arrays
The formal CLI help surface SHALL include a short warning that bridged C# arrays and generic lists remain bridge objects with .NET-oriented semantics and should not be assumed to behave exactly like native JavaScript arrays.

#### Scenario: Agent reads bridge guidance for collection-shaped values
- **WHEN** an agent reads the bridge-oriented help guidance
- **THEN** the help states that bridged C# arrays and `List<T>` values are not plain JS arrays
- **AND** the help points callers toward the intended PuerTS-aware access patterns or reference material for deeper details

### Requirement: Help exposes a purpose-built bridge discovery path
The formal CLI help surface SHALL expose bridge usage through a purpose-built help path, example, or dedicated section rather than relying only on the existing editor-exit workflow example.

#### Scenario: Agent looks for a canonical bridge usage example
- **WHEN** an agent uses published help to learn how to call Unity or C# types from JavaScript
- **THEN** the help surface offers a bridge-oriented example or section intended for that purpose
- **AND** the agent does not need to treat a task-specific exit example as the only discoverable bridge reference

### Requirement: Official bridge reference links remain supplementary
When the CLI help surface links to external bridge documentation, the link SHALL supplement rather than replace repository-owned help text.

#### Scenario: Agent needs deeper bridge details than the CLI can carry concisely
- **WHEN** the published help links to an official PuerTS JS-to-C# reference
- **THEN** the CLI still explains the local bridge model in repository-owned help text
- **AND** the external link is presented as a deeper reference, not as the only explanation of expected bridge usage
