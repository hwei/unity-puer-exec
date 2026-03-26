## Context

The CLI currently emits a single `next_step` field only on `exec → running` responses, always pointing to `wait-for-exec`. This was introduced by the `improve-agent-verification-closure` change as a "continuation hint" for medium-capability agents. The current implementation is in `_next_step_payload()` in `unity_puer_exec_runtime.py`, which builds a fixed `{ "command": "wait-for-exec", "argv": [...] }` payload.

All ten commands produce structured JSON responses across multiple status outcomes, but only one command × one status carries any follow-up guidance. Agents operating without `--help` context must either memorize the command tree or fall back to help lookups mid-workflow.

The formal-cli-contract spec (requirement "Accepted project-scoped exec responses include an explicit continuation hint") currently mandates the single-valued `next_step` pointing to `wait-for-exec`.

## Goals / Non-Goals

**Goals:**
- Replace `next_step` (singular object) with `next_steps` (array of action candidates) across all commands and statuses where follow-up actions are non-trivial.
- Add `situation` (string) for response states where no concrete command is appropriate but context helps the agent understand the predicament.
- Add a global `--suppress-guidance` flag to omit both fields for proficient agents.
- Expand `--help-status` to include situation-level explanations so suppressed agents can still query status meanings.
- Define a static guidance matrix (command × status → next_steps + situation) as the single source of truth.

**Non-Goals:**
- Dynamic filtering of `next_steps` based on script content or response payload inspection (e.g., detecting `correlation_id` in result). All candidates for a given command × status are always emitted; the `when` hint lets the agent decide applicability.
- Adding guidance for usage errors (exit code 2) — these are already handled by argparse and help text.
- Changing `--help` or workflow example content — the runtime guidance supplements but does not replace the help surface.

## Decisions

### Decision 1: Static guidance matrix over dynamic payload inspection

The guidance matrix is a static lookup keyed by `(command, status)`. The CLI does not inspect the response payload to filter candidates (e.g., checking whether `result` contains `correlation_id`).

**Rationale**: Dynamic filtering would couple guidance logic to script authoring conventions and create fragile inference paths. The `when` hint gives agents enough context to self-filter. This keeps the implementation simple and the contract predictable.

**Alternative considered**: Inspect `result` fields to conditionally include/exclude candidates. Rejected because `running` responses may not yet have the relevant `result` data, and the coupling would make the guidance matrix harder to reason about.

### Decision 2: `next_steps` items carry optional `argv`

Each action candidate carries `command` (string), `when` (string), and optional `argv` (string array). `argv` is included when the CLI has enough context to construct a concrete invocation (e.g., same `--project-path`, same `--request-id`). When `argv` cannot be constructed from the current response context, only `command` and `when` are provided.

**Rationale**: Concrete `argv` reduces agent work for the common case (like the current `next_step`), while omitting it for context-dependent candidates (like `wait-for-log-pattern` where the pattern is caller-defined) avoids emitting misleading incomplete invocations.

### Decision 3: Global flag position and naming

`--suppress-guidance` is a global flag parsed before the subcommand name: `unity-puer-exec --suppress-guidance <command> ...`. This requires adding an argument to the top-level parser rather than each subparser.

**Rationale**: The flag applies identically to all commands and has no command-specific semantics. A global position reduces cognitive load ("one flag, one place") and avoids repeating the definition across ten subparsers. Current precedent is per-subparser flags, but `--suppress-guidance` is genuinely cross-cutting in a way that `--include-diagnostics` (which is also universal) is not — diagnostics are a response-enrichment concern scoped to individual command output, while guidance suppression is a presentation-layer concern.

**Alternative considered**: Per-subparser `--suppress-guidance` following existing `--include-diagnostics` pattern. Rejected because it creates ten identical definitions with no per-command variation.

### Decision 4: Guidance data lives in help_surface.py

The guidance matrix (command × status → next_steps + situation) is defined as a data structure in `help_surface.py` alongside existing help data. Runtime code calls a lookup function rather than inlining guidance logic.

**Rationale**: `help_surface.py` is already the single source of truth for command descriptions, status meanings, and workflow examples. Guidance is semantically part of the help/discoverability surface. Keeping it in one place makes the matrix easy to audit and update.

### Decision 5: `--help-status` expansion approach

The existing `render_command_status_help()` output is extended with situation descriptions for each non-success status. No new `--help-status <status-name>` sub-query is added.

**Rationale**: The per-status situation text is short enough that listing all statuses together is not burdensome, and the single-query approach avoids adding a new help flag variation for marginal token savings.

### Decision 6: Breaking change — `next_step` → `next_steps`

The singular `next_step` field is removed and replaced by `next_steps` (array). There is no compatibility shim or dual-emission period.

**Rationale**: The only known consumers are AI agents interacting through the CLI's machine-readable output. These agents re-read help on each session and can adapt to the renamed field immediately. A compatibility shim would add complexity for a consumer base that does not need it.

## Risks / Trade-offs

- **[Breaking field rename]** → Agents that hard-code `next_step` (singular) will need updating. Mitigation: the change is documented as BREAKING in the proposal; `--help-status` and `--help` will reflect the new field name.
- **[Matrix maintenance burden]** → Every new command or status requires a guidance matrix entry. Mitigation: the matrix is co-located with existing help data in `help_surface.py`, making it part of the same review surface.
- **[Global flag is a new parser pattern]** → No existing flags use the global position. Mitigation: argparse supports top-level arguments alongside subparsers; the implementation is straightforward. If future global flags are needed, the pattern is established.
