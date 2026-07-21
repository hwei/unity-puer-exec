# Host Validation Evidence

Real-host confirmation of the fix, 2026-07-21, using the existing validation
host `c3-client-tree2/Project` and a second, already-running, unrelated
project `c3-client-game2/Project` (both under `F:\C3`).

## Environment

`c3-client-game2`'s Unity Editor (pid `43400`) was already running
interactively and its control service was `ready` on the preferred port
`55231`, reporting `"project_path": "F:\\C3\\c3-client-game2\\Project"` —
exactly the precondition that produced the original real-host misroute
(see `openspec/changes/archive/2026-07-21-improve-large-response-retrieval/results/validation-evidence.md`).
`c3-client-tree2/Project` had no session artifact and its own Editor was not
running.

`c3-client-tree2/Project`'s `Packages/manifest.json` was wired to the
repository-local package (`tools/prepare_validation_host.py --project-path
<Project>`, no `--dry-run`) and the embedded
`Packages/com.txcombo.unity-puer-exec` copy was moved out to a sibling
backup directory (embedded packages shadow the `manifest.json` dependency
regardless of rename, per the prior change's validation notes) so the run
exercised the current repository's fixed code. Both changes were reverted
after the run (`git checkout -- Project/Packages/manifest.json`, embedded
folder moved back) — `git status` on `c3-client-tree2` is clean.

## Command

```
unity-puer-exec exec --project-path <c3-client-tree2/Project> \
  --unity-exe-path "E:\Program Files\Unity\Hub\Editor\2022.3.62f2\Editor\Unity.exe" \
  --code "export default function run(ctx) { return { request_id: ctx.request_id, marker: 'tree2-real-host-check' }; }" \
  --wait-timeout-ms 30000
```

## Result

```json
{"ok": true, "status": "running", "operation": "exec", "request_id": "b9c182464ab24b79b9c860383577c995", "session": {"owner": "project_recovery", "launched": false, "base_url": "http://127.0.0.1:55231", "project_path": "F:\\C3\\unity-puer-exec-workspace\\c3-client-tree2\\Project", "unity_pid": 43400}, ...}
```

`ensure_session_ready` raised `UnityNotReadyError` internally (the resolver
never matched game2's identity to tree2's `project_path`, so the fixed wait
loop correctly refused to accept game2's `ready` health as tree2's own). The
CLI's existing not-ready/stalled handling in `run_exec` caught that and
returned a `status: "running"` pending-exec response instead of a false
`completed` result — the script was never sent to game2, and no result was
ever produced from it.

Confirmed directly against the filesystem:

- `c3-client-tree2/Project/Temp/UnityPuerExec/session.json` — **does not
  exist**. No session artifact was persisted for tree2 recording game2's
  `base_url`/`unity_pid`/`session_marker`. This is the exact artifact
  corruption the original incident produced; it did not reproduce here.
- Only a `pending_exec/<request_id>.json` retry-bookkeeping file was written
  (removed after the check) — expected CLI behavior for a not-yet-ready
  session, unrelated to endpoint identity.

## Known, separately-tracked limitation surfaced by this same run

The returned `session.base_url`/`unity_pid` in the "running" diagnostics
still display game2's values (`55231`/`43400`) even though no misroute
occurred — these are diagnostic fields on the pre-wait `project_recovery`
session object attached to the timeout exception, not a claimed/persisted
endpoint. Separately, because `_list_unity_pids()` is not project-scoped,
`ensure_session_ready` treats *any* running Unity Editor (including game2's,
unrelated to tree2) as a "recoverable signal" and enters a recovery wait
instead of launching tree2's own Editor — so while game2 keeps running,
repeated `exec`/`wait-for-exec` calls against tree2 will keep timing out
rather than ever launching tree2. This trades the prior silent
wrong-project execution for a loud, safe timeout, which is the correct
priority, but it is a real usability gap in the "unrelated project already
running, no local artifact" case. Logged as a `product-improvement`
follow-up candidate at apply closeout (see design.md's Decisions section);
not fixed by this change.

## Summary

| Check | Result |
|---|---|
| `exec` against tree2 while an unrelated project (game2) is `ready` on the preferred port, no tree2 artifact | Does not misroute — no false `completed` result, no wrong session persisted |
| `Temp/UnityPuerExec/session.json` under tree2 after the run | Absent (previously: recorded game2's endpoint under tree2's `project_path`) |
| Host state after validation | Restored (`git status` clean on `c3-client-tree2`) |
