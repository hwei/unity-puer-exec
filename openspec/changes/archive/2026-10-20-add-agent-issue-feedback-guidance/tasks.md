# Tasks

## 1. Feedback help surface

- [x] 1.1 Add a shared issue-tracker URL constant and a `render_feedback_help()` renderer in `cli/python/help_surface.py` covering: confirm with user before filing, public-tracker redaction (project paths, project code, asset names, unapproved logs), duplicate search then comment, report contents (`--version`, command line, status + exit code, expected vs actual, repro), prefilled `issues/new?title=&body=` fallback when `gh` is unavailable, and friction as reportable
- [x] 1.2 Add a one-bullet `Feedback` section to `render_top_level_help()` pointing at `unity-puer-exec --help-feedback`
- [x] 1.3 Handle `--help-feedback` in `cli/python/unity_puer_exec_surface.py` beside `--help-example` (exit 0, no selector, no Unity contact; extra args → usage error)
- [x] 1.4 Tests in `tests/test_unity_session_cli.py`: top-level help has the one-bullet pointer and no procedure text; `--help-feedback` exits 0 and contains the confirmation gate, tracker URL, redaction list, duplicate search, report fields, fallback URL, friction; extra args rejected

## 2. failure_origin classification

- [x] 2.1 Set `failure_origin: "cli_internal"` in the unclassified-exception handler in `cli/python/unity_puer_exec_runtime.py`
- [x] 2.2 In the `HTTPError` branch of `direct_exec_client.invoke_command`, read the body defensively and set `failure_origin: "service_internal"` only for code 500 with JSON `error == "internal_error"`; keep `status`, `http_status`, and exit code unchanged
- [x] 2.3 Trace that the service-internal payload reaches `_attach_guidance` with the field intact on project-path and base-url paths (including `wait-for-exec` and play-mode post paths); fix any path that rebuilds the payload and drops it
- [x] 2.4 Tests: uncaught exception → `cli_internal`, exit 1; HTTP 500 + `internal_error` → `service_internal` with status/exit unchanged; HTTP 500 with empty / non-JSON / other error → no field; script `failed`, `invalid_arguments`, `not_available` (connection refused), `refresh_unsettled` → no field

## 3. Feedback hint composition

- [x] 3.1 In `_attach_guidance`, when `failure_origin` is present, append the `--help-feedback` `next_steps` candidate (`command` = invoked command, `argv` = `["unity-puer-exec", "--help-feedback"]`) after matrix candidates and append the hint sentence to `situation`
- [x] 3.2 Tests: hint and candidate present with matrix candidates preserved; absent without `failure_origin`; `--suppress-guidance` keeps `failure_origin` but drops `next_steps`/`situation`
- [x] 3.3 Confirm the existing guidance-matrix coverage / live-surface tests still pass with the new candidate (`--help-feedback` is accepted by the CLI surface)

## 4. Repository and docs

- [x] 4.1 Add `.github/ISSUE_TEMPLATE/bug.yml`, `friction.yml`, and `config.yml` (blank issues enabled) with fields matching the `--help-feedback` report contents plus a "filed by an agent on the user's behalf" checkbox
- [x] 4.2 Add one Usage sentence mentioning `unity-puer-exec --help-feedback` to `README.md` and the matching translation to `README.zh-CN.md`

## 5. Validation and closeout

- [x] 5.1 Run the full unit test suite (`openspec/specs/validation-host-integration/how-to-run.md`) and record the result
- [x] 5.2 Manual check: run the built CLI with `--help`, `--help-feedback`, and a forced internal failure; record transcripts in the closeout
- [x] 5.3 `openspec validate add-agent-issue-feedback-guidance --strict`; update `meta.yaml` `updated_at`/`evidence`; write the apply closeout summary
