## Context

ReadMe.md currently serves as an internal orientation doc for contributors and agents, covering product boundary definitions, OpenSpec workflow entry points, test layering, and directory structure. None of this is useful to a user who lands on the GitHub repository page wanting to understand, install, or use the package.

AGENTS.md already contains contributor-facing environment setup and OpenSpec workflow guidance. `openspec/specs/validation-host-integration/spec.md` already establishes the requirements for real-host integration testing (what SHALL be validated), but contains no operational instructions (how to set up the environment, which commands to run, how to interpret skip vs. fail). That operational gap is what the test workflow content in ReadMe.md fills.

## Goals / Non-Goals

**Goals:**
- Rewrite ReadMe.md as a user-facing document covering: what the product is, requirements, how to install (Unity package via UPM), and a brief usage pointer
- Add `openspec/specs/validation-host-integration/how-to-run.md` with operational testing instructions (test layering, real-host regression setup, result interpretation) migrated from ReadMe.md
- Add a link in AGENTS.md pointing contributors to that document
- Retire content already covered by AGENTS.md or openspec/config.yaml (product boundary prose, OpenSpec quick-links, directory overview)

**Non-Goals:**
- Writing comprehensive usage documentation or API reference (that is future work)
- Changing the product, the CLI, or the package in any way
- Moving content into openspec/config.yaml (it already has the right context; no additions needed)

## Decisions

### D1: Language for the new ReadMe.md — English

The package targets the Unity developer community broadly (GitHub, potential OpenUPM distribution). English is the standard for package-level README files in this ecosystem. Internal workflow docs (AGENTS.md) remain in Chinese, which is correct for contributor-facing content in this repository.

### D2: Scope of the new ReadMe.md

The rewritten ReadMe contains exactly four sections:
1. **Product name + one-liner** — what it is
2. **Requirements** — Unity 2022.3+, Puerts Core 3.0.0 dependency
3. **Installation** — UPM git URL method; note that OpenUPM is a future goal (already tracked as a separate change)
4. **Usage pointer** — brief description of the integration model (Unity package + external CLI), with a note that detailed docs are forthcoming

No changelog, no badges, no roadmap prose. Keeping it minimal avoids content that needs continuous maintenance before the product stabilizes.

### D3: Migration target for test workflow content — `validation-host-integration/how-to-run.md`

`openspec/specs/validation-host-integration/spec.md` is already the authoritative location for real-host integration requirements. Placing a companion `how-to-run.md` in the same directory keeps the spec (what) and the operational runbook (how) together, so a contributor reading the spec can immediately find the instructions without switching contexts.

AGENTS.md gets a single pointer line under its existing "OpenSpec entry points" section, directing contributors to `how-to-run.md` for test execution instructions.

The content is migrated verbatim where accurate; the `current coverage chain` line (which names a specific CLI invocation chain) is retained as-is since it reflects the actual integration test state at the time of this change.

### D4: Product boundary section — retire, do not migrate

The product boundary bullets in ReadMe.md (lines 5–13) describe repository governance decisions that are:
- Already captured in openspec/config.yaml's context field
- Contributor/agent guidance, not user information
- Partially superseded by AGENTS.md's environment setup

Migrating them to AGENTS.md would introduce duplication. They are retired.

## Risks / Trade-offs

- **Risk: ReadMe.md is sparse at first** → Acceptable for a pre-stable package. Sparse and accurate beats detailed and misleading.
- **Risk: Installation section references a git URL that may change** → Use the canonical GitHub URL from package.json; it's the right long-term pointer.
- **Risk: `how-to-run.md` becomes stale** → Same staleness risk existed in ReadMe.md; no worse. The spec and tests themselves are the authoritative source. Placing it next to the spec makes it easier to notice and update together.
