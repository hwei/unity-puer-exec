## Why

The CLI's command list exists in three places that have drifted apart in two different directions, and nothing detects the drift.

`unity_puer_exec_surface.build_parser` declares **twelve** subcommands. `help_surface.COMMANDS` — derived from `COMMAND_GROUPS`, and the gate for every help tier and every guidance-matrix lookup — contains **ten**, omitting `get-compile-errors` and `get-compile-warnings`. The `formal-cli-contract` requirement that names the "authoritative flat command tree" lists **eleven**, omitting `wait-for-compile`. Each list is missing something a different list has.

The user-visible consequence is that two commands with full durable specs in `compile-error-surface` and `formal-cli-contract` are undocumented at runtime. They appear in the argparse usage line, so an agent can discover them, but:

```
$ unity-puer-exec get-compile-errors --help
usage: unity-puer-exec [--suppress-guidance] {…,get-compile-errors,get-compile-warnings} ...
unity-puer-exec: error: unrecognized arguments: --help
```

`handle_command_help` gates on `COMMANDS`, so `--help`, `--help-args`, and `--help-status` all fall through to argparse and are rejected as unrecognized arguments. Both commands are also absent from `TOP_LEVEL_COMMANDS`, so `unity-puer-exec --help` never mentions them, and absent from `GUIDANCE_MATRIX`, so no response from either carries `next_steps` or `situation` for **any** status — not only the `version_mismatch` that surfaced this.

The durable specs encode the same fragility. `runtime-guidance` states that the matrix "SHALL cover all **ten** commands" — a hardcoded count in prose that was already wrong when the twelfth command shipped and will go stale again on the thirteenth.

## What Changes

- Introduce a single command registry as the one place the CLI's command set is declared, and derive the argparse subcommand set, the help command list, the top-level command summary, and guidance-matrix coverage from it.
- Register `get-compile-errors` and `get-compile-warnings` so they gain `--help`, `--help-args`, and `--help-status` tiers, a top-level help entry, and guidance-matrix coverage on the same terms as every other command.
- Add `wait-for-compile` to the `formal-cli-contract` authoritative command tree, which has been missing it since the command shipped.
- Replace the hardcoded "ten commands" in `runtime-guidance` with a structural requirement: the matrix covers every registered command, whatever the registry contains.
- Add a consistency test asserting that the argparse subcommand set, the help command list, the top-level command summary, and the guidance-matrix command coverage are the same set, so a future command that is added to one and forgotten in the others fails immediately.
- **BREAKING** for a caller that relies on `get-compile-errors --help` or `get-compile-warnings --help` exiting `2` with a prose usage block: those invocations now succeed and render help.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `formal-cli-contract`: the authoritative flat command tree becomes the single declared registry and gains `wait-for-compile`; the per-command help-tier requirement is extended to state that every command in that tree answers every help tier.
- `runtime-guidance`: the guidance-matrix coverage requirement drops the hardcoded command count and is restated against the registry.

## Impact

- New CLI module or shared constant declaring the command registry.
- `cli/python/unity_puer_exec_surface.py`: `build_parser` subcommand declaration derives from the registry.
- `cli/python/help_surface.py`: `COMMAND_GROUPS` / `COMMANDS`, `TOP_LEVEL_COMMANDS`, `COMMAND_HELP`, and `GUIDANCE_MATRIX` gain entries for the two compile commands and are checked against the registry.
- `openspec/specs/formal-cli-contract/spec.md` and `openspec/specs/runtime-guidance/spec.md` via delta specs.
- `tests/test_unity_session_cli.py`: registry-consistency test and help-rendering coverage for the two newly documented commands.
- Sequencing: `normalize-cli-usage-error-responses` rewrites the same `handle_command_help` fall-through path. Landing this change first removes two invocations from that path rather than teaching it to wrap them in JSON and then deleting the case.
