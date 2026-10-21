# Proposal

## Why

GitHub issue hwei/unity-puer-exec#1 reports two project-mode defects seen with two Editors open on one machine and a relative `--project-path Project`:

1. `stop` keeps returning `status: running`, `play_state: null` until its timeout even though `EditorApplication.isPlaying` is already `false`.
2. `get-blocker-state` reports a `session` whose `base_url` belongs to the other project's Editor while `unity_pid` belongs to the target project.

Both are confirmed in code. Neither involves the C# package.

- **Bug 1:** the project-mode play-state probe finds its endpoint only by a control-port scan that matches the health `project_path` against the raw `--project-path`. The two strings are compared after `normpath`/`normcase` only. The health value is absolute (the parent of `Application.dataPath`). A relative argument therefore never matches, so `play`/`pause`/`stop` never see their target state. `exec` hides the defect because it confirms the publication first.
- **Bug 2:** `get-blocker-state` and `resolve-blocker` build their session with the hard-coded default port, while `unity_pid` comes from the project's publication. Blocker detection is keyed on the pid, so it already targets the right Editor. The reported session is wrong, though, and misleads anyone who reuses its `base_url`.

## What Changes

- Project-path identity matching becomes relative/absolute and spelling insensitive. A `--project-path` is resolved to an absolute path once at entry, and the health `project_path` comparison uses the same realpath-based equality that publication confirmation already uses.
- The project-mode play-state probe resolves the endpoint from the Editor's publication first (session-marker confirmed) and falls back to the identity scan only when the publication cannot be confirmed. This matches how readiness waits already resolve endpoints.
- When a play-mode command's budget runs out without any project-owned endpoint answering, the `running` payload says so. The caller can then tell "the endpoint could not be resolved" apart from "the transition has not finished", rather than reading `play_state: null` as still playing.
- The `session` that `get-blocker-state` and `resolve-blocker` report takes `base_url`, `unity_pid` and `project_path` from the same publication. With no publication, `base_url` is reported as `null` and never as the default port.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `editor-session-discovery`: adds requirements that a caller's relative project path identifies the same project as its absolute form, and that a reported session triple always comes from one publication.
- `play-mode-control`: adds requirements that play-mode commands resolve the endpoint publication-first, and that an unresolved endpoint is reported distinctly from an unfinished transition.

## Impact

- `cli/python/unity_session.py`: `_payload_matches_project`, `resolve_project_path` callers, and `get_blocker_state`.
- `cli/python/unity_puer_exec_runtime.py`: `_play_probe_endpoint`, `_wait_for_play_state`, and `_play_running_result`.
- `cli/python/help_surface.py`: the `running` guidance text for `play`/`pause`/`stop`.
- Tests: `tests/test_unity_session.py` and `tests/test_unity_session_cli.py`.
- No C# or protocol change. No CLI flag change. The `session.project_path` value in payloads becomes absolute.
