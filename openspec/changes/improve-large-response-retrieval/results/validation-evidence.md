# Host Validation Evidence

Real-host validation on Unity 2022.3.62f2 (Mono), validation host
`c3-client-tree2/Project`, 2026-07-21. Unity exe resolved at
`E:\Program Files\Unity\Hub\Editor\2022.3.62f2\Editor\Unity.exe`.

## Host wiring note — embedded package shadowing had to be resolved twice

The host's `Packages/manifest.json` did not reference the repository-local
package at all; instead `Packages/com.txcombo.unity-puer-exec/` contained a
git-tracked embedded copy (with a prebuilt `CLI~/unity-puer-exec.exe`), which
Unity Package Manager treats as authoritative regardless of `manifest.json`.
`tools/prepare_validation_host.py --project-path <Project>` (no `--dry-run`)
rewrote the manifest to `file:../../../unity-puer-exec/packages/com.txcombo.unity-puer-exec`
and reported `embedded_package_shadowing: false`.

That first fix was insufficient: **renaming** the embedded folder in place
(`com.txcombo.unity-puer-exec` → `com.txcombo.unity-puer-exec.shadowed-aside`)
did not stop Unity from treating it as the embedded package — UPM discovers
embedded packages by scanning every folder directly under `Packages/` for a
`package.json` and reads the package name from inside it, independent of the
containing folder's name. `Packages/packages-lock.json` confirmed this:
`"com.txcombo.unity-puer-exec": {"version": "file:com.txcombo.unity-puer-exec.shadowed-aside", "source": "embedded"}`.
The completion-log format observed after this first attempt was still the
pre-fix `result={...}` shape, proving Unity was still compiling the old
embedded copy despite the renamed folder.

Fix: the folder had to be moved **out of `Packages/` entirely** (relocated to
`c3-client-tree2/.puer-exec-embedded-backup/com.txcombo.unity-puer-exec`, sibling
to `Project/`, not inside it). After that, `packages-lock.json` re-resolved to
`"version": "file:../../../unity-puer-exec/packages/com.txcombo.unity-puer-exec", "source": "local"`
and Editor.log stack traces showed frames rooted at
`F:/C3/unity-puer-exec-workspace/unity-puer-exec/packages/com.txcombo.unity-puer-exec/Editor/...`,
confirming the repository's own source was compiled. The embedded copy is
preserved intact at the backup path (not deleted) and should be restored to
`Project/Packages/com.txcombo.unity-puer-exec/` — with the manifest change
reverted — once this validation-only wiring is no longer needed.

## Follow-up finding (out of scope for this change) — observed exec misroute, root cause not isolated

Before the host was properly wired, `exec --project-path c3-client-tree2/Project`
was issued while an unrelated `c3-client-game2/Project` Editor was already
running on the control-service preferred port (55231, `unity_pid=57896`).
The `exec` call completed against that endpoint instead of launching or
locating `c3-client-tree2`'s own Editor: the accepted response's
`session_marker` matched game2's `/health` session_marker exactly, and the
CLI persisted `Temp/UnityPuerExec/session.json` under `c3-client-tree2/Project`
recording game2's `base_url`/`unity_pid`/`session_marker` under tree2's
`project_path` field, even though `/health` on port 55231 reported
`"project_path": "F:\\C3\\c3-client-game2\\Project"`.

This is recorded as an **observed misroute symptom**, not a diagnosed root
cause — `unity_session.py`'s `ensure_session_ready` / discovery path was not
read or debugged, and no code change was made for it (out of scope for this
change). In particular it is not yet known whether the cause is specific to
`exec`'s discovery path, or whether it also affects `get-log-source` (whose
`--project-path` invocation on the same host, before this incident, returned
the shared default Editor.log path and the preferred-port `base_url` with no
tree2 session yet on record — which may be the documented default-path
fallback behavior in `log-brief`'s log-source-resolution contract rather than
a bug, since no session artifact existed at that point). No project assets
were mutated by the misrouted script (pure computation, no Unity API calls).
Logged as a `product-improvement` follow-up candidate for human disposition
at apply closeout; not fixed here.

## 5.1 — Large Unicode result through `--response-file`

Script returned a 500-element array of objects containing CJK text and an
emoji character.

```
unity-puer-exec exec --project-path <tree2/Project> --unity-exe-path <exe> \
  --code "export default function run(ctx) { const items = []; for (let i = 0; i < 500; i++) { items.push({ i, name: '项目' + i, emoji: '😀' }); } return { request_id: ctx.request_id, items }; }" \
  --wait-timeout-ms 120000 \
  --response-file .tmp/real-host-response-file/exec-large.json
```

