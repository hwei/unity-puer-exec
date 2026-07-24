## Context

The evidence for this change was produced while validating `enforce-cli-version-compatibility` against the real host on 2026-07-23.

- Two Unity Editors were running, neither launched with `-logFile`: PID 85632 on the validation host `c3-client-tree2\Project`, and PID 9560 on the unrelated `c3-client-tree3\Project`. Both were therefore bound to the per-user `%LOCALAPPDATA%\Unity\Editor\Editor.log`.
- The file the CLI read contained `0` occurrences of `[UnityPuerExecResult]` immediately after the validation host had logged one, and `1` occurrence of `[UnityPuerExec] Ready on port` where two live bridges should have produced two. The offsets the CLI was handed (~19.4 MB) exceeded the file's actual size (3.0 MB).
- `test_exec_checkpoint_observation_chain_against_real_host` fails reproducibly under this condition. A stashed pre-change baseline established the failure predates the version-guard work, which is what reclassified it from "regression" to "the harness is reading the wrong file".

Two independent defects sit underneath that observation.

**The path is guessed, not asked for.** `unity_session_logs.resolve_effective_log_path` falls back to `default_editor_log_path()`, a hardcoded `~/AppData/Local/Unity/Editor/Editor.log`. The bridge meanwhile caches `Application.consoleLogPath` in `UnityPuerExecServer.cachedConsoleLogPath` and uses it only to compute `ReadEditorLogOffset()`. The authoritative value exists inside the product and is never published.

**Offset invalidation is absorbed.** `read_editor_log_chunk` resets `start_offset > file_size` to `0` and rescans from the beginning. A caller holding a `log_range` from before a rotation receives no signal; the symptom is an unexplained wait timeout.

## Goals / Non-Goals

**Goals:**

- Make the running Editor state where it writes, and make the CLI believe that statement over a platform guess.
- Give a CLI-launched project session a log file no other Editor can share.
- Turn a silently-absorbed offset invalidation into a reported condition.
- Make the real-host suite trustworthy on a machine that has other Unity projects open, because that is the normal development machine.

**Non-Goals:**

- Mirroring, tee-ing, or re-emitting Unity log content into a second file. See D2.
- Changing the Unity log format, the log-brief parser, or `brief_sequence` delimiting.
- Isolating the log of an Editor a human opened from Unity Hub. The CLI cannot influence how that process was launched; D4 covers what is achievable there.
- Making the real-host suite pass. The two failures it currently records are diagnosed by this change but their remediation is judged after the log source is trustworthy.

## Decisions

### D1: The bridge publishes `console_log_path` in `/health`

`Application.consoleLogPath` is already cached on the main thread in `RefreshConsoleLogPathCache`. It is added to the ready health payload as `console_log_path` and threaded through `UnityPuerExecProtocol.BuildHealthResponseJson`, alongside the `bridge_version` field added by `enforce-cli-version-compatibility`.

*Rationale.* This is the only value in the system that is correct by construction for the process actually writing the log. Every other source — the platform default, a caller-supplied flag, a session artifact recorded from an earlier guess — is a derived claim that can be stale or wrong.

*Consequence that matters.* It is correct even for an Editor the CLI did not launch, which is the case D4 leaves otherwise unsolved. Isolation and correct resolution are separable, and this decision buys the second one everywhere.

### D2: Isolation comes from `-logFile` at launch, not from mirroring into `Temp/`

Mirroring the log — having the bridge subscribe to `Application.logMessageReceivedThreaded` and append to a project-local file — was considered and rejected.

*Rationale.* That callback delivers only managed-side log messages. Lines that Unity writes natively — `Asset Pipeline Refresh (id=…)`, `<RI> Initialized touch support`, Puerts native output, native crash output — never pass through it, and all of them appear in the real Editor log. `wait-for-log-pattern` is a general regular expression over Unity log output, so a mirror would silently stop matching an entire class of lines while appearing to work. It would also double the write volume on a log that a real game project already floods.

`launch_unity` already accepts `unity_log_path` and emits `-logFile`; the plumbing exists and Unity itself writes the complete stream to it. The change is to supply a project-local default rather than leaving the parameter unset.

*Consequence that matters.* `Application.consoleLogPath` inside an Editor launched this way returns exactly the supplied path, so D1 and D2 compose: the CLI discovers the isolated log automatically and no caller has to thread `--unity-log-path` through every subsequent command.

### D3: Resolution precedence is explicit and additive

```
--unity-log-path (explicit caller intent)
  └─▶ session artifact effective_log_path (established session)
        └─▶ health console_log_path (NEW — the bridge's own statement)
              └─▶ platform default Editor.log (guess, last resort)
```

The new tier sits below both existing authoritative tiers and above the guess, so no currently-working caller changes behavior; only the case that was previously guessing is corrected. `get-log-source` reports which tier produced the answer, so an agent can tell "the Editor told me" from "I assumed".

*Alternative considered.* Placing the health-reported path above the session artifact was rejected: the artifact is what makes observation work before and across health-probe failures, and demoting it would make log resolution depend on service reachability.

### D4: The Hub-launched Editor is addressed by detection, not by isolation

An Editor a human started from Unity Hub has no `-logFile` and will share the per-user log with any other such Editor. D1 makes the CLI read the right file, but two Editors sharing one file still corrupt each other's offsets.

The residual case is therefore handled by making it *visible*: D5's rotation signal fires when offsets are invalidated, and `how-to-run.md` states the concurrent-Editor prerequisite for real-host runs.

*Rationale for not going further.* Detecting "another Editor is bound to my log file" reliably would mean correlating process command lines with log ownership, which is platform-specific and fragile. Naming the condition when its consequence appears is proportionate.

### D5: Offset invalidation is reported, not silently repaired

`read_editor_log_chunk` keeps rescanning from `0` — dropping the read would be worse — but the condition becomes observable in the response rather than inferred from a timeout.

*Rationale.* The failure this change exists to fix presented as a 30-second wait timeout with no diagnostic content, and cost a stashed-baseline bisect to attribute. The information needed to short-circuit that was available at the moment of the read.

## Risks / Trade-offs

- **A caller reading the per-user `Editor.log` directly by path loses sight of a CLI-launched session.** → Intended and marked BREAKING in the proposal. Callers using `get-log-source` or the session artifact are unaffected, and those are the documented paths. The alternative — keeping the shared default — preserves a compatibility that only works when exactly one Editor is open.
- **A project-local log under `Temp/` is discarded when Unity clears `Temp/`.** → Acceptable: the log is an observation surface for a live session, not an archive, and the session artifact is separately persisted. A post-mortem reader who needs a durable log passes `--unity-log-path`.
- **`console_log_path` is sampled on the main thread and read from the listener thread.** → Same pattern already used for `cachedConsoleLogPath` and the stack-trace-logging snapshot; no new concurrency model.
- **The rotation signal could fire on an ordinary first read with a stale artifact.** → The condition is specifically `start_offset > file_size` with a caller-supplied offset, not an absent one; a fresh observation supplies no offset and cannot trip it.
- **Two Editors sharing a log remain broken when neither was CLI-launched.** → Documented limitation (D4), surfaced by D5 rather than silently tolerated.
