## Context

The latest Prompt B evidence showed that the CLI can verify through `exec` plus `wait-for-log-pattern`, but top-level help still presents workflow names in a way that looks command-like. That ambiguity is product-facing because it sits on the main discovery surface.

## Goals / Non-Goals

**Goals:**
- Make it obvious which top-level entries are executable commands and which are `--help-example` workflow identifiers.
- Preserve the existing workflow examples instead of removing them.
- Validate the effect through a Prompt B rerun.

**Non-Goals:**
- Do not redesign Prompt B itself.
- Do not add a real executable command solely to mirror every workflow example name.

## Decisions

### Decision: Keep workflow examples, but label them as examples
Top-level help should keep advertising workflow examples because they are useful, but each workflow-style entry should visibly state that it is a `--help-example` target rather than a subcommand.

### Decision: Prompt B remains the validation target
The fix should be judged by whether a `gpt-5.4-mini subagent` Prompt B rerun avoids the false-start of treating a workflow example as a direct command while staying inside the published help-only boundary.

## Risks / Trade-offs

- [Stronger labeling may make the overview slightly denser] → Acceptable because top-level help is already a discovery-oriented document and clarity matters more than brevity here.
