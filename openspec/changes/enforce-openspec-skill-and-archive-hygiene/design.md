## Context

The repository already states that OpenSpec is the canonical workflow, but that instruction has not been specific enough to force the correct operational path for new agent sessions. In practice, a session can understand that OpenSpec matters while still missing the stronger rule that propose/apply/archive work should be done through the installed OpenSpec skills or the official `openspec` CLI rather than by manually moving change directories.

That gap likely contributed to the current stale state around `validate-help-only-agent-cli-discoverability`: the archived record exists, but an empty active-directory placeholder remains visible enough for `openspec list` to treat it as active work. This change should both repair the current inconsistency and make the preferred operator path explicit.

## Goals / Non-Goals

**Goals:**
- Make the expected OpenSpec operating path explicit for agents and maintainers.
- Reduce the chance that manual directory manipulation leaves archive residue or stale active placeholders.
- Repair the existing stale active-directory placeholder and verify that planning scans no longer surface it.

**Non-Goals:**
- Do not redesign the OpenSpec CLI itself.
- Do not add automated archive validation tooling in this change.
- Do not rewrite all repository workflow guidance from scratch.

## Decisions

### Decision: Prefer OpenSpec skills first, official CLI second, manual directory edits only for repair
Repository guidance should state that agents should first use the installed OpenSpec skills for propose/apply/archive tasks, fall back to official `openspec` commands when needed, and avoid manual manipulation of `openspec/changes/` except when explicitly repairing abnormal state.

Alternative considered:
- Document only the `openspec` CLI. Rejected because the repository already provides OpenSpec skills that encode the safer workflow shape for agent sessions.

### Decision: Repair the current empty placeholder manually
The existing empty active-directory placeholder should be removed now because it is already known to be stale and its continued presence pollutes active planning views.

Alternative considered:
- Leave the residue in place and only document future behavior. Rejected because the repository would continue to present misleading active-work state.

## Risks / Trade-offs

- [Agents may still bypass the preferred path] -> Make the rule explicit in both `AGENTS.md` and `openspec/project.md`.
- [Manual cleanup could remove unexpected content] -> Confirm the stale active path is empty before deleting it.
- [Guidance may become repetitive] -> Keep the wording short and focused on propose/apply/archive operations.
