# Exe Origin Project Inference

## Purpose

Define the durable requirements for inferring the Unity project root from the CLI exe's own install location, enabling `--project-path` to be optional when the exe is installed inside the target project's package tree.

## Requirements

### Requirement: CLI infers project path from exe install location

When no explicit project path is supplied via `--project-path` and no `UNITY_PROJECT_PATH` environment variable is set, the CLI SHALL attempt to infer the Unity project root from the exe's own install location. The CLI SHALL resolve the exe origin from `sys.argv[0]`, walk up the directory tree, and identify the first ancestor that contains `Packages/manifest.json` with `com.txcombo.unity-puer-exec` listed in its `dependencies` object. If inference succeeds, the inferred path SHALL be used as the project path. If inference fails, the CLI SHALL fall back to the cwd fallback without error.

#### Scenario: Exe installed in PackageCache infers project root

- **WHEN** the CLI exe is invoked by absolute path from `<Project>/Library/PackageCache/com.txcombo.unity-puer-exec@<version>/CLI~/unity-puer-exec.exe`
- **AND** no `--project-path` argument or `UNITY_PROJECT_PATH` env var is provided
- **THEN** the CLI infers `<Project>` as the Unity project root
- **AND** selector-driven commands operate against that project

#### Scenario: Exe installed as embedded package infers project root

- **WHEN** the CLI exe is invoked by absolute path from `<Project>/Packages/com.txcombo.unity-puer-exec/CLI~/unity-puer-exec.exe`
- **AND** no `--project-path` argument or `UNITY_PROJECT_PATH` env var is provided
- **THEN** the CLI infers `<Project>` as the Unity project root

#### Scenario: Exe not inside a Unity project falls through silently

- **WHEN** the CLI exe is invoked from a location where no ancestor directory contains `Packages/manifest.json` referencing `com.txcombo.unity-puer-exec`
- **AND** no `--project-path` argument or `UNITY_PROJECT_PATH` env var is provided
- **THEN** the CLI does not produce an error from the inference attempt
- **AND** the CLI falls back to cwd as the project path

#### Scenario: Manifest exists but does not reference this package

- **WHEN** the CLI exe is located under a Unity project whose `Packages/manifest.json` does not contain `com.txcombo.unity-puer-exec` in its `dependencies`
- **THEN** that directory is not treated as a matching project root
- **AND** the walk continues upward or falls through to cwd

### Requirement: Explicit project path takes precedence over exe inference

The resolution order SHALL be: `--project-path` > `UNITY_PROJECT_PATH` env var > exe origin inference > cwd fallback. Exe origin inference SHALL NOT override any explicitly configured project path.

#### Scenario: --project-path overrides inference

- **WHEN** `--project-path /explicit/path` is supplied
- **AND** the exe is installed inside a different Unity project
- **THEN** the CLI uses `/explicit/path` as the project path
- **AND** exe origin inference is not attempted

#### Scenario: Environment variable overrides inference

- **WHEN** `UNITY_PROJECT_PATH` is set to `/env/path`
- **AND** no `--project-path` argument is supplied
- **AND** the exe is installed inside a Unity project
- **THEN** the CLI uses `/env/path` as the project path
- **AND** exe origin inference is not attempted
