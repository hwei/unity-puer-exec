# Tasks

## 1. Project path identity

- [x] 1.1 Make `unity_session_env.resolve_project_path` return an absolute path for an explicit argument and for `UNITY_PROJECT_PATH` (design D1). Verify with a new `tests/test_unity_session_modules.py` (or `test_unity_session.py`) case: a relative argument resolves against cwd. Update any existing assertion on a literal relative `session.project_path`.
- [x] 1.2 Make `unity_session._payload_matches_project` delegate to `unity_session_endpoint.paths_equal` (design D2). Verify with new `tests/test_unity_session.py` cases. A relative path matches the absolute forward-slash `Application.dataPath`-style value from its parent cwd. A different project's absolute path still does not match.
- [x] 1.3 Add a `discover_project_endpoint` regression test with a relative project path and a mocked health probe. Verify it returns the project-owned candidate and skips a ready foreign-project candidate on the preferred port.

## 2. Play-mode probe resolution

- [x] 2.1 Build one `_make_published_endpoint_resolver` per project-mode play-mode invocation and use it in `_play_probe_endpoint` (and therefore `_post_play_mode`, `_wait_for_play_state` and `_stop_wait_for_compile`) (design D3). Verify with a `tests/test_unity_session_cli.py` `stop` case using a relative `--project-path`. The publication's base URL changes and its marker rotates mid-wait. The command must return `status: completed` with `play_state: edit`.
- [x] 2.2 Add a `tests/test_unity_session_cli.py` case with two ready endpoints. The foreign project is `playing` on the preferred port and the target project is `edit` on its published port. Verify that `stop` for the target completes from the target's state and never reports the foreign state.
- [x] 2.3 Track whether any probe resolved a project-owned endpoint. Add `result.target_play_state` and `result.endpoint_resolved` to `_play_running_result`, and add the distinct unresolved-endpoint guidance `situation` in `help_surface.py` (design D4). Verify with CLI tests for both `running` shapes (resolved/unfinished and unresolved), and with the help-surface test that renders `stop`'s status text.

## 3. Blocker session coherence

- [x] 3.1 Make `get_blocker_state` take `base_url` from the publication, or `None` when there is none (design D5). Verify with `tests/test_unity_session.py` cases. With a publication on a non-default port, the session reports that port and the published pid. With no publication, `base_url` is `None` and `to_payload()` emits `null`.
- [x] 3.2 Update the `get-blocker-state` / `resolve-blocker` help text to state that `session.base_url` is the project's published endpoint and may be `null`. Verify the existing help-surface tests still pass and the text appears in `unity-puer-exec get-blocker-state --help`.

## 4. Integration validation

- [x] 4.1 Run the default mocked suite listed in `openspec/specs/validation-host-integration/how-to-run.md` and `openspec validate fix-project-path-endpoint-resolution --strict`. Verify both pass.
- [x] 4.2 Real-host check on the validation host, with a second Editor open for another project if one is available: run `play` → `stop` with a relative `--project-path`, then `get-blocker-state`. Verify that `stop` returns `completed` / `play_state: edit` and that the `session` triple is self-consistent. Record the transcript and set `meta.yaml` `evidence: tests, host-validation`.

## Workflow follow-up

- Comment on hwei/unity-puer-exec#1 with the root causes and the fixing version once released, then close it.
- Archive the change after review.
