## 1. Guidance matrix data

- [x] 1.1 Define the `GUIDANCE_MATRIX` data structure in `help_surface.py`, keyed by `(command, status)`, with `next_steps` (list of `{command, argv_template?, when}`) and `situation` (optional string) per entry
- [x] 1.2 Populate the matrix for `exec` across all statuses: `running`, `completed`, `modal_blocked`, `busy`, `not_available`, `request_id_conflict`, `launch_conflict`, `unity_start_failed`, `unity_stalled`, `unity_not_ready`, `failed`
- [x] 1.3 Populate the matrix for `wait-for-exec` across all statuses: `running`, `completed`, `modal_blocked`, `missing`, `not_available`, `launch_conflict`, `unity_start_failed`, `unity_stalled`, `unity_not_ready`, `failed`
- [x] 1.4 Populate the matrix for observation commands: `wait-for-log-pattern`, `wait-for-result-marker` across all their statuses
- [x] 1.5 Populate the matrix for readiness and stop commands: `wait-until-ready`, `ensure-stopped` across all their statuses
- [x] 1.6 Populate the matrix for blocker commands: `get-blocker-state`, `resolve-blocker` across all their statuses
- [x] 1.7 Populate the matrix for info commands: `get-log-briefs` (`completed` → tip about `get-log-source`), `get-log-source` (no guidance)

## 2. Guidance lookup function

- [x] 2.1 Implement `build_next_steps(command, status, context)` in `help_surface.py` that looks up the matrix and constructs concrete `argv` arrays where possible using the `context` dict (project_path, request_id, etc.)
- [x] 2.2 Implement `build_situation(command, status)` in `help_surface.py` that returns the situation string or `None`

## 3. Global --suppress-guidance flag

- [x] 3.1 Add `--suppress-guidance` to the top-level parser in `unity_puer_exec_surface.py` as a global flag parsed before the subcommand
- [x] 3.2 Pass the flag value through to the runtime entry point so command handlers can access it

## 4. Runtime integration

- [x] 4.1 Replace `_next_step_payload()` in `unity_puer_exec_runtime.py` with calls to `build_next_steps()` and `build_situation()`
- [x] 4.2 Update `_emit_running_payload()` to emit `next_steps` (array) instead of `next_step` (object)
- [x] 4.3 Update `_normalize_exec_lifecycle_body()` to emit `next_steps` instead of `next_step`
- [x] 4.4 Add `next_steps` and `situation` emission to all other command handler response paths that have guidance matrix entries (wait-for-exec, wait-for-log-pattern, wait-for-result-marker, wait-until-ready, ensure-stopped, get-blocker-state, resolve-blocker, get-log-briefs)
- [x] 4.5 Suppress both fields when `--suppress-guidance` is active

## 5. Help surface expansion

- [x] 5.1 Expand `render_command_status_help()` in `help_surface.py` to include situation-level explanations for each non-success status
- [x] 5.2 Add `--suppress-guidance` description to the top-level help output with a note that `--help-status` remains available as a fallback
- [x] 5.3 Add `--suppress-guidance` to the per-command `--help-args` output for discoverability

## 6. Spec updates

- [x] 6.1 Apply delta spec changes to `openspec/specs/formal-cli-contract/spec.md` (continuation hint requirement updated, help-status scenario added)
- [x] 6.2 Create `openspec/specs/runtime-guidance/spec.md` as a new durable spec

## 7. Validation

- [x] 7.1 Verify `exec → running` response includes `next_steps` array with three candidates and no `next_step` singular field
- [x] 7.2 Verify `exec → modal_blocked` response includes both `situation` and `next_steps`
- [x] 7.3 Verify `exec → not_available` response includes `situation` and no `next_steps` (or empty array)
- [x] 7.4 Verify `--suppress-guidance` omits both `next_steps` and `situation` from a response that would normally include them
- [x] 7.5 Verify `exec --help-status` output now includes situation explanations for non-success statuses
- [x] 7.6 Spot-check at least two other commands (e.g., `wait-for-exec → modal_blocked`, `get-blocker-state → modal_blocked`) for correct guidance emission
