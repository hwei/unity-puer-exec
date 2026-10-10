# Spec Delta

## MODIFIED Requirements

### Requirement: Refresh triggers only when a compile-triggering change is detected

The Unity control service SHALL observe changes to compile-triggering project files and SHALL perform an `AssetDatabase.Refresh()` before executing a script when, and only when, it detects a change that requires recompilation. Compile-triggering files SHALL comprise C# script sources, assembly definition and reference files, and compiler response files. Changes to scenes, prefabs, metadata files, textures, audio, and all other non-code assets SHALL NOT trigger a refresh. A file whose path contains a directory segment whose name starts with `.`, within the watched `Assets/` or `Packages/` tree, SHALL NOT count as a detected change.

#### Scenario: C# source changes before exec

- **WHEN** a `.cs` file under the project's `Assets/` or `Packages/` tree is written after the last settled import
- **AND** no directory segment in that path starts with `.`
- **AND** a new exec request arrives
- **THEN** the server refreshes the project before executing the script
- **AND** the refresh completes before script execution begins

#### Scenario: Assembly definition changes before exec

- **WHEN** an `.asmdef` or `.asmref` file is written after the last settled import
- **AND** no directory segment in that path starts with `.`
- **AND** a new exec request arrives
- **THEN** the server refreshes the project before executing the script

#### Scenario: Non-code asset change does not trigger refresh

- **WHEN** a `.unity` scene, `.prefab`, `.meta`, texture, or audio file is written after the last settled import
- **AND** no compile-triggering file changed
- **AND** a new exec request arrives
- **THEN** the server does not refresh
- **AND** the exec proceeds without a refresh step

#### Scenario: No change at all proceeds immediately

- **WHEN** no compile-triggering file changed since the last settled import
- **AND** a new exec request arrives
- **THEN** the server does not refresh and does not walk the project tree
- **AND** the exec proceeds to its normal job creation and execution path

#### Scenario: A compile-triggering file inside a dot-directory does not refresh

- **WHEN** a `.cs`, `.asmdef`, `.asmref`, or `.rsp` file is written under a directory whose name starts with `.`
- **AND** no other compile-triggering file changed
- **AND** a new exec request arrives
- **THEN** the change signal is not pending
- **AND** the server does not refresh
- **AND** the exec proceeds without waiting for a compilation

#### Scenario: A dot segment above the watched root does not suppress detection

- **WHEN** a compile-triggering file is written under the watched `Assets/` or `Packages/` tree
- **AND** an ancestor of that root on disk has a directory whose name starts with `.`
- **AND** no directory segment below the watched root starts with `.`
- **AND** a new exec request arrives
- **THEN** the change is detected
- **AND** the server refreshes the project before executing the script
