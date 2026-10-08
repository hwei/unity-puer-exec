## 1. Restructure the rollover assertions

- [ ] 1.1 Read the two rollover cases, `_stage_rollover`, `_PreferredPortBinder`, and `_scan_ready_control_endpoint` end to end, and label each assertion in the case bodies by the property it actually tests: P1 (the service is ready on a later port than the preferred one and a project-scoped command discovers it) or P2 (the service rebinds across a domain reload because something took the preferred port in the `Stop()`→`Start()` window). Verify: every assertion is labelled, and the assertions reachable only when the binder won the port are named explicitly.
- [ ] 1.2 Split each case so P1 is asserted unconditionally and P2 only when the staging actually succeeded, and remove the `skipTest` calls that currently fire when the preferred port is held by an unrelated ready service or process. Verify: with another project's ready Editor holding the preferred port, both cases run and assert P1 instead of skipping.
- [ ] 1.3 Record which sub-assertion was not staged in each case's own boundary result, so "asserted P1 only" is distinguishable from "asserted P1 and P2". Verify: a run on a contended host and a run on a free host produce distinguishable boundary records.
- [ ] 1.4 Replace `skipTest("no ready control endpoint for host project; cannot stage rollover")` with a bounded retry followed by a failure that reports the bound launch outcome and the ports probed. Verify: a deliberately broken oracle fails the case with those fields rather than skipping.

## 2. Run instructions and ride-along fidelity

- [ ] 2.1 Correct the skip policy for these cases in `openspec/specs/validation-host-integration/how-to-run.md`, which currently documents the inverted condition ("It `skip`s when `55231` is held by an unrelated process at start"), and make the result-interpretation table's `skip` row match the three-way classification in `design.md`. Verify: the documented policy and the suite's actual behavior agree for all three conditions.
- [ ] 2.2 Rename `_scan_for_project_endpoint_any_status` so its name states the identity rule it can actually apply (only a `ready` payload carries `project_path`), and align `test_scan_any_status_finds_rolled_over_cold_start_editor`'s fixture and premise with the payload shape the bridge emits. Verify: no test asserts against a `compiling` payload carrying `project_path`.
- [ ] 2.3 Determine by evidence whether the renamed scan is now equivalent in role to `discover_project_endpoint`, and collapse the duplicate if so; if not, record the concrete difference that keeps both. Verify: the remaining identity-matching rule is stated in one place or the divergence is justified in `design.md`.

## 3. Validation and Closeout

- [ ] 3.1 Run the default mocked/unit suite. Verify: green.
- [ ] 3.2 Confirm against the real host (`c3-client-tree2/Project`, see `openspec/specs/validation-host-integration/how-to-run.md`) while another project's Editor occupies the preferred control port, and confirm both rollover cases run and assert rather than skip. Verify: the cases that previously reported `SKIP` report their boundary records, and the discovery assertion passes.
- [ ] 3.3 Run `openspec validate --all` and confirm the change is archive-ready; revise the delta if the restructure concluded the durable dispositions need different substance. Verify: the delta matches what the suite actually enforces.
- [ ] 3.4 Complete the required apply closeout review and record either `No new follow-up work identified` or human-discussed follow-up candidates in an allowed category. Verify: the closeout separates this validation work from `diagnose-recovery-readiness-timeout`, `diagnose-exec-missing-after-auto-refresh`, and `diagnose-empty-response-parse-error`.
