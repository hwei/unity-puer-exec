# Validation evidence — document-host-js-runtime-escape-hatch

Documentation-contract change: no CLI behavior, payload, exit code, or Unity package surface was
touched, so the evidence is the rendered help, the pins that hold it, and the source reading that
justifies the wording.

## The two corrected surfaces

`exec --help` (Quick Start) — the coordination entry keeps its first sentence and the denial is
replaced by a separate, bounded entry:

```
- To coordinate with application code, place or read shared C#/Unity state both sides can observe, then confirm the outcome with log-based observation.
- Escape hatch, outside this CLI's contract: the bridge can enumerate the host application's own JavaScript environments and `Eval` into one -- `puer.loadType('Puerts.JsEnv').jsEnvs` on PuerTS 2.x, `puer.loadType('Puerts.ScriptEnv').scriptEnvs` on 3.x. Both are PuerTS internals, the entry-point name differs by major, and the list order is not stable across boots, so pick the environment holding the state you expect. Expect this to change without notice; prefer the shared C#/Unity route above.
```

`exec --help-args` (Bridge Model) — same correction; the separation entry above it is untouched:

```
- To have application code perform work, place or read shared C#/Unity objects both sides observe, then confirm via log observation.
- Reaching the host application's own JavaScript environments is possible but outside this CLI's contract: the bridge entry point is a PuerTS internal whose name differs by major (`Puerts.JsEnv.jsEnvs` on 2.x, `Puerts.ScriptEnv.scriptEnvs` on 3.x), and `Eval` on the chosen environment runs there. Treat it as an escape hatch that can change without notice, not as a supported interface.
```

Checked on the rendered output, not on the source strings:

| assertion | `exec --help` | `exec --help-args` |
|---|---|---|
| denial present (`no supported way` / `do not expect to call into`) | absent | absent |
| `outside this CLI's contract` | present | present |
| environment-separation boundary still stated | present | present |
| shared C#/Unity still named as the supported route | present | present |
| both majors' entry points named, each on a line naming its major | yes | yes |
| framework-specific technique still scoped to a project-local skill | present | present |

The second site was **not** in the original task list. `--help-args` carried a softer form of the
same denial, and the existing `formal-cli-contract` scenario covers `exec --help` *or*
`exec --help-args`, so correcting only the first would have left the contract violated on a
surface it names. Task 1.1 and the proposal's Impact section were amended during apply to record
this.

## Why both majors are named rather than one

Read from the two hosts' `com.tencent.puerts.core` sources, not from documentation:

| | 2.2.2 | 3.0.0 |
|---|---|---|
| static environment list | `public static List<JsEnv> jsEnvs` — `Runtime/Src/Default/JsEnv.cs:26` | `public static List<ScriptEnv> scriptEnvs` — `Runtime/Src/IL2Cpp/ScriptEnv.cs:24` **and** `Runtime/Src/PInvoke/ScriptEnv.cs:21` |
| `Eval` | `Runtime/Src/Default/JsEnv.cs:350`, `Eval<TResult>` at `:367` | `IL2Cpp/ScriptEnv.cs:194`, `Eval<T>` at `:199`; `PInvoke/ScriptEnv.cs:208`, `Eval<TResult>` at `:213` |
| the other major's entry point | `ScriptEnv` does not exist at all | the retained-but-`[Obsolete]` `JsEnv` (`Runtime/Src/JsEnv.cs:32`) has `Eval` but **no** static `jsEnvs` |

The last row is the finding that settles the wording: on 3.x there is no `JsEnv.jsEnvs` to fall
back to, so a single name in help would be wrong on one major no matter which name was chosen.
`scriptEnvs` is declared identically in both the IL2Cpp and PInvoke variants, so within 3.x the
name does not depend on the scripting backend.

This is `manual-check` evidence: source reading across two host worktrees
(`c3-client-tree2` at 2.2.2, `c3-client-tree5` at 3.0.0).

## Pins

`tests/test_cli_version.py` gains `HostJsRuntimeEscapeHatchHelpTests`, 6 cases over both rendered
surfaces: denial absent, route presented as outside the contract, separation boundary kept, both
majors' entry points named, no entry point presented as valid across majors (line-scoped, so a
field name without its major fails), and framework technique still scoped to a project-local
skill.

Mutation probe `.tmp/help_escape_hatch_guard_teeth.py` — each mutant edits the rendered guidance
list in memory, renders, and restores, which is the exact shape of a future regression:

| mutant | failures |
|---|---|
| old absolute denial restored in Quick Start | 1 |
| old "do not expect to call into" restored in Bridge Model | 1 |
| `jsEnvs` left on a line that no longer names 2.x | 1 |
| the 3.x `scriptEnvs` entry dropped entirely | 1 |
| Bridge Model collapsed to a single major | 1 |
| the environment-separation boundary dropped | 1 |

**6 of 6 caught.** After the run the source is unmutated: the denial count in
`cli/python/help_surface.py` is `0` and the escape-hatch entry is present exactly once.

## Suite

Mocked default suite as documented, including the new pins:

```
Ran 852 tests in 74.791s
OK
```

846 before this change, 852 after — the six new cases, no other movement.

`openspec validate document-host-js-runtime-escape-hatch --strict` passes. The MODIFIED block's
header matches `openspec/specs/formal-cli-contract/spec.md:1353` exactly, so archive replaces the
requirement that currently forbids help from describing the mechanism (its scenario at line 1361).
Until archive, the live main spec still carries that sentence; the post-archive grep is a workflow
follow-up, not a task here.
