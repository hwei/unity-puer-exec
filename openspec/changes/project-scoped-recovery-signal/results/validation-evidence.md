# Host Validation Evidence

Real-host confirmation of the fix, 2026-07-21, using the existing validation
host `c3-client-tree2/Project` and a second, already-running, unrelated
project `c3-client-game2/Project` (both under `F:\C3`), reusing the same
setup as `diagnose-exec-endpoint-misroute`'s prior real-host run.

## Environment

Before this run, four `Unity.exe` processes were already live on the host
(pids `43400`, `38252`, `51600`), including `c3-client-game2`'s Editor
(pid `43400`, confirmed held via `_project_lockfile_is_held` against
`c3-client-game2/Project`). `c3-client-tree2/Project` had no session
artifact and its own lockfile was confirmed **not** held
(`_project_lockfile_is_held` returned `False`) — the exact precondition
that previously caused `ensure_session_ready` to stall instead of launching.

`c3-client-tree2/Project`'s `Packages/manifest.json` was wired to the
repository-local package (`tools/prepare_validation_host.py --project-path
<Project>`, no `--dry-run`) and the embedded
`Packages/com.txcombo.unity-puer-exec` copy was moved out to a sibling
`.bak` directory first, following the same setup as the prior change's
validation run. This change is Python-CLI-only (`_project_lockfile_is_held`
and the `ensure_session_ready` decision it feeds), so the wiring was not
strictly required for this particular fix — the `unity-puer-exec` CLI ran
directly from the repository regardless of which C# package Unity loaded —
but it was kept for consistency with the established recipe.
`embedded_package_shadowing` was confirmed `false` after the rename.
Both changes were reverted after the run (`git checkout -- Packages/manifest.json`,
embedded folder moved back) — `git status` on `c3-client-tree2` is clean.

## Command

```
unity-puer-exec exec --project-path <c3-client-tree2/Project> \
  --unity-exe-path "E:\Program Files\Unity\Hub\Editor\2022.3.62f2\Editor\Unity.exe" \
  --code "export default function run(ctx) { return { request_id: ctx.request_id, marker: 'project-scoped-recovery-signal-real-host-check' }; }" \
  --wait-timeout-ms 30000
```

## Result

```json
{"ok": true, "status": "completed", "request_id": "52f2281fbae44ceead99fce70c4635d4", "session_marker": "361dd0b90fd346438f7faa51969b898a", "result": {"request_id": "52f2281fbae44ceead99fce70c4635d4", "marker": "project-scoped-recovery-signal-real-host-check"}, ...}
```

A new `Unity.exe` process (pid `54712`) appeared on the host immediately
after the `exec` call — `ensure_session_ready` launched tree2's own Editor
instead of entering a recovery wait, even though three unrelated Unity
Editors (including game2's `ready` service) were already running. The
script executed against tree2's own, newly launched Editor and returned
`status: "completed"` with the correct marker — no timeout, no misroute.

`c3-client-tree2/Project/Temp/UnityPuerExec/session.json` confirms the
launched session's identity:

```json
{
  "base_url": "http://127.0.0.1:55232",
  "unity_pid": 54712,
  "project_path": "F:\\C3\\unity-puer-exec-workspace\\c3-client-tree2\\Project"
}
```

`unity_pid` is the freshly launched Editor (not game2's `43400` or any other
pre-existing pid); `base_url` rolled over to `55232` since `55231` was
occupied by another already-running project — both expected, correct
behavior, and unrelated to this change's scope (range-aware discovery,
unchanged).

## Summary

| Check | Result |
|---|---|
| `_project_lockfile_is_held` against a running project (game2) | `True` |
| `_project_lockfile_is_held` against a not-running project (tree2) | `False` |
| `exec` against tree2 while three unrelated Editors are running, no tree2 artifact | Launches tree2's own Editor instead of stalling in a recovery wait |
| `exec` result | `status: "completed"`, correct marker, tree2's own session persisted |
| Host state after validation | Restored (`git status` clean on `c3-client-tree2`) |
