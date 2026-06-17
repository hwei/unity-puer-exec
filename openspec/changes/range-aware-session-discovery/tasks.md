## 1. Shared range definition

- [ ] 1.1 Add a single shared control-port range definition (preferred port + bounded range length) that both `direct_exec_client` and `unity_session` reference, replacing duplicated `55231`/range literals; keep `DEFAULT_BASE_URL` as the preferred-first entry point.
- [ ] 1.2 Add a helper that enumerates loopback candidate base URLs for the range in preferred-first order.

## 2. Range-aware discovery primitive

- [ ] 2.1 Implement a discovery helper in `unity_session` that scans the candidate range, probes `/health` per candidate with the existing short health timeout, and returns the first ready endpoint whose identity satisfies `_payload_matches_project(payload, project_path)` (preferred port tried first, stop on first match).
- [ ] 2.2 Ensure the helper returns enough to bind a session (resolved base_url + matched payload) and a clear "no match found" outcome distinct from "found another project's endpoint".

## 3. Wire discovery into ensure_session_ready

- [ ] 3.1 Replace the Phase 2 single `_probe_health(base_url)` discovery with the range-aware scan, preserving the existing artifact-first Phase 1 behavior.
- [ ] 3.2 Replace the post-launch-claim re-probe with the range-aware scan.
- [ ] 3.3 Make the recovery wait (`_build_recovery_session` + `wait_ready_with_activity`) resolve the endpoint by re-scanning the range with identity matching until a ready, project-matched endpoint appears or the readiness timeout elapses; bind the session to the resolved endpoint.
- [ ] 3.4 Make the cold-start post-launch wait resolve the launched Editor by range scan so a rolled-over port is discovered instead of waiting only on the preferred port.
- [ ] 3.5 Confirm strict identity gating at every claim site so a ready endpoint for a different project is skipped, never claimed.

## 4. Preserve base-url and single-instance behavior

- [ ] 4.1 Confirm base-url selector mode is unchanged: no range scan, no project validation, direct single-endpoint targeting.
- [ ] 4.2 Confirm the single-instance preferred-port hit path short-circuits on the first candidate with no extra probes.

## 5. Tests

- [ ] 5.1 Add unit/integration coverage for the discovery primitive: preferred-port hit, non-preferred-port match, different-project endpoint skipped, and no-match outcome.
- [ ] 5.2 Add coverage for recovery resolving a non-preferred bound port and for cold-start rollover discovery.
- [ ] 5.3 Add real-host regression(s) for the non-preferred-port and cold-start-rollover paths per the validation-host run instructions (evidence target: host-validation).

## 6. Closeout

- [ ] 6.1 Verify the modified `formal-cli-contract` scenarios are each exercised by a test or host-validation step.
- [ ] 6.2 Run the repository test suite and capture host-validation evidence; record results.
- [ ] 6.3 Produce the apply closeout finding summary and recommend the commit / `openspec archive` / final commit sequence.
