## MODIFIED Requirements

### Requirement: Help includes a component-detection example

The formal CLI help surface SHALL include a `--help-example` entry for component detection that demonstrates the standard PuerTS pattern for scene-inspection scripts: using direct `CS.UnityEngine.X` access for static members and instance calls, `puer.$typeof(CS.UnityEngine.X)` only where a `System.Type` value is required as a parameter (such as `TryGetComponent`), `puer.$ref()` for out-parameter references, and `get_Item()` for C# indexer access. The example SHALL NOT wrap static member access in `puer.$typeof(...)`. The example script SHALL be verified to execute successfully against a real Unity host as part of the change's acceptance evidence, not solely verified by help-text rendering.

#### Scenario: Agent discovers the component-detection example

- **WHEN** an agent invokes `unity-puer-exec --help-example component-detection`
- **THEN** the output includes a complete script body demonstrating direct `CS.UnityEngine.SceneManagement.SceneManager` static access, `puer.$typeof(CS.UnityEngine.MeshFilter)` used only as the `TryGetComponent` type argument, `puer.$ref()`, `TryGetComponent`, and `get_Item()`
- **AND** the example notice text explains that `puer.$typeof(CS.XXX)` is only needed where a `System.Type` parameter is required, not for ordinary static or instance member access
- **AND** the notice text explains that C# indexers require `get_Item()` syntax

#### Scenario: Component-detection example executes against a real host

- **WHEN** the documented `component-detection` example script body is executed against a real Unity host via `exec`
- **THEN** the script completes without a thrown error
- **AND** the returned `result` matches the shape described by the example (a `rootCount` integer and a `results` array)
