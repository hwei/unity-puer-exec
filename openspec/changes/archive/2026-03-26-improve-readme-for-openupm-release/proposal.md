## Why

The package is now published on OpenUPM, but the current `ReadMe.md` reads as a minimal developer stub — no vision, no badges, and no guidance shaped for the actual primary audience: humans directing AI agents. Readers landing from OpenUPM need to immediately understand what the tool is for, why it matters, and how to get started by prompting their agent.

## What Changes

- Add OpenUPM and Agentic AI badges near the top
- Add a language switcher (English / 中文) near the top
- Add a **Vision** section: Unity development fully AI Agent-driven, humans never touching IDE or Editor
- Add a **Design Philosophy** section: CLI-native Unity, self-discoverable help, minimal primitives + skill-based extensibility
- Rewrite **Installation** as an agent prompt users can copy-paste
- Rewrite **Usage** with CLI discovery guidance and two concrete example prompts (simple scene op; code change + compile + verify)
- Add a **Solidifying Skills** section explaining the pattern and the opening prompt to start a design conversation with an agent
- Add `ReadMe.zh-CN.md` as a complete Chinese translation, linked from the English README

## Capabilities

### New Capabilities

- `readme-agent-onboarding`: User-facing README content that conveys project vision, design philosophy, and agent-oriented installation/usage guidance targeted at OpenUPM readers

### Modified Capabilities

<!-- No existing spec-level requirements are changing. This change is purely a documentation surface. -->

## Impact

- `ReadMe.md`: full rewrite
- `ReadMe.zh-CN.md`: new file (complete Chinese translation)
- No source code, CLI behavior, or spec requirements are affected
