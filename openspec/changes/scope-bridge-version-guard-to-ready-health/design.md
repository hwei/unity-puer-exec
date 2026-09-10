## Context

See proposal.md for motivation. Upstream `enforce-cli-version-compatibility` D5 remains true for a **ready** service that cannot name its version. This change addresses the gap D5 did not name: `/health` during compile/reload is a non-ready payload, and `BuildHealthResponseJson` currently emits a compiling stub that drops `bridge_version` even when the assembly knows it.

The wait-loop already treats that stub as "not observable yet" (`require_version=False`). The extra probe in `ensure_session_ready` and `_base_url_bridge_guard` do not. `--refresh-before-exec` hits both after `AssetDatabase.Refresh()` returns and compile has started.

## Goals / Non-Goals

**Goals:**

- One rule for missing `bridge_version`: mismatch only on ready health.
- Compiling / `not_available` health that knows the package version reports it, so a matching pair can be verified during the compile window.
- `--refresh-before-exec`, `wait-for-compile`, and other control-service commands survive the compile/reconnect window without a false `bridge_version_unknown`.
- A compiling payload that *does* carry a disagreeing version still refuses.

**Non-Goals:**

- A caller-facing bypass for real `version_mismatch`.
- Changing exact-string equality, package-layout guard, or exit code 24.
- Fixing empty HTTP bodies / JSON `Expecting value` when the listener dies mid-request.
- Changing `wait-for-compile`'s edge-aware appear/settle machine beyond not refusing on compiling health.

## Decisions

### D1: Scope missing-version mismatch to `status == "ready"`

`check_bridge(..., require_version=True)` is the current default. The extra probe and base-url guard pass whatever payload they got. After this change, missing `bridge_version` is a mismatch only when the payload is ready. For `compiling` and `not_available`, absence is skipped; presence is still compared.

*Alternatives considered.* (1) Keep D5 literal and only add `bridge_version` to compiling JSON — an older vendored Editor package would still false-refuse a newer CLI. (2) Treat any non-ready payload as a transport miss — would hide a compiling service that *does* report a wrong version. Status-gated `require_version` keeps D5 for ready services and still catches a versioned compiling mismatch.

### D2: Emit `bridge_version` on non-ready health when known

`BuildHealthResponseJson` already receives `bridgeVersion` and ignores it on the compiling branch. Include it on compiling and on bound `not_available` when non-empty. Session marker stays. Other ready-only identity fields (`project_path`, `unity_pid`, `console_log_path`) stay ready-only; `confirm_publication` already treats those as ready-only.

*Alternative considered.* Leave the stub unchanged and fix only the CLI. That would work for this CLI, but any other caller of `/health` during compile still cannot verify the pair, and a future extra probe with `require_version=True` would regress. Emitting the known version is the smaller contract completion.

### D3: Extra probe after wait is not a second, stricter contract

`ensure_session_ready` waits until ready, then probes again with `require_version=True`. A TOCTOU compile start between those two probes is the project-path transcript. After D1, that second probe seeing `compiling` without version no longer refuses. If it sees compiling *with* a matching version, the command proceeds and the server can return `compiling` as a non-terminal phase — which `formal-cli-contract` already requires for `--refresh-before-exec`.

Do not invent a third wait loop. Reuse the existing compiling continuation.

### D4: No bypass flag

Unchanged from upstream D4. The false refusal is removed by scoping the guard, not by documenting that agents may ignore `version_mismatch`.

## Risks / Trade-offs

- **[An old compiling stub still has no version]** → D1 makes that a wait/continue, not a refusal. D2 only helps once the Editor package is updated.
- **[A compiling payload with a wrong `bridge_version` now refuses immediately]** → Intended. Previously that payload had no version so the extra probe already refused, just with the wrong guard (`bridge_version_unknown` vs `bridge`).
- **[Ready-only identity fields still missing on compiling]** → Accepted. Ownership comparison stays on ready health and on the publication file; this change does not expand compiling health into a full identity document.
- **[Tests without a live Editor cannot prove the Unity JSON shape on a real compile]** → Unit-test the protocol builder and the CLI guards with fixtures; host-validation is optional evidence, not the gate.

## Migration Plan

No caller-facing flag or response-shape break for the happy path. Mixed-install refusals on ready endpoints are unchanged. After apply, agents can drop the "ignore `version_mismatch` after `--refresh-before-exec`" workaround; help and `version_mismatch` guidance stay "reconcile the installation".