Response:
```json
{"ok": true, "status": "completed", "request_id": "f016e31e8f2440a8a3ded6a5a0dd976a", "session_marker": "06bb1a0fe67940778b71dd25bb0b56bf", "response_file": {"path": "F:\\C3\\unity-puer-exec-workspace\\unity-puer-exec\\.tmp\\real-host-response-file\\exec-large.json", "encoding": "utf-8", "byte_count": 32175, "sha256": "c4f5a9bc205aaabb5d84345ce02aa605f3d70a03f8ff337d9deb5c17eaa2956d"}}
```

Verified independently in Python: re-reading the stored file, recomputing
`len(bytes)` and `sha256(bytes)` matched the reference exactly; `json.load`
parsed cleanly with 500 items; `items[0].name == '项目0'`; `log_range` and
`brief_sequence` were present in the stored envelope.

Editor.log completion line for this request — bounded, no payload echo:
```
[UnityPuerExec] Complete request=f016e31e8f2440a8a3ded6a5a0dd976a result_bytes=21839
```
(Prior to fixing the package wiring, the same scenario against stale compiled
code produced the old unbounded `result={...500 full items...}` line — see
the wiring note above. `result_bytes` differs from the response-file's stored
byte count because it is the raw un-escaped UTF-8 length of the script's
`JSON.stringify` result on the C# side, before the CLI's `ensure_ascii=True`
re-encoding and envelope wrapping.)

## 5.2 — `exec` then `wait-for-exec --response-file` recovers without re-executing

Script increments a `ctx.globals` counter and returns it, so a second
execution would be observable as `invocationCount: 2`.

```
unity-puer-exec exec --project-path <tree2/Project> --unity-exe-path <exe> \
  --request-id R-recover-once \
  --code "export default function run(ctx) { ctx.globals.__recoverCounter = (ctx.globals.__recoverCounter || 0) + 1; return { request_id: ctx.request_id, invocationCount: ctx.globals.__recoverCounter }; }" \
  --wait-timeout-ms 30000
```
```json
{"...": "...", "status": "completed", "request_id": "R-recover-once", "result": {"request_id": "R-recover-once", "invocationCount": 1}, ...}
```

```
unity-puer-exec wait-for-exec --project-path <tree2/Project> \
  --request-id R-recover-once --wait-timeout-ms 10000 \
  --response-file .tmp/real-host-response-file/recovered.json
```
```json
{"ok": true, "status": "completed", "request_id": "R-recover-once", "response_file": {"byte_count": 367, "sha256": "1cfbf9451634419e6d01c30bee7cbd2a516a7822e45095afb4f37c8d96aca709", ...}}
```

Recovered file content: `"result": {"request_id": "R-recover-once", "invocationCount": 1}` —
`invocationCount` is still `1`, confirming `wait-for-exec` recovered the
retained terminal response instead of re-running the script.

## 5.3 — Long Unicode log entry via `get-log-briefs --full-text --response-file`

Script emitted one `console.log` line combining a CJK sentence (repeated
3x, well over 100 characters), an emoji, and a request-id marker.

```
unity-puer-exec get-log-briefs --project-path <tree2/Project> \
  --range 90414-102284 --include 3 --full-text \
  --response-file .tmp/real-host-response-file/full-text-brief.json
```
```json
{"ok": true, "status": "completed", "operation": "get-log-briefs", "response_file": {"byte_count": 2800, "sha256": "4a1c5aaf10773f7fbb02e58a6fa0f7b6370c0fa360a54697d2dcecc76a1fe200", ...}}
```

Stored file: brief index 3's `text` preview remained the truncated ~100-char
form; `full_text` (1493 characters) contained the complete entry — the full
repeated CJK sentence, the emoji, and the trailing `end-marker-<request_id>` —
plus the entry's stack-trace continuation lines and `(Filename: ...)` footer,
all recovered without any manual Editor.log byte-seeking. Re-reading the
stored file and recomputing byte count/sha256 matched the reference exactly.

## Summary

| Scenario | Result |
|---|---|
| 5.1 large Unicode `exec --response-file` | PASS |
| 5.2 `wait-for-exec --response-file` recovery, no double execution | PASS |
| 5.3 `get-log-briefs --full-text --response-file` exact retrieval | PASS |
| Bounded Unity completion log (no payload echo) | PASS (confirmed via 5.1 Editor.log line) |
