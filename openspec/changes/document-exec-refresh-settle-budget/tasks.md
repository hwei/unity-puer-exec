## 1. Confirm the claim that is missing and where it belongs

- [ ] 1.1 Read the `exec` help surface end to end (`cli/python/help_surface.py`: the option list, the "Automatic refresh" line, "Timeout Rules", and the `--help-status` status section) and name every sentence from which a caller could infer that `--wait-timeout-ms` bounds an automatic refresh's settle. Verify: the finding lists the exact sentences and the surface each appears on, not a general impression.
- [ ] 1.2 Confirm the two budgets in code: the per-request wait the server holds (`--wait-timeout-ms` in `_run_exec_impl` / `direct_exec_client`) and the compile-scale settle (`_post_refresh_ready_timeout_seconds` after `diagnose-exec-missing-after-auto-refresh`). Verify: the finding cites both call sites and states which constant the settle uses.
- [ ] 1.3 Decide the surfaces and the wording: which `exec` sections carry the statement, whether `--help-status` needs its own sentence or only consistency, and whether any literal number is named (see `design.md` Decision 1). Check `wait-for-compile --help`'s `--settle-timeout-seconds` wording first. Verify: the decision covers `--help` and `--help-status`, and states why a literal is or is not used.
- [ ] 1.4 Enumerate the existing help-content assertions that touch these strings so none is relaxed to make room for the new text. Verify: the list names each test case and the guarantee it holds.

## 2. State it on the help surfaces

- [ ] 2.1 Add the statement to the `exec` help surface so it appears in the wait or timeout guidance as well as the automatic-refresh description. Verify: `exec --help` read as plain text carries both facts — the settle has its own compile-scale budget, and `--wait-timeout-ms` does not bound it.
- [ ] 2.2 Make `exec --help-status` consistent, adding a sentence only if its status section would otherwise imply the opposite. Verify: the status surface does not imply `--wait-timeout-ms` bounds a refresh settle.
- [ ] 2.3 Leave `wait-for-compile --help`'s `--settle-timeout-seconds` wording describing the same cycle, adjusting only if the two surfaces now disagree. Verify: both surfaces describe one compile cycle, consistently.
- [ ] 2.4 Add regression assertions on the new statement to the help-content tests, and review each pre-existing assertion from 1.4 rather than deleting any. Verify: the new assertions fail without 2.1, and no pre-existing help guarantee was dropped.

## 3. Validation and Closeout

- [ ] 3.1 Run the focused Python suites covering the help surfaces and the CLI contract (`tests.test_unity_session_cli`, `tests.test_cli_version`, `tests.test_openspec_spec_hygiene`). Verify: green.
- [ ] 3.2 Capture the `exec --help` and `exec --help-status` output as the change's evidence. Verify: the transcript shows both facts, so the evidence is readable without running the CLI.
- [ ] 3.3 Run `openspec validate document-exec-refresh-settle-budget` and confirm the change is archive-ready. Verify: the added requirement carries a `SHALL` and at least one `#### Scenario:` so `tests.test_openspec_spec_hygiene` accepts it.
- [ ] 3.4 Complete the required apply closeout review and record either `No new follow-up work identified` or human-discussed follow-up candidates in an allowed category. Verify: the closeout separates this documentation gap from `make-base-url-exec-refresh-recoverable` and from the intermittent launch-recovery and CLI empty-response flakes.
