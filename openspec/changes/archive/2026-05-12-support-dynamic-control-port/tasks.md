## 1. Unity Endpoint Identity

- [x] 1.1 Replace the fixed Unity listener port with bounded dynamic loopback port binding that tries the preferred port first and records the selected port.
- [x] 1.2 Update Unity health response construction so ready responses include `port`, `base_url`, `unity_pid`, `project_path`, and `session_marker`.
- [x] 1.3 Add Unity-side tests or protocol-level tests that cover health identity fields and non-default selected port reporting.

## 2. Project Session Artifact

- [x] 2.1 Extend session artifact read/write helpers to preserve endpoint identity fields including `port` and `project_path`.
- [x] 2.2 Add artifact validation logic that treats artifact endpoints as candidates until live health proves project ownership.
- [x] 2.3 Add unit tests for stale artifact cases: unreachable endpoint, wrong project identity, missing identity fields, and old fixed-port artifacts.

## 3. CLI Project Routing

- [x] 3.1 Update project-scoped readiness flow to probe a validated artifact endpoint before using fixed preferred-port fallback or launching Unity.
- [x] 3.2 Update cold-start launch/recovery flow so old artifacts are not authoritative until the newly ready endpoint is verified.
- [x] 3.3 Preserve direct `--base-url` behavior without project artifact rewriting.
- [x] 3.4 Add CLI tests proving project mode routes to a non-default validated endpoint and direct base-url mode remains literal.

## 4. Validation And Documentation

- [x] 4.1 Update help or guidance text where it implies project-scoped routing always uses `127.0.0.1:55231`.
- [x] 4.2 Run the relevant Python unit test subset for direct client, session modules, and CLI routing.
- [x] 4.3 Run or document a real-host validation where one UnityPuerExec service occupies the preferred port and another project becomes ready on a later port.
- [x] 4.4 Record apply closeout findings and state whether any new follow-up work was identified.
