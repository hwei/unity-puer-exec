## 1. Characterise the hidden compile

- [x] 1.1 Reproduce on the validation host: force `recompile_after_finished_playing`, enter play mode, touch a real `.cs`, exit play mode, and record `/health` over the whole window (statuses, `refresh.pending`, reachability) plus the `SessionState` settle timestamp. Verify: the record shows whether `pending` clears during the reload or after it, and whether the settle timestamp advances across the reload.
- [x] 1.2 Determine the listener's exact downtime relative to compile start/finish from the project-private `Editor.log` (`beforeAssemblyReload` stop, `Reloading assemblies`, `AssetDatabase: script compilation time`). Verify: the timeline shows whether any `compiling` window exists that a fast poller could catch.
- [x] 1.3 Test the candidate signals against the record: can a baseline taken before play exit (pending state, settle timestamp, or a new epoch) distinguish "compiled across the reload" from "nothing compiled"? Verify: each candidate is marked usable / unusable with the reason.

## 2. Choose an approach

- [x] 2.1 Decide between a server-side compile epoch, the persisted settle timestamp, and a CLI-driven baseline. Verify: `design.md` records the chosen approach, its limits, and the rejected alternatives with reasons.
- [x] 2.2 Decide the caller-facing outcome: keep `compile_settled` (with the edge inferred) versus a distinct state. Verify: the decision respects the existing `compile-wait` contract ("an initial `ready` is never terminal before an edge is observed") or states how it is amended.
- [x] 2.3 State explicitly whether a caller that starts after the reload can ever be satisfied, or whether the requirement is scoped to the CLI-driven sequence. Verify: the scope is written down, not implied.

## 3. Recommendation and hand-off

- [x] 3.1 If a reliable signal exists, update the change to a `feature` with durable `compile-wait` requirements and implementation tasks; if not, record the limitation and close the spike with the finding. Verify: the change type and artifacts match the conclusion. — A reliable signal exists (compile generation on `compilationFinished`, persisted across the reload). Per repository convention the implementation is carried by the follow-up change `add-compile-generation-signal`; this spike closes with its finding.
- [x] 3.2 Record the investigation result in `design.md`. Verify: a reader can see the timeline, the signal comparison, and the chosen path.
- [x] 3.3 Run `openspec validate observe-compile-across-domain-reload`. Verify: green.
