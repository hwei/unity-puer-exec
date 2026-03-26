## Context

`ReadMe.md` is currently a minimal stub (requirements + git URL install + "usage forthcoming"). The package is now live on OpenUPM, so the README is the primary landing page for new users. The target audience is Unity developers who direct AI agents — they need to understand the vision, install via OpenUPM, and know how to prompt their agent to use the tool.

The explore session established the full content structure and wording before this proposal was filed. Design decisions here reflect those findings.

## Goals / Non-Goals

**Goals:**
- English `ReadMe.md` that a new user can understand and act on within 2 minutes
- Complete Chinese translation at `ReadMe.zh-CN.md`
- Language switcher at the top of both files
- Badges: OpenUPM + Agentic AI
- Vision and Design Philosophy sections that set expectations
- Agent-prompt-shaped Installation and Usage sections with two tested example prompts
- Solidifying Skills section that introduces the pattern conceptually with an opening prompt

**Non-Goals:**
- CLI behavior changes
- Spec requirement changes
- A full skill library or JS script examples (those belong in future skill-focused changes)
- Any Unity Editor or package source changes

## Decisions

### Document structure order
Vision → Design Philosophy → Requirements → Installation → Usage → Solidifying Skills → License → language link

Rationale: readers who don't yet know what the tool is should encounter the vision first. Technical prerequisites come after motivation. Skill solidification is last because it requires prior experience with the basic workflow.

### Language switcher placement
One line at the very top of each file, before badges:

```
[English](ReadMe.md) | [中文](ReadMe.zh-CN.md)
```

Rationale: avoids readers abandoning a file they can't read before reaching the switcher.

### Installation prompt design
Give a nearly-fixed agent prompt. The only variable is the Unity project path; the prompt tells the agent to auto-detect and ask if not found.

```
"Install the Unity package com.txcombo.unity-puer-exec from OpenUPM
(registry: https://package.openupm.com) into my Unity project.
If you can't locate the project, ask me."
```

Rationale: OpenUPM install is mechanical — there's no decision the user needs to make.

### CLI discovery guidance
State that the binary is inside the package at `CLI~/unity-puer-exec.exe` and give the agent the package name (`com.txcombo.unity-puer-exec`) to find it. Do not hardcode the full `Library/PackageCache/...@<version>/` path.

Rationale: the version segment makes a hardcoded path brittle. The agent can resolve the actual location given the package name; both `Library/PackageCache/` (OpenUPM) and `Packages/` (local install) are findable by package name.

### Usage examples — two prompts
1. **Simple scene operation** (create a sphere): agent discovers the exec + observe workflow through CLI help. No "verify the result" instruction — the human checks visually.
2. **Code change + compile + verify** (add a MenuCommand that logs GUID): multi-step workflow demonstrating compile cycle handling. "Verify" kept because it is the explicit goal of this example.

Rationale: these two prompts cover the two validation-tested task shapes (Prompt A and Prompt B). They give readers concrete copy-pasteable starting points without over-specifying how the agent should proceed.

### Solidifying Skills section
Introduce the problem (repeated JS scripts, re-explaining workflows), then provide a single opening prompt to start the design conversation:

> "The unity-puer-exec commands we just ran will come up often, and the JS scripts might be reusable. Can you find a way to turn these into a skill? Let's discuss the design."

No prescriptive skill format or file structure. The section is intentionally conceptual — the design conversation happens with the agent, not in the README.

### Chinese translation
`ReadMe.zh-CN.md` is a complete translation. All content is mirrored; no sections are omitted. Agent prompts are translated into natural Chinese but preserve the technical terms (`unity-puer-exec`, package names, badge markup).

## Risks / Trade-offs

- **Agent prompt wording drift**: if the CLI surface changes significantly, the example prompts in the README may become misleading. Mitigation: prompts are intentionally high-level ("use unity-puer-exec to...") and rely on CLI help for discovery rather than hardcoding command syntax.
- **Chinese translation maintenance**: two files to keep in sync. Mitigation: accepted trade-off; the Chinese translation is complete at this point in time and future changes can update both together.
