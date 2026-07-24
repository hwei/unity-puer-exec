## Context

This change carries the help-only remainder of the 2026-07-23 agent feedback round. That round produced eleven items; the investigation that followed sorted them into three groups, and only one group belongs here.

Items dissolved by the version discovery and handled by `enforce-cli-version-compatibility`: the three "missing capability" claims (`--full-text`, `--indexes`, `--response-file`), all of which are documented in current help and were absent only from the v0.6.0 binary the agent ran. Nothing needs adding to help for these.

Items withdrawn by the reporting agent under interview: a `wait-for-log-pattern --include-new-error-briefs` flag, and a PlayMode wait command. The interview established that the transport is healthy across PlayMode transitions — `session_marker` was identical before and after entering PlayMode, no reconnection or endpoint rediscovery occurred, and a later query returning `gm-not-ready` still carried `status: completed` with exit `0`. That evidence is what reduces the PlayMode item from a proposed command to a help statement about timing.

Items requiring runtime or guidance changes, deferred to sibling changes: empty `next_steps` on the `exec` and `wait-for-log-pattern` success statuses, and the plain-text argparse parse-error path.

What remains here is content the help surface does not currently carry, verified by reading current source rather than by trusting the report.

## Goals / Non-Goals

**Goals:**

- Give a first-time caller the correct mental model of what an `exec` script can and cannot reach, before it discovers the boundary by failed experiment.
- Name the supported route to a running game, generically, so callers stop looking for a way to call into the game's own JavaScript.
- Set the expectation that a PlayMode transition is a request, without introducing a command.
- Make log-offset and session-guard selection a documented decision rather than a guess.

**Non-Goals:**

- Any runtime, response-shape, status, exit-code, or guidance-matrix change. Those belong to the sibling changes.
- Framework-specific UI instruction. Widget-tree traversal, event invocation conventions, and game-specific operations are explicitly pushed to project-local skills; help states the boundary and stops there.
- A PlayMode wait command, a PlayMode status query, or any new command.
- Re-documenting capabilities that already appear in current help.

## Decisions

### D1: Describe the boundary in terms of what is reachable, not in terms of internals

Help states that the exec environment is separate from the game runtime's JavaScript environment and that the shared C#/Unity object graph is the crossing point. It does not describe how many environments exist, how they are created, or how the host wires them, because that is implementation detail that would date quickly and does not change what a caller should do.

*Alternative considered.* Documenting the environment topology directly was rejected: callers do not need it to make the right choice, and it would couple help text to host internals that the CLI does not own.

### D2: Document the coordination pattern generically, sourced from observed use

The reporting agent's own workaround — creating a shared `GameObject` that the game's main loop recognized, then observing the outcome through logs — is the generic form of the pattern, and it uses nothing framework-specific. Help describes that shape: place or read state both sides can see, then verify through log observation. This is what makes the boundary statement actionable rather than merely restrictive.

### D3: State the skill boundary inside the product

Help explicitly says that framework-specific UI technique belongs in a project-local skill. This is unusual for reference help, and it is deliberate: the same feedback round proposed folding an entire game-UI validation playbook into this CLI's help, and a stated boundary is what prevents that pressure from recurring. It also tells the next caller where that knowledge is expected to live instead of leaving them to infer that the omission is an oversight.

### D4: PlayMode guidance is a timing shape, not a recipe

Help gives the three-stage shape — request, confirm the state flipped, wait for the readiness signal the task actually needs — without prescribing what the third stage looks like, because that is project-specific. The evidence that the second stage is necessary and the first is not sufficient comes from the interview transcript, where the transition returned `completed` immediately and a game-layer query afterward returned `gm-not-ready`.

### D5: Offset selection is documented as intent, not as a default

Rather than changing which offset the existing example teaches, help states the mapping: `.start` for output the originating `exec` produced, `.end` for activity that follows it. Both are correct for their case, and the existing example's use of `.start` is correct for what it demonstrates. Presenting one as the default would reintroduce the ambiguity in the other direction.

### D6: The PowerShell note moves tiers rather than being duplicated

The note is promoted into `exec --help` rather than copied there. A caller composing an inline `--code` value hits the hazard before opening the argument tier, and the failure it produces is misleading — a shell-expanded `$typeof` yields a JavaScript syntax error that does not name the shell. Duplicating the text across tiers was rejected to avoid two copies drifting.

## Risks / Trade-offs

- **Help grows on the surface a first-time caller reads.** → The additions target `exec --help` and `wait-for-log-pattern` help, which are already the densest sections. Mitigation: the boundary statement replaces experimentation that costs far more than reading it, and the PowerShell note moves rather than adds. Length is reviewed against the existing requirement that help prioritize the shortest effective workflow.
- **The stated skill boundary could read as a refusal to help.** → Mitigation: it is paired with the generic pattern that does work, so the caller leaves with a route rather than only a restriction.
- **PlayMode guidance describes host behavior the CLI does not control.** → It is framed as a timing expectation about Unity, not as a CLI contract, and it asserts only what the interview transcript established.
- **Help assertions are verified by rendering, not by execution.** → This is a known weakness of help-only changes in this repository, previously addressed for the component-detection example by adding a real-host execution test. The content here is prose guidance rather than an executable snippet, so rendering assertions are the available check; any code-shaped example added for the PlayMode shape should follow the component-detection precedent and be executed against a real host.
