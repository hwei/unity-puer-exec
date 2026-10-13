## 1. Confirm the remaining gap

- [x] 1.1 Enumerate every `GUIDANCE_MATRIX` candidate whose `argv_template` names `--project-path`, and mark which target commands accept `--base-url`. Verify: the list names each candidate, its status key, and whether it is convertible.
- [x] 1.2 Reproduce the gap for `wait-for-exec --base-url` returning `running` and `exec --base-url` returning `completed` (mocked transport). Verify: reproduced on the caller-visible response, not inferred.

## 2. Convert the convertible candidates

- [x] 2.1 Add a `--base-url` `argv_templates` variant to the `("wait-for-exec", "running")` candidate. Verify: a base-url running response carries a `--base-url` argv, and the project-path argv is unchanged.
- [x] 2.2 Add selector-keyed variants to every remaining candidate whose target and originating commands both accept `--base-url`, and leave the rest unchanged. Verify: the project-path-only `get-log-briefs`, `get-blocker-state`, and `resolve-blocker` candidates keep the authored form, and a `resolve-blocker` response gains no base-url variant.
- [x] 2.3 Reconcile the durable success-path error-sweep requirement and this delta so a project-path-only `get-log-briefs` keeps its candidate and omits `argv` under `--base-url`. Verify: the durable text no longer demands a complete invocation for a selector the command rejects.

## 3. Validation and Closeout

- [x] 3.1 Add regression coverage driven by the derived candidate list: for every converted candidate under both selectors, assert `argv` is present, names the right selector, differs only by the selector tokens, and uses only flags the target parser accepts; add negative assertions for `get-log-briefs` (argv omitted) and `resolve-blocker` (no base-url variant), plus a drift test pinning the project-path-only set against the live parser. Verify: base-url assertions fail without 2.1/2.2, and project-path assertions pin the unchanged form.
- [x] 3.2 Run `tests.test_unity_session_cli`, `tests.test_unity_session_modules`, and `tests.test_openspec_spec_hygiene`. Verify: green, no pre-existing guidance guarantee relaxed.
- [x] 3.3 Run `openspec validate restore-base-url-argv-for-remaining-continuations --strict` and `openspec validate --all`. Verify: the delta matches the implemented behavior.
- [x] 3.4 Complete the required apply closeout review and record the finding with allowed categories, separating it from the guidance-record rule and the harness follow-ups.

## Closeout

**Finding: New follow-up candidates identified** (surfaced for human discussion; not promoted
into work).

- `product-improvement` — `get-log-briefs` still has no base-url form, so a base-url `exec` /
  `wait-for-exec` / `wait-for-log-pattern` `completed` response can only advertise the error
  sweep without a runnable invocation. This change deliberately kept the candidate and omitted
  `argv` (design Decision 3); giving the command a base-url log path (for example by resolving
  the log source over the transport) is separate work.
- `validation-gap` — the conversion set is command-level. Statuses that are project-scoped
  (`unity_start_failed`, `unity_stalled`, `unity_not_ready`) are produced only by the
  project-path path, so a base-url variant added to their continuations is currently
  unreachable: it renders and is covered, but no validation distinguishes a live variant from a
  dead one.

**Explicitly not follow-ups from this change:**

- The `wait-for-exec --request-id` record-presence rule was settled by
  `2026-10-13-restore-base-url-exec-continuation-guidance` and is unchanged here.
- The harness watched-extension-set work and the play-mode transport-reset flake have their own
  changes (`consolidate-watched-extension-set-in-harness`,
  `reproduce-play-mode-transport-reset-flake`).
- `refresh_unsettled` is base-url-only by construction — the runtime emits it only for
  `selector == "base_url"` — so its base-url-only templates are correct, not a gap.
- The `resolve-blocker` completed candidate was excluded, not deferred: `resolve-blocker` is a
  project-path-only command, so a base-url variant would be dead code.

**Evidence:** `python -m unittest discover -s tests` → 723 tests OK (3 skipped);
`tests.test_unity_session_cli` (244), `tests.test_unity_session_modules`, and
`tests.test_openspec_spec_hygiene` green inside that run;
`openspec validate restore-base-url-argv-for-remaining-continuations --strict` clean;
`openspec validate --all` → 34 passed, 0 failed. A before/after snapshot (`.tmp/probe_snapshot.py`)
shows project-path rendered `argv` is byte-identical across all 127 continuation candidate
instances (every `(matrix, source command, status, target command)` key in both matrices — not a
scope change from the 66 candidates carrying an `argv_template`, of which 48 were
command-convertible and 47 reachable), and a base-url probe confirms every converted candidate
renders for both selectors with no flag its command rejects.
