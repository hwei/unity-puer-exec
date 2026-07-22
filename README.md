[English](README.md) | [中文](README.zh-CN.md)

[![OpenUPM](https://img.shields.io/npm/v/com.txcombo.unity-puer-exec?label=openupm&registry_uri=https://package.openupm.com)](https://openupm.com/packages/com.txcombo.unity-puer-exec/)
[![Agentic AI Project](https://img.shields.io/badge/Agentic%20AI-Project-0a7ea4)](https://github.com/hwei/unity-puer-exec)

# Unity Puer Exec

Unity package and CLI for **fully autonomous** AI agent-driven Unity workflows over a [PuerTS](https://github.com/Tencent/puerts) host.

The agent starts the Editor, writes code, handles compile errors, dismisses blocking dialogs, and verifies results — entirely without human intervention at the Editor.

## Why unity-puer-exec?

Most Unity automation tools assume a human has already opened the Editor and will stay nearby to unblock things. `unity-puer-exec` is built for the case where **the agent is alone with the project**:

- **Zero-to-result session lifecycle.** The CLI launches the correct Unity version for the project, waits for readiness, recovers crashed sessions, avoids duplicate launches, and auto-dismisses modal blockers (Safe Mode, save-scene dialogs). No human at the Editor, ever.
- **Structured compile-error closed loop.** `exec --refresh-before-exec` brackets a full refresh → compile-settle → execute cycle. Compile failures return machine-readable diagnostics (exit code 23, inline error list) so the agent can fix code and retry until clean — no log scraping.
- **Multi-project parallel operation.** Dynamic port allocation, per-project session artifacts, and launch claims let one agent (or many) drive several Unity projects concurrently without cross-talk.
- **PuerTS-powered instant execution.** Scripts run through the PuerTS JavaScript bridge — interpreted, no compilation step, no external compiler dependency. If your project already uses PuerTS, there is nothing extra to install.

### Real-world scenario: asset pipeline automation

This is the workflow `unity-puer-exec` was built for. In one agent session, with no human touching the Editor:

1. The agent inspects art assets to understand their structure and characteristics.
2. It writes C# processing code for the asset pipeline.
3. It triggers compilation via the CLI and reads structured diagnostics if anything fails.
4. It fixes errors, recompiles, and triggers the build/packaging step.
5. It inspects the build output and verifies correctness before reporting back.

The human describes the intent and reviews the result. Everything in between belongs to the agent.

### How it compares

| Capability | unity-puer-exec | [Unity CLI](https://unity.com/blog/meet-the-unity-cli) (official) | [unity-cli-loop](https://github.com/hatayama/unity-cli-loop) | [UniCli](https://github.com/yucchiy/UniCli) | [Puerts Agent](https://github.com/Tencent/puerts) (Puerts.AI) |
|---|:-:|:-:|:-:|:-:|:-:|
| CLI launches & recovers Editor autonomously | Yes | Partial (`unity open`) | Partial (`uloop launch`) | No | No |
| Structured compile-error retry loop | Yes | No | Partial (compile + get-logs) | No | No |
| Auto-dismiss modal blockers (Safe Mode, etc.) | Yes | No | No | No | No |
| Session recovery & duplicate-launch prevention | Yes | No | Basic | No | No |
| Multi-project parallel (first-class) | Yes | No | Basic (port flag) | No | No |
| Dynamic code execution | JS via PuerTS (interpreted, instant) | C# eval (pipeline package, experimental) | C# via Roslyn (compiles to DLL) | C# eval | JS via PuerTS |
| Extra runtime dependency | None (self-contained .exe) | None | Node.js 22+ + Unity-bundled Roslyn | None | None |
| Minimum Unity version | 2022.3 | 6.0 LTS | 2022.3 | 2022.3 | 2022.3 |
| PlayMode input simulation / recording | No | No | Yes | No | No |
| Screenshot / multimodal feedback | Via JS | No | Yes | Yes | Yes |

Key differences vs the closest alternatives:

- **vs unity-cli-loop**: Its `execute-dynamic-code` compiles C# to a DLL through Unity-bundled Roslyn (`csc.dll` / `Microsoft.CodeAnalysis.CSharp.dll`) with a warm compiler worker process — heavier per-execution cost and more moving parts. `unity-puer-exec` interprets JavaScript through PuerTS with no compilation step. For projects already on PuerTS, the dependency footprint is dramatically smaller: no Roslyn resolution, no compiler process management, no Node.js runtime.
- **vs Unity CLI (official)**: Right direction, but the `com.unity.pipeline` package that connects to a running Editor is still experimental and requires Unity 6.0 LTS+. No compile-error loop, no blocker recovery, no multi-project management yet.
- **vs UniCli / Puerts Agent**: Both require a human-opened Editor. Neither manages sessions, compile errors, or modal blockers.

## Design Philosophy

`unity-puer-exec` is intentionally small.

- The interface is CLI-native, so agents can inspect `--help`, choose commands, and recover from non-success states without depending on repository-only tribal knowledge.
- The core surface stays minimal: a few primitives for readiness, execution, observation, and recovery instead of a large pile of one-off commands.
- Every non-success response carries `next_steps` and `situation` guidance — concrete follow-up commands the agent can execute directly.
- Repeated higher-level workflows belong in skills. Once you and your agent notice a pattern, you can solidify it instead of re-explaining it forever.

## Requirements

- Unity 2022.3 or later
- [com.tencent.puerts.core](https://github.com/Tencent/puerts) 3.0.0

## Installation

Install from **OpenUPM** (https://package.openupm.com), the open-source Unity package registry. Do **not** clone this repository into your project — the repository is the development source; the OpenUPM package is the built, versioned distribution.

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

Chinese version: [README.zh-CN.md](README.zh-CN.md)
