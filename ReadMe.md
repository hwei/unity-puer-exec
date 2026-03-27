[English](ReadMe.md) | [中文](ReadMe.zh-CN.md)

[![OpenUPM](https://img.shields.io/npm/v/com.txcombo.unity-puer-exec?label=openupm&registry_uri=https://package.openupm.com)](https://openupm.com/packages/com.txcombo.unity-puer-exec/)
[![Agentic AI Project](https://img.shields.io/badge/Agentic%20AI-Project-0a7ea4)](https://github.com/hwei/unity-puer-exec)

# Unity Puer Exec

Unity package and CLI for AI agent-driven Unity workflows over a [PuerTS](https://github.com/Tencent/puerts) host.

## Vision

The end state is straightforward: humans describe the change, and AI agents do the Unity work.

That means no routine clicking through the Unity Editor, no hand-driving an IDE for every iteration, and no fragile "copy this script, now run that tool" workflow as the default. `unity-puer-exec` exists to let an agent operate Unity through a CLI-native surface, so the human can stay focused on intent, review, and direction.

## Design Philosophy

`unity-puer-exec` is intentionally small.

- The interface is CLI-native, so agents can inspect `--help`, choose commands, and recover from non-success states without depending on repository-only tribal knowledge.
- The core surface stays minimal: a few primitives for readiness, execution, observation, and recovery instead of a large pile of one-off commands.
- Repeated higher-level workflows belong in skills. Once you and your agent notice a pattern, you can solidify it instead of re-explaining it forever.

## Requirements

- Unity 2022.3 or later
- [com.tencent.puerts.core](https://github.com/Tencent/puerts) 3.0.0

## Installation

Give your agent this prompt:

```text
Install the Unity package com.txcombo.unity-puer-exec from OpenUPM (registry: https://package.openupm.com) into my Unity project. If you can't locate the project automatically, ask me for the project path. If the OpenUPM registry is unreachable, ask me for the proxy settings or mirror configuration you should use, such as HTTP_PROXY and HTTPS_PROXY.
```

The package name is `com.txcombo.unity-puer-exec`.

## Usage

The CLI binary ships inside the package at `CLI~/unity-puer-exec.exe`. Your agent should find it by searching the Unity project for the package `com.txcombo.unity-puer-exec` rather than hardcoding a full `Library/PackageCache/...@<version>/` path.

Start by letting the agent discover the CLI surface through `--help` and per-command help instead of assuming command syntax from memory.

Example prompt: simple scene operation

```text
Use unity-puer-exec to add a Sphere to the currently open Unity scene. First discover the CLI workflow from help, then locate the unity-puer-exec binary inside the installed package, run the change, and tell me what you changed.
```

Example prompt: code change, compile, and verify

```text
Use unity-puer-exec to add a Unity Editor menu command that logs the GUID of the currently selected asset. Discover the CLI workflow from help first, find the binary inside the com.txcombo.unity-puer-exec package, make the code change, handle any compile cycle you encounter, run the verification workflow, and tell me the verification result.
```

## Solidifying Skills

After a few sessions, a pattern usually appears: the agent keeps rediscovering the same `unity-puer-exec` workflow, and the JavaScript snippets start to look reusable.

That is the right time to turn the repeated workflow into a skill instead of treating every session as a fresh invention.

Use this opening prompt to start that design conversation:

```text
The unity-puer-exec commands we just ran will come up often, and the JS scripts might be reusable. Can you find a way to turn these into a skill? Let's discuss the design.
```

## Maintainer Release Prep

For the maintainer release-preparation workflow and the local `tools/release_openupm.py` helper, see [openspec/specs/openupm-release-pipeline/how-to-run.md](openspec/specs/openupm-release-pipeline/how-to-run.md).

## License

MIT

Chinese version: [ReadMe.zh-CN.md](ReadMe.zh-CN.md)
